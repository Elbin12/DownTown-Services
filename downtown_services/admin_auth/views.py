from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from accounts.models import CustomUser, Orders
from accounts.serializer import OrdersListingSerializer
from worker.models import CustomWorker
from .models import Categories, SubCategories, Subscription
from .serializer import GetUsers, GetWorkers, GetCategories, SubcategorySerializer, SubscriptionsSerializer
from accounts.views import token_generation_and_set_in_cookie
from worker.models import Services
from worker.serializer import ServiceSerializer
from .utils import send_email_for_worker_reject
from django.db.models import Q
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
        page_no = int(request.query_params.get('page_no', 1))
        page_size = 5
        offset = (page_no - 1) * page_size

        current_users = CustomUser.objects.filter(is_superuser=False).order_by('date_joined')[offset:offset + page_size]
        total_users = CustomUser.objects.filter(is_superuser=False).count()
        total_pages = (total_users + page_size - 1) // page_size

        pagination = {
            'total_pages':total_pages,
            'current_page':page_no
        }
        serializer = GetUsers(current_users, many=True)
        return Response({'users': serializer.data, 'pagination': pagination}, status=status.HTTP_200_OK)
    

class Block(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        email = request.data.get('email')
        user = CustomUser.objects.filter(email=email).first()
        if user:
            if user.is_active:
                user.is_active = False
            else:
                user.is_active = True
            user.save()
            print(user.is_active, 'lll')
        
        return Response({'isActive':user.is_active}, status=status.HTTP_200_OK)
    
class WorkerBlock(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        email = request.data.get('email')
        worker = CustomWorker.objects.filter(email=email).first()
        if worker:
            if worker.is_active:
                worker.is_active = False
            else:
                worker.is_active = True
            worker.save()
            print(worker.is_active, 'lll')
        return Response({'isActive':worker.is_active}, status=status.HTTP_200_OK)


class Workers(APIView):
    permission_classes = [permissions.IsAdminUser]
    def get(self, request):
        page_no = int(request.query_params.get('page_no', 1))
        page_size = 5
        offset = (page_no - 1) * page_size

        workers = CustomWorker.objects.filter(status='verified').order_by('date_joined')[offset:offset + page_size]
        total_users = CustomWorker.objects.all().count()
        total_pages = (total_users + page_size - 1) // page_size

        pagination = {
            'total_pages':total_pages,
            'current_page':page_no
        }
        serializer = GetWorkers(workers, many=True)
        return Response({'workers': serializer.data, 'pagination': pagination}, status=status.HTTP_200_OK)
    
class Worker(APIView):
    permission_classes = [permissions.IsAdminUser]
    def get(self, request, pk):
        try:
            worker = CustomWorker.objects.get(id=pk)
            serializer = GetWorkers(worker)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except CustomWorker.DoesNotExist:
            return Response({'error':'worker do not found.'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error':'Something went wrong'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

class Requests(APIView):
    permission_classes = [permissions.IsAdminUser]
    def get(self, request):
        workers = CustomWorker.objects.exclude(Q(status='verified')|Q(status='rejected')).order_by('date_joined')
        print(workers, 'l')
        serailizer = GetWorkers(workers, many=True)
        return Response(serailizer.data, status=status.HTTP_200_OK)

class HandleRequest(APIView):
    permission_classes = [permissions.IsAdminUser]
    def post(self, request):
        status = request.data.get('status')
        reason = request.data.get('reason')
        user = CustomWorker.objects.filter(email=request.data.get('email')).first()
        if user:
            if status in dict(CustomWorker.STATUS_CHOICES):
                user.status = status
                if status == 'verified':
                    user.is_active = True
                elif status == 'rejected':
                    send_email_for_worker_reject(user.email, reason, f'id={user.id}')
                    user.is_active = False
                user.save()
                serailizer = GetWorkers(user)
                if user.is_active:
                    return Response( {**serailizer.data, 'success':'Request accepted'}, status=200)
                return Response( {**serailizer.data, 'failure':'Request rejected'}, status=200)
            else:
                return Response({'error': 'Invalid status'}, status=400)
        return Response({'error': 'User not found'}, status=404)
    
class CategoryManage(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get_object(self, pk):
        try:
            return Categories.objects.get(id=pk)
        except Categories.DoesNotExist:
            return Response(f'category not found on {pk}', status=status.HTTP_404_NOT_FOUND)

    def get(self, request):
        categories = Categories.objects.all()
        serializer = GetCategories(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        print(request.data, 'data')
        serializer = GetCategories(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        print(pk, 'll', request.data)
        category = self.get_object(pk)  
        serializer = GetCategories(category, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK) 
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        print(request.data, 'ooo')
        category = self.get_object(pk)
        category.delete()
        return Response(status=status.HTTP_200_OK)


class Subcategory(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get_object(self, pk):
        print(pk, 'kk')
        try:
            return SubCategories.objects.get(id=pk)
        except SubCategories.DoesNotExist:
            return Response(f'subcategory not found on {pk}', status=status.HTTP_404_NOT_FOUND)

    def get(self, request):
        sub_categories = SubCategories.objects.all()
        print(sub_categories    )
        serializer = SubcategorySerializer(sub_categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        print(request.data)
        serializer = SubcategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        print(request.data)
        subcategory = self.get_object(pk)
        serializer = SubcategorySerializer(subcategory, request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        print(request.data, 'ooo')
        subcategory = self.get_object(pk)
        subcategory.delete()
        return Response(status=status.HTTP_200_OK)
    
class GetServices(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        services = Services.objects.all()
        serializer = ServiceSerializer(services, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class GetService(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, pk):
        try:
            service = Services.objects.get(id=pk)
            serializer = ServiceSerializer(service)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Services.DoesNotExist:
            return Response({'error':'Service not found'}, status=status.HTTP_404_NOT_FOUND)
        
    # Block Serive 
    def post(self, request, pk):
        try:
            service = Services.objects.get(id=pk)
            if service.is_active:
                service.is_active = False
            else:
                service.is_active = True
            service.save()
            serializer = ServiceSerializer(service)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Services.DoesNotExist:
            return Response({'error':'Service not found'}, status=status.HTTP_404_NOT_FOUND)
    
class SubscriptionsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get_object(self, pk):
        print(pk, 'kk')
        try:
            return Subscription.objects.get(id=pk)
        except Subscription.DoesNotExist:
            return Response(f'Subscription not found on {pk}', status=status.HTTP_404_NOT_FOUND)

    def get(self, request):
        subscriptions = Subscription.objects.all()
        serializer = SubscriptionsSerializer(subscriptions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        print(request.data, 'data')
        serializer = SubscriptionsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        print(pk, 'll', request.data)
        subscription = self.get_object(pk)  
        serializer = SubscriptionsSerializer(subscription, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK) 
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        print(request.data, 'ooo')
        subscription = self.get_object(pk)
        subscription.delete()
        return Response(status=status.HTTP_200_OK)
    
class GetOrders(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        try:
            orders = Orders.objects.all()
            serializer = OrdersListingSerializer(orders, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Orders.DoesNotExist:
            return Response({'error':'Order not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error':f'{e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetOrderDetails(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, pk):
        try:
            order = Orders.objects.get(id=pk)
            serializer = OrdersListingSerializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Orders.DoesNotExist:
            return Response({'error':f'order not found on {pk}.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error':f'Error on {e}.'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)