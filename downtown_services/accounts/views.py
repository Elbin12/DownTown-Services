from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.core.mail import send_mail

from .models import CustomUser, UserProfile

import random
from django.conf import settings

import jwt, datetime
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser
from .serializer import ProfileSerializer, UserGetSerializer


# Create your views here.


def generate_otp():
    otp = random.randint(100000, 999999)
    return otp

def token_generation_and_set_in_cookie(user, additional_data=None):
    refresh = RefreshToken.for_user(user)
    refresh["email"] = str(user.email)
    content = {
        'isActive': user.is_active,
        'email':user.email,
    }

    if additional_data:
        content.update(additional_data)

    response = Response(content, status=status.HTTP_200_OK)
    response.set_cookie(
            key = settings.SIMPLE_JWT['AUTH_COOKIE'],
            value = str(refresh.access_token),
            secure = settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
            httponly = settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
            samesite = settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE']
        )
    response.set_cookie(
        key = 'refresh_token',
        value = str(refresh),
        secure = settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
        httponly = settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
        samesite = settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE']
    )
    return response

class SignIn(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        print(request.data, 'lll')
        email = request.data['email']
        mob = request.data['mob']
        print(request.data, 'lll')
        if not email and not mob:
            return Response({'message': 'Email or Mobile number is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        otp = generate_otp()
        request.session['otp'] = otp
        request.session['email'] = email
        request.session['mob'] = mob
        
        message = (
            f"""
            Dear {request.data['email']},

            Thank you for registering with DownTown Services!

            To complete your account setup, please verify your email address by entering the One-Time Password (OTP) provided below:

            Your OTP is: {otp}

            Best regards,
            The DownTown Services Team
            """
        )
        send_mail(
            "OTP verification",
            message,
            settings.EMAIL_HOST_USER,
            ['ajinth@yopmail.com'],
            fail_silently=False,
        )
        return Response({'message':f'OTP sent successfully to {email}.'}, status=status.HTTP_200_OK)


class VerifyOTP(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        print('vannu')
        otp = request.data['otp']
        session_otp = request.session.get('otp')
        email = request.session.get('email')
        mob = request.session.get('mob')
        print(email, mob, 'mob')
        if not mob:
            mob = None
        if not email:
            email = None
        if session_otp is not None:
            if str(session_otp) == otp:
                del request.session['otp']
                try:
                    user = CustomUser.objects.get(email=email)
                except:
                    user = CustomUser.objects.create_user(email=email, mob=mob)
                    user.save()
                response = token_generation_and_set_in_cookie(user)
                return response
            else:
                return Response({'message':'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'message': 'OTP not found or expired'}, status=status.HTTP_400_BAD_REQUEST)
        
class SignInWithGoogle(APIView):
    permission_classes  = [permissions.AllowAny]
    def post(self, request):
        print(request.data, 'ddd')
        email = request.data['email']
        try:
            user = CustomUser.objects.get(email=email)
            user_profile = UserProfile.objects.get(user=user)
            serializer = UserGetSerializer(user_profile)
            additional_data = serializer.data
            print('hello')
        except:
            user = CustomUser.objects.create_user(email=email)
            user.save()
            profile = UserProfile.objects.create(
                    user=user, 
                    first_name=request.data['given_name'], 
                    last_name=request.data['family_name'],
                    profile_pic=request.data['picture'],
                )
            profile.save()
            additional_data = {
                'first_name': request.data.get('given_name', ''),
                'last_name': request.data.get('family_name', ''),
                'profile_pic': request.data.get('picture', '')
            }
        response = token_generation_and_set_in_cookie(user, additional_data)
        return response

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        print(request,'llll',request.COOKIES)
        try:
            refresh_token = request.COOKIES.get("refresh_token")
            print(refresh_token,'token')
            token = RefreshToken(refresh_token)
            print('000')
            token.blacklist()
            print('pppp')
            response = Response(status=status.HTTP_205_RESET_CONTENT)
            print(';;')
            response.delete_cookie('refresh_token')
            response.delete_cookie('access_token')
            response.delete_cookie('csrftoken')
            print('finished')
            return response
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
class Profile(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request):
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            serializer = UserGetSerializer(user_profile)
        except:
            return Response({'message':'user doesnot has a profile'}, status=status.HTTP_200_OK)
        
        return Response({'message': 'Profile retrieved successfully', 'data':serializer.data}, status=status.HTTP_200_OK)

    def post(self, request):
        print(request.user, 'lggk')
        serializer = ProfileSerializer(data=request.data)
        if serializer.is_valid():
            # user = CustomUser.objects.filter(email=request.user)
            user_profile, created = UserProfile.objects.get_or_create(user=request.user, first_name = serializer.validated_data['first_name'], last_name = serializer.validated_data['last_name'], dob=serializer.validated_data['dob'], gender=serializer.validated_data['gender'], profile_pic = serializer.validated_data['profile_pic'])
            if not created:
                user_profile.first_name = serializer.validated_data['first_name']
                user_profile.last_name = serializer.validated_data['last_name']
                user_profile.dob = serializer.validated_data['dob']
                user_profile.gender = serializer.validated_data['gender']
                user_profile.profile_pic = serializer.validated_data['profile_pic']
                user_profile.save()
        else:
            print(serializer.errors)
            return Response(serializer.errors)

        return Response({'message': 'Profile updated successfully', 'data':serializer.data}, status=status.HTTP_200_OK)

        

class Home(APIView):
    def get(self, request):
        return Response({'message': 'Data received'}, status=status.HTTP_200_OK)
    
    def post(self, request):
        return Response({'message': 'Data received'}, status=status.HTTP_200_OK)