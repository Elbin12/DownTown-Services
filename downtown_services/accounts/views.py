from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.core.mail import send_mail

from django.conf import settings


# Create your views here.


class SignIn(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        email = request.data['email']
        mob = request.data['mob']
        print(request.data)
        if not email and not mob:
            return Response({'message': 'Email or Mobile number is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        send_mail(
            "Subject here",
            "Here is the message.",
            settings.EMAIL_HOST_USER,
            ["ajinth@yopmail.com"],
            fail_silently=False,
        )
        
        return Response({'message': 'Data received'}, status=status.HTTP_200_OK)
    

class Home(APIView):
    def get(self, request):
        return Response({'message': 'Data received'}, status=status.HTTP_200_OK)
    
    def post(self, request):
        return Response({'message': 'Data received'}, status=status.HTTP_200_OK)