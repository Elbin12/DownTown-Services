from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.core.mail import send_mail

from .models import CustomUser

import random
from django.conf import settings

import jwt, datetime
from rest_framework_simplejwt.tokens import RefreshToken


# Create your views here.


def generate_otp():
    otp = random.randint(100000, 999999)
    return otp

def token_generation_and_set_in_cookie(user):
    refresh = RefreshToken.for_user(user)
    refresh["email"] = str(user.email)
    content = {
        'isAdmin': user.is_superuser,
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

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
        email = request.data['email']
        try:
            user = CustomUser.objects.get(email=email)
        except:
            user = CustomUser.objects.create_user(email=email)
            user.save()
        response = token_generation_and_set_in_cookie(user)
        return response
        

class Home(APIView):
    def get(self, request):
        return Response({'message': 'Data received'}, status=status.HTTP_200_OK)
    
    def post(self, request):
        return Response({'message': 'Data received'}, status=status.HTTP_200_OK)