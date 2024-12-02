from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from accounts.models import CustomUser, OrderPayment, Additional_charges
from .models import CustomWorker, WorkerProfile, Services, Requests
from .serializer import WorkerRegisterSerializer, WorkerLoginSerializer, ServiceSerializer, ServiceListingSerializer, RequestListingDetails

import jwt, datetime
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from .serializer import WorkerDetailSerializer
from admin_auth.serializer import GetCategories, GetCategoriesOnly
from admin_auth.models import Categories

from rest_framework.parsers import MultiPartParser, FormParser

from accounts.utils import upload_fileobj_to_s3
from accounts.models import Orders, OrderTracking
from accounts.serializer import UserOrderSerializer

import os, json
from datetime import datetime

from django.db.models import Q
# Create your views here.


class CheckingCredentials(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        print(request.data)
        email = request.data.get('email')
        mob = request.data.get('mob')
        if CustomWorker.objects.filter(email=email).exists():
            return Response({'message':'An account is already registered with this email'}, status=status.HTTP_400_BAD_REQUEST)
        if CustomWorker.objects.filter(mob=mob).exists():
            return Response({'message':'An account is already registered with this mobile number'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = GetCategoriesOnly(Categories.objects.all(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class SignUp(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        print(request.FILES, 'files', request.data)
        data = request.data
        if 'services' in request.data and isinstance(request.data['services'], str):
            try:
                request.data['services'] = json.loads(request.data['services'])
                print(data, 'dddd')
            except json.JSONDecodeError:
                return Response({'services': 'Invalid format for services.'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                print(e)
                return Response({'services': 'Invalid data.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        serializer = WorkerRegisterSerializer(data=data)
        if serializer.is_valid():
            print('llll')
            serializer.save()
        else:
            print(serializer.errors, 'err')
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        print(serializer, serializer.data)

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request):
        print(request.FILES, 'files', request.data)
        worker_id = request.query_params.get('id')
        try:
            worker = CustomWorker.objects.get(id=worker_id)
        except CustomWorker.DoesNotExist:
            return Response({"error": "Worker not found."}, status=status.HTTP_404_NOT_FOUND)
        
        data = request.data
        if 'services' in request.data and isinstance(request.data['services'], str):
            try:
                services = json.loads(data["services"]) if isinstance(data["services"], str) else data["services"]
                worker.worker_profile.services.set(services)
            except json.JSONDecodeError:
                return Response({'services': 'Invalid format for services.'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                print(e)
                return Response({'services': 'Invalid data.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if "aadhaar_no" in data:
            worker.worker_profile.aadhaar_no = data["aadhaar_no"]

        if "location" in data:
            worker.worker_profile.location = data["location"]

        if "lat" in data:
            worker.worker_profile.lat = data["lat"]

        if "lng" in data:
            worker.worker_profile.lng = data["lng"]

        if "experience" in data:
            worker.worker_profile.experience = data["experience"]

        if "certificate" in request.FILES:
            cert_img = request.FILES["certificate"]

            if cert_img:
                file_extension = os.path.splitext(cert_img.name)[1]
                current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_filename = f"{current_time_str}{file_extension}"
                s3_file_path = f"workers/certificate/{unique_filename}"
                try:
                    image_url = upload_fileobj_to_s3(cert_img, s3_file_path)
                    if image_url:
                        worker.worker_profile.certificate = s3_file_path
                        print("Image URL:", image_url)
                    else:
                        return Response({'error':"File upload to S3 failed"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({'error':"something went wrong"}, status=status.HTTP_400_BAD_REQUEST)
        worker.status = 'in_review'
        worker.worker_profile.save()
        worker.save()
        return Response({'success':"Request sent successfully"}, status=status.HTTP_200_OK)


class Login(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        print('hi', request.data)
        if not request.data.get('email'):
            return Response({'message': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST) 
        worker = CustomWorker.objects.filter(email = request.data['email']).first()
        print(worker, 'gkg')
        if not worker:
            return Response({'message': 'Invalid email'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not worker.check_password(request.data.get('password')):
            return Response({'message': 'Invalid password'}, status=status.HTTP_400_BAD_REQUEST)
        
        if worker.status=='rejected':
            return Response({'message': 'You are rejected by admin'}, status=status.HTTP_400_BAD_REQUEST)
        if worker.status == 'in_review':
            return Response({'message': 'Your account are under verification.'}, status=status.HTTP_400_BAD_REQUEST)
        if not worker.is_active:
            return Response({'message': 'You are blocked'}, status=status.HTTP_400_BAD_REQUEST)
        
        worker_profile = WorkerProfile.objects.filter(user=worker).first()

        refresh = RefreshToken()
        refresh['worker_id'] = str(worker.id)
        refresh['user_type'] = 'worker'
        refresh["email"] = str(worker.email)
        content = {
            'isActive': worker.is_active,
            'isAdmin' : worker.is_superuser,
            'isWorker': worker.is_staff,
            'email':worker.email,
            'mob':worker.mob
        }

        if worker_profile:
            serializer = WorkerDetailSerializer(worker)
            content.update(serializer.data)

        response = Response(content, status=status.HTTP_200_OK)
        response.set_cookie(
                key = 'worker_access_token',
                value = str(refresh.access_token),
                secure = settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
                httponly = settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
                samesite = settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE']
            )
        response.set_cookie(
            key = 'worker_refresh_token',
            value = str(refresh),
            secure = settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
            httponly = settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
            samesite = settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE']
        )
        
        return response
    
class Profile(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        worker = CustomWorker.objects.get(user=request.user)
        serializer = WorkerDetailSerializer(worker)
        if serializer.is_valid():
            return Response(serializer.data,status=status.HTTP_200_OK)
        return Response(serializer.errors,status=status.HTTP_200_OK)
    
    def put(self, request):
        worker = request.user
        serializer = WorkerDetailSerializer(worker, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def post(self, request):
        print(request.user, 'lggk', request.data, request.user, request.user.id)
        print(request.FILES, 'kkk')
        serializer = WorkerDetailSerializer(data=request.data, context={'request':request})
        if serializer.is_valid():    
            print('hiiii')
            worker_profile, created = WorkerProfile.objects.get_or_create(user=request.user)
            worker_profile.first_name = request.data.get('first_name', worker_profile.first_name)
            worker_profile.last_name = request.data.get('last_name', worker_profile.last_name)
            worker_profile.dob = request.data.get('dob', worker_profile.dob)
            worker_profile.gender = request.data.get('gender', worker_profile.gender)
            request.user.mob = request.data.get('mob')
            if 'profile_pic' in request.FILES:
                print(request.FILES, 'llll')
                file = request.FILES['profile_pic']
                file_extension = os.path.splitext(file.name)[1]
                current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_filename = f"{current_time_str}{file_extension}"
                s3_file_path = f"workers/profile_pic/{unique_filename}"
                try:
                    image_url = upload_fileobj_to_s3(file, s3_file_path)
                    if image_url:
                        worker_profile.profile_pic = s3_file_path
                        print("Image URL:", image_url)
                    else:
                        return Response({'error': 'File upload failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                except Exception as e:
                    print(e)
                    return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                print(worker_profile.profile_pic)

            worker_profile.save()
            request.user.save()

            serializer = WorkerDetailSerializer(request.user)
        
        else:
            return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return Response(serializer.data, status=status.HTTP_200_OK)
    

class Logout(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        try:
            refresh_token = request.COOKIES.get("worker_refresh_token")
            token = RefreshToken(refresh_token)
            token.blacklist()
            response = Response(status=status.HTTP_205_RESET_CONTENT)
            response.delete_cookie('worker_refresh_token')
            response.delete_cookie('worker_access_token')
            response.delete_cookie('csrftoken')
            return response
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        

class ServicesManage(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get_object(self, pk):
        print(pk, 'kk')
        try:
            return Services.objects.get(id=pk)
        except Services.DoesNotExist:
            return Response(f'service not found on {pk}', status=status.HTTP_404_NOT_FOUND)

    def get(self, request):
        services = Services.objects.filter(worker=request.user, is_deleted=False)
        serializer = ServiceListingSerializer(services, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        print(request.data, 'data')
        serializer = ServiceSerializer(data=request.data,  context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        print(request.data)
        service = self.get_object(pk)
        serializer = ServiceSerializer(service, request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        service = self.get_object(pk)
        service.is_deleted = True
        service.save()
        return Response(status=status.HTTP_200_OK)


class WorkerRequests(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        print(request.user)
        worker = CustomWorker.objects.get(email=request.user)
        requests = Requests.objects.filter(worker=worker.worker_profile, status='request_sent')
        serializer = RequestListingDetails(requests,many=True)
        print(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        print(request.data, 'data')
        request_status = request.data.get('request')
        request_id = request.data.get('request_id')
        request_obj = Requests.objects.filter(id=request_id).first()
        if request_status:
            if request_status in ['accepted', 'rejected']:
                request_obj.status = request_status
                request_obj.save()
                if request_obj.status == 'accepted':
                    # if Orders.objects.filter(user=request_obj.user, service_provider=request_obj.worker)
                    order = Orders.objects.create(user=request_obj.user, service_provider=request_obj.worker.user, request=request_obj, service_name = request_obj.service.service_name, service_description=request_obj.service.description, service_price=request_obj.service.price, service_image_url=request_obj.service.pic, user_description=request_obj.description)
                    OrderTracking.objects.create(order=order)
                return Response({"message": f"Request status updated to {request_status}."}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": "Request not found."}, status=status.HTTP_404_NOT_FOUND)
    

class ChangeLocation(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        lat = request.data.get('lat')
        lng = request.data.get('lng')
        location = request.data.get('location')
        try:
            user_profile = WorkerProfile.objects.get(user=request.user)
            user_profile.lat = lat
            user_profile.lng = lng
            user_profile.location = location
            user_profile.save()
            serializer = WorkerDetailSerializer(request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except WorkerProfile.DoesNotExist:
            return Response({'error':'No user profile'}, status=status.HTTP_404_NOT_FOUND)
        
class OrdersView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        try:
            filter_key = request.query_params.get('filter_key', 'completed')
            orders = Orders.objects.filter(service_provider=request.user, status=filter_key)
            if filter_key == 'completed':
                orders = Orders.objects.filter(service_provider=request.user, status=filter_key, order_payment__status='paid')
            elif filter_key == 'working':
                orders = Orders.objects.filter(Q(service_provider=request.user) & Q(status=filter_key) | Q(status='pending') | Q(order_payment__status='unPaid'))
            print(orders, 'ordersss')
            serializer = UserOrderSerializer(orders, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Orders.DoesNotExist:
            return Response({'error':'Orders not found'}, status=status.HTTP_400_BAD_REQUEST)
        
class AcceptedServices(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        uncompleted_orders = Orders.objects.filter(Q(service_provider=request.user) & (Q(status='pending') | Q(status='working') | (Q(status='completed') & Q(order_payment__status='unPaid'))))
        accepted_requests = Requests.objects.filter(worker=request.user.worker_profile, status='accepted')
        serializer = UserOrderSerializer(uncompleted_orders, many=True)
        print('hi', uncompleted_orders)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class AcceptedService(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            order = Orders.objects.get(id=pk)
            serializer = UserOrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Orders.DoesNotExist:
            return Response(f'order not found on {pk}', status=status.HTTP_404_NOT_FOUND)

class WorkCompleted(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('order_id', None)
        try:
            order = Orders.objects.get(id = order_id)
            order_tracking = order.status_tracking
            order_tracking.work_end_time = datetime.now()
            order.status = 'completed'
            order_tracking.save()
            order.save()
            serializer = UserOrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Orders.DoesNotExist:
            return Response({'error':'Order not found.'}, status=status.HTTP_404_NOT_FOUND)
        
class AddPayment(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        order_id = request.data.get('order_id')
        additional_charges = request.data.get('additional_charges', [])

        if isinstance(additional_charges, str):
            try:
                additional_charges = json.loads(additional_charges)
            except json.JSONDecodeError:
                return Response({"error": "Invalid JSON format in additional_charges"}, status=status.HTTP_400_BAD_REQUEST)
        
        for index, charge in enumerate(additional_charges):
            file_key = f'image_{index}'
            if file_key in request.FILES:
                charge['image'] = request.FILES[file_key]

        print(additional_charges, 'addd')
        try:
            order = Orders.objects.get(id=order_id)
            total_amount = order.service_price
            payment = OrderPayment.objects.create(order=order)
            if additional_charges:
                for charge in additional_charges:
                    additional_charge = Additional_charges.objects.create(order_payment=payment, description=charge['description'], price=int(charge['amount']))
                    image_file = charge.get('image')
                    total_amount += int(charge.get('amount'))
                    if image_file:      
                        try:
                            file_extension = os.path.splitext(image_file.name)[1]
                            current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                            unique_filename = f"{current_time_str}{file_extension}"
                            s3_file_path = f"users/payment/receipts/{unique_filename}"

                            image_url = upload_fileobj_to_s3(image_file, s3_file_path)
                            if image_url:
                                additional_charge.image = s3_file_path
                                additional_charge.save()
                            else:
                                return Response({'error': 'File upload failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                        except Exception as e:
                            print(e)
                            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            payment.total_amount = total_amount
            payment.save()
            return Response(status=status.HTTP_200_OK)
        except Orders.DoesNotExist:
            return Response({'error':'Order not found.'}, status=status.HTTP_404_NOT_FOUND)
