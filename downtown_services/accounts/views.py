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

from .tasks import send_mail_task


# Create your views here.


def send_email(request, email, mob):
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
    send_mail_task.delay(
        "OTP verification",
        message,
        settings.EMAIL_HOST_USER,
        [email]
    )
    print('otp', otp)
    


def generate_otp():
    otp = random.randint(100000, 999999)
    return otp

def token_generation_and_set_in_cookie(user, additional_data=None):
    refresh = RefreshToken.for_user(user)
    refresh["email"] = str(user.email)
    refresh['user_type'] = 'user'
    content = {
        'isActive': user.is_active,
        'isAdmin' : user.is_superuser,
        'isWorker': user.is_staff,
        'email':user.email,
    }

    print('from token')
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
        send_email(request, email, mob)
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
            print(session_otp, otp)
            if str(session_otp) == otp:
                del request.session['otp']
                try:
                    user = CustomUser.objects.get(email=email)
                except:
                    user = CustomUser.objects.create_user(email=email, mob=mob)
                    user.save()
                if not user.is_active:
                    return Response({'message':'You are Blocked by admin'}, status=status.HTTP_400_BAD_REQUEST)
                profile = UserProfile.objects.filter(user=user).first()
                if profile:
                    serializer = UserGetSerializer(profile)
                    response = token_generation_and_set_in_cookie(user, serializer.data)
                else:
                    response = token_generation_and_set_in_cookie(user)
                return response
            else:
                return Response({'message':'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'message': 'OTP not found or expired'}, status=status.HTTP_400_BAD_REQUEST)
        
class SignInWithGoogle(APIView):
    permission_classes  = [permissions.AllowAny]
    def post(self, request):
        print(request.data, 'ddd',)
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
        if not user.is_active:
            return Response({'message':'You are Blocked by admin'}, status=status.HTTP_400_BAD_REQUEST)
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
        print(request.user, 'lggk', request.data)
        print(request.FILES, 'kkk')
        serializer = ProfileSerializer(data=request.data, context={'request':request})
        if serializer.is_valid():    
            user_profile, created = UserProfile.objects.get_or_create(user=request.user)
            user_profile.first_name = request.data.get('first_name', user_profile.first_name)
            user_profile.last_name = request.data.get('last_name', user_profile.last_name)
            user_profile.dob = request.data.get('dob', user_profile.dob)
            user_profile.gender = request.data.get('gender', user_profile.gender)
            request.user.mob = request.data.get('mob')
            if 'profile_pic' in request.FILES:
                print(request.FILES, 'llll')
                user_profile.profile_pic = request.FILES['profile_pic']
                print(user_profile.profile_pic)

            user_profile.save()
            request.user.save()

            serializer = UserGetSerializer(user_profile)
        
        else:
            return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return Response(serializer.data, status=status.HTTP_200_OK)

        

class Home(APIView):
    def get(self, request):
        return Response({'message': 'Data received'}, status=status.HTTP_200_OK)
    
    def post(self, request):
        return Response({'message': 'Data received'}, status=status.HTTP_200_OK)

