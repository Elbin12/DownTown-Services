from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from accounts.models import CustomUser
from worker.models import CustomWorker
from .serializer import GetUsers, GetWorkers
from accounts.views import token_generation_and_set_in_cookie
# Create your views here.



class Login(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        print(request.data, 'data')
        user = CustomUser.objects.filter(email = request.data['email']).first()
        if not user:
            return Response({'message': 'Invalid email or password'}, status=status.HTTP_400_BAD_REQUEST)
        if not user.is_superuser:
            return Response({'message': 'You are not admin'}, status=status.HTTP_400_BAD_REQUEST)
        if not user.check_password(request.data.get('password')):
            print('kkgj')
            return Response({'message': 'Invalid email or password'}, status=status.HTTP_400_BAD_REQUEST)
        response = token_generation_and_set_in_cookie(user)
        
        return response
    

class Users(APIView):
    permission_classes = [permissions.IsAdminUser]
    def get(self, request):
        users = CustomUser.objects.filter(is_superuser=False).order_by('date_joined')
        serailizer = GetUsers(users, many=True)
        return Response(serailizer.data, status=status.HTTP_200_OK)
    

class Block(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        email = request.data.get('email')
        user = CustomUser.objects.filter(email=email).first()
        print(user.is_active, 'active')
        if user:
            if user.is_active:
                user.is_active = False
            else:
                user.is_active = True
            user.save()
        print(user.is_active, 'lll')
        
        return Response({'isActive':user.is_active}, status=status.HTTP_200_OK)


class Workers(APIView):
    permission_classes = [permissions.IsAdminUser]
    def get(self, request):
        workers = CustomWorker.objects.all().order_by('date_joined')
        serailizer = GetWorkers(workers, many=True)
        return Response(serailizer.data, status=status.HTTP_200_OK)
    

class Requests(APIView):
    permission_classes = [permissions.IsAdminUser]
    def get(self, request):
        workers = CustomWorker.objects.exclude(status='verified').order_by('date_joined')
        print(workers, 'l')
        serailizer = GetWorkers(workers, many=True)
        return Response(serailizer.data, status=status.HTTP_200_OK)

class HandleRequest(APIView):
    permission_classes = [permissions.IsAdminUser]
    def post(self, request):
        status = request.data.get('status')
        user = CustomWorker.objects.filter(email=request.data.get('email')).first()
        if user:
            if status in dict(CustomWorker.STATUS_CHOICES):
                user.status = status
                user.save()
                return Response({'message': 'Status updated successfully'}, status=200)
            else:
                return Response({'error': 'Invalid status'}, status=400)
        return Response({'error': 'User not found'}, status=404)