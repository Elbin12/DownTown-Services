from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from accounts.models import CustomUser, OrderPayment, Additional_charges
from .models import CustomWorker, WorkerProfile, Services, Requests, Wallet, Transaction, WorkerSubscription
from admin_auth.models import Subscription
from admin_auth.serializer import SubscriptionsSerializer
from .serializer import WorkerRegisterSerializer, WorkerLoginSerializer, ServiceSerializer, ServiceListingSerializer, RequestListingDetails, ChatMessageSerializer, WalletSerializer

from django.utils.timezone import make_aware, now, timedelta
import jwt, datetime
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from .serializer import WorkerDetailSerializer
from admin_auth.serializer import GetCategories, GetCategoriesOnly
from admin_auth.models import Categories

from rest_framework.parsers import MultiPartParser, FormParser

from accounts.utils import upload_fileobj_to_s3, generate_otp
from accounts.models import Orders, OrderTracking, ChatMessage, Review
from accounts.serializer import OrdersListingSerializer

import os, json, stripe
from datetime import datetime
from accounts.tasks import send_notification
from django.db.models import Q, OuterRef, Subquery, Avg, Sum

from .utils import update_subscription_plan, cancel_subscription
# Create your views here.


stripe.api_key = settings.STRIPE_SECRET_KEY


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
            serializer = WorkerLoginSerializer(worker)
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
        services = Services.objects.filter(worker=request.user).order_by('-created_at')
        serializer = ServiceListingSerializer(services, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        print(request.data, 'data')
        usage = request.user.worker_profile.worker_subscription
        serializer = ServiceSerializer(data=request.data,  context={'request': request})
        if serializer.is_valid():
            serializer.save()
            usage.increment_services_added()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        print(request.data)
        service = self.get_object(pk)
        usage = request.user.worker_profile.worker_subscription
        serializer = ServiceSerializer(service, request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            serializer.save()
            usage.increment_services_updated()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        service = self.get_object(pk)
        service.is_listed = True if service.is_listed == False else False
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
                    usage = request.user.worker_profile.worker_subscription
                    if usage.can_handle_request():
                        send_notification.delay(
                            user_id=request_obj.user.id,
                            message=f"Your request has been accepted by {request_obj.worker.first_name}!"
                        )
                        otp = generate_otp()
                        send_notification.delay(
                            user_id=request_obj.user.id,
                            message=f"{otp} Show this otp to worker when the worker {request_obj.worker.first_name} arrives"
                        )
                        order = Orders.objects.create(user=request_obj.user, service_provider=request_obj.worker.user, request=request_obj, service_name = request_obj.service.service_name, service_description=request_obj.service.description, service_price=request_obj.service.price, service_image_url=request_obj.service.pic, user_description=request_obj.description, otp=otp)
                        OrderTracking.objects.create(order=order)
                        usage.increment_user_requests_handled()
                        usage.save()
                    else:
                        return Response({'failure':'User request limit reached for the subscription tier.'}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    send_notification.delay(
                        user_id=request_obj.user.id,
                        message=f"Your request has been rejected by {request_obj.worker.first_name}!"
                    )
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
                orders = Orders.objects.filter(Q(service_provider=request.user) & (Q(status=filter_key) | Q(status='pending') | Q(order_payment__status='unPaid')))
            print(orders, 'ordersss')
            serializer = OrdersListingSerializer(orders, many=True, context={'request':request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Orders.DoesNotExist:
            return Response({'error':'Orders not found'}, status=status.HTTP_400_BAD_REQUEST)
        
class AcceptedServices(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        print(request.user, 'user')
        uncompleted_orders = Orders.objects.filter(Q(service_provider=request.user) & (Q(status='pending') | Q(status='working') | (Q(status='completed') & Q(order_payment__status='unPaid')))).order_by('-created_at')
        accepted_requests = Requests.objects.filter(worker=request.user.worker_profile, status='accepted')
        serializer = OrdersListingSerializer(uncompleted_orders, many=True, context={'request':request})
        print('hi', uncompleted_orders)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class AcceptedService(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            order = Orders.objects.get(id=pk)
            serializer = OrdersListingSerializer(order, context={'request':request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Orders.DoesNotExist:
            return Response(f'order not found on {pk}', status=status.HTTP_404_NOT_FOUND)

class CheckOTP(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('order_id')
        otp = int(request.data.get('otp'))
        print(order_id, 'idddd')
        try:
            order = Orders.objects.get(id=order_id)
            if otp == order.otp:
                order.status = 'working'
                order_tracking = order.status_tracking
                order_tracking.is_worker_arrived = True
                order_tracking.arrival_time = datetime.now()
                order_tracking.work_start_time = datetime.now()
                order_tracking.is_work_started = True
                order_tracking.save()
                order.save()
                serializer = OrdersListingSerializer(order, context={'request':request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)
        except Orders.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        except OrderTracking.DoesNotExist:
            return Response({"error": "Order tracking data not found."}, status=status.HTTP_404_NOT_FOUND)

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
            user_profile = order.user.user_profile
            user_profile.is_any_pending_payment = True
            user_profile.save()
            serializer = OrdersListingSerializer(order)
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
            serializer = OrdersListingSerializer(order, context={'request':request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Orders.DoesNotExist:
            return Response({'error':'Order not found.'}, status=status.HTTP_404_NOT_FOUND)


class ChatHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id, worker_id, page_no):
        ids = sorted([user_id, worker_id])
        no = page_no*20
        messages = ChatMessage.objects.filter(
            sender_id__in=ids,
            recipient_id__in=ids
        ).order_by('-timestamp')[(page_no-1)*20:no]
        messages = messages[::-1]                                                                                                                                                                                                                  
        serializer = ChatMessageSerializer(messages, many=True, context={'request':request})
        return Response({'messages':serializer.data, 'page_no':page_no}, status=status.HTTP_200_OK)

class Chats(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Subquery to find the last message for each conversation involving the user
        last_message_subquery = ChatMessage.objects.filter(
            Q(sender_id=OuterRef('sender_id'), recipient_id=OuterRef('recipient_id')) |
            Q(sender_id=OuterRef('recipient_id'), recipient_id=OuterRef('sender_id'))
        ).filter(
            Q(sender_id=user.id) | Q(recipient_id=user.id)  # Restrict to user's conversations
        ).order_by('-timestamp').values('id')[:1]

        # Fetch the latest messages in user's conversations
        last_messages = ChatMessage.objects.filter(
            Q(sender_id=user.id) | Q(recipient_id=user.id),  # Include only user's messages
            id__in=Subquery(last_message_subquery)
        ).distinct().order_by('-timestamp')

        serializer = ChatMessageSerializer(last_messages, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


    

class WalletView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            print(request.user, 'uuu')
            wallet, created = Wallet.objects.get_or_create(worker=request.user)
            serializer = WalletSerializer(wallet)
            print(serializer.data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Wallet.DoesNotExist:
            return Response({'error':'Wallet not found.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e, 'ee')
            return Response({'error':'Something went wrong.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        amount = int(request.data.get("amount"))*100

        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency="inr",
                payment_method_types=["card"],
            )

            wallet, created = Wallet.objects.get_or_create(worker=request.user)
            transaction = Transaction.objects.create(wallet=wallet, transaction_type = 'credit', amount=amount/100)
            return Response({"client_secret": payment_intent.client_secret, 'transaction_id':transaction.id}, status=status.HTTP_200_OK)
        except Exception as e:
            print(e, 'ee')
            return Response({'error':'Something went wrong.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class CapturePayment(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        transaction_id = request.data.get("transaction_id")
        payment_intent_id = request.data.get("payment_intent_id")
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            trans = Transaction.objects.get(id=transaction_id)

            if payment_intent['status'] == 'succeeded':
                if trans.status != 'completed':
                    trans.status = 'completed'
            else:
                trans.status = 'failed'
            trans.save()
            serailizer = WalletSerializer(Wallet.objects.get(worker=request.user))
            return Response(serailizer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(e, 'eee')
            try:
                trans = Transaction.objects.get(id=transaction_id)
                trans.status = 'failed'
                trans.save()
            except Transaction.DoesNotExist:
                return Response({'error':'Transaction not found'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response({'error':'Something went wrong'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class SubscriptionPlans(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        subscriptions = Subscription.objects.all()
        serializer = SubscriptionsSerializer(subscriptions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
def get_sales_chart_data(request):
    today = now().date()
    labels = [(today - timedelta(days=i)).strftime("%d-%m-%Y") for i in range(6, -1, -1)]
    
    # Calculate daily order counts for the last 7 days
    orders_last_week = []
    revenue_last_week = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        orders_count = Orders.objects.filter(service_provider= request.user, created_at__date=day).count()
        revenue_sum = (
            OrderPayment.objects.filter(order__service_provider=request.user, order__created_at__date=day)
            .aggregate(total=Sum('total_amount'))['total'] or 0
        )
        orders_last_week.append(orders_count)
        revenue_last_week.append(revenue_sum)

    return orders_last_week, revenue_last_week, labels

    
        
class Dashboard(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        worker_status = request.user.worker_profile.is_available
        services_completed = Orders.objects.filter(service_provider=request.user, order_payment__status='paid')
        revenue = sum([service.order_payment.total_amount for service in services_completed])
        # Count completed orders
        services_count = services_completed.count()

        # Calculate average rating
        reviews = Review.objects.filter(order__service_provider=request.user)
        average_rating = reviews.aggregate(Avg('rating')).get('rating__avg', 0) or 0
        feedback = reviews.values('review', 'rating', 'created_at')[:5]

        orders_last_week, revenue_last_week, labels = get_sales_chart_data(request)

        return Response({'status':worker_status, 'revenue':revenue, 'services_count':services_count, 'average_rating':average_rating, 'feedback': feedback,
                         'orders_last_week':orders_last_week, 'revenue_last_week':revenue_last_week, 'labels':labels }, status=status.HTTP_200_OK)

    def post(self, request):
        worker_status = request.data.get('status', None)
        user = request.user
        if worker_status is not None:
            user.worker_profile.is_available = worker_status
        user.worker_profile.save()
        print(user.worker_profile.is_available, 'is_available')
        return Response({'status':worker_status}, status=status.HTTP_200_OK)
    

class CreateSubscriptionView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        try:
            subscription_plan_id = request.data.get("subscription_plan_id")
            payment_method_id = request.data.get("payment_method_id")

            if not subscription_plan_id or not payment_method_id:
                return Response({"error": "Missing required parameters."}, status=status.HTTP_400_BAD_REQUEST)
            
            subscription_plan = Subscription.objects.get(id=subscription_plan_id)

            if not request.user.worker_profile.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=request.user.email,
                    payment_method=payment_method_id,
                )
                request.user.worker_profile.stripe_customer_id = customer.id
                request.user.worker_profile.save()
            
                stripe.Customer.modify(
                    customer.id,
                    invoice_settings={'default_payment_method': payment_method_id}
                )
            else:
                customer = stripe.Customer.retrieve(request.user.worker_profile.stripe_customer_id)
                # Attach new payment method to existing customer
                stripe.PaymentMethod.attach(
                    payment_method_id,
                    customer=customer.id,
                )
            
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{
                    "price": subscription_plan.stripe_price_id, 
                }],
                default_payment_method=payment_method_id,
                expand=["latest_invoice.payment_intent"],
            )

            # Check if payment was successful
            payment_intent = subscription.latest_invoice.payment_intent
            if payment_intent.status != 'succeeded':
                return Response({"error": "Payment failed."}, status=status.HTTP_402_PAYMENT_REQUIRED)
            
            invoice_id = subscription.latest_invoice.id
            subscription_end_date = make_aware(datetime.fromtimestamp(subscription.current_period_end))
            worker_subscription, created = WorkerSubscription.objects.get_or_create(
                worker_profile=request.user.worker_profile,
                defaults={
                    "stripe_subscription_id": subscription.id,
                    "stripe_price_id": subscription_plan.stripe_price_id,
                    "stripe_product_id": subscription_plan.stripe_product_id,
                    "tier_name": subscription_plan.tier_name,
                    "price": subscription_plan.price,
                    "platform_fee_perc": subscription_plan.platform_fee_perc,
                    "analytics": subscription_plan.analytics,
                    "service_add_limit": subscription_plan.service_add_limit,
                    "service_update_limit": subscription_plan.service_update_limit,
                    "user_requests_limit": subscription_plan.user_requests_limit,
                    "subscription_status": "active",
                    "subscription_end_date": subscription_end_date,
                    "invoice_id": invoice_id,
                }
            )

            if not created:
                worker_subscription.stripe_subscription_id = subscription.id
                worker_subscription.stripe_price_id = subscription_plan.stripe_price_id,
                worker_subscription.stripe_product_id =  subscription_plan.stripe_product_id,
                worker_subscription.tier_name = subscription_plan.tier_name,
                worker_subscription.price = subscription_plan.price,
                worker_subscription.platform_fee_perc = subscription_plan.platform_fee_perc,
                worker_subscription.analytics = subscription_plan.analytics,
                worker_subscription.service_add_limit = subscription_plan.service_add_limit,
                worker_subscription.service_update_limit = subscription_plan.service_update_limit,
                worker_subscription.user_requests_limit = subscription_plan.user_requests_limit,
                worker_subscription.subscription_status = "active"
                worker_subscription.subscription_end_date = subscription_end_date
                worker_subscription.invoice_id = invoice_id
                worker_subscription.save()

            # Update user profile
            request.user.worker_profile.is_subscribed = True
            request.user.worker_profile.subscription = subscription_plan
            request.user.worker_profile.save()

            return Response({'status':'success', "message": "Subscription created successfully and payment was processed.", 'worker_info':WorkerDetailSerializer(request.user).data})
        except Subscription.DoesNotExist:
            return Response({"status": "failed", "error": "Invalid subscription plan ID."}, status=status.HTTP_404_NOT_FOUND)
        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error": f"Something went wrong: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
class SubscriptionUpgrade(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        try:
            subscription_plan_id = request.data.get("subscription_plan_id")

            if not subscription_plan_id:
                return Response({"status": "failed", "error": "Subscription plan ID is required."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                subscription_plan = Subscription.objects.get(id=subscription_plan_id)
            except Subscription.DoesNotExist:
                return Response({"status": "failed", "error": "Invalid subscription plan ID."}, status=status.HTTP_404_NOT_FOUND)
            
            worker_profile = request.user.worker_profile
            update_subscription_plan(worker_profile, subscription_plan)
            return Response({'message':'Subscription upgraded successfully.', 'worker_info':WorkerDetailSerializer(request.user).data}, status=status.HTTP_200_OK)

        except stripe.error.StripeError as e:
            return Response({"status": "failed", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response({"status": "failed", "error": f"Something went wrong: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class CancelSubscription(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        try:
            worker_profile = request.user.worker_profile
            success = cancel_subscription(worker_profile)

            if success:
                return Response({'message': 'Subscription cancellation scheduled successfully.'}, status=status.HTTP_200_OK)
            else:
                return Response({'message': 'Failed to cancel subscription.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'message':f'error on {e}.'}, status=status.HTTP_400_BAD_REQUEST)
        
class GetCategories(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        serializer = GetCategoriesOnly(Categories.objects.all(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

