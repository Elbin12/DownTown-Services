from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.core.mail import send_mail

from .models import CustomUser, UserProfile, Orders, OrderTracking, Review, Interactions, Wallet, Transaction, ChatMessage

import random
from django.conf import settings

import jwt, datetime
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser
from .serializer import ProfileSerializer, UserGetSerializer,CategoriesAndSubCategories, CustomUserSerializer, UserOrderSerializer, RequestListingDetails, UserOrderTrackingSerializer, WalletSerializer, ChatMessageSerializer
from admin_auth.models import Categories, SubCategories
from worker.serializer import RequestsSerializer, ServiceListingSerializer, ServiceListingDetailSerializer, WorkerDetailSerializerForUser
from worker.models import Services, CustomWorker, WorkerProfile, Requests

from .tasks import send_mail_task
from django.db.models import Q, Max
from .utils import upload_fileobj_to_s3, create_presigned_url, AuthenticateIfJWTProvided, find_distance, find_distance_for_anonymoususer, get_nearby_services, get_nearby_services_for_anonymoususer

import os, stripe
from datetime import datetime
from django.db.models import Count, OuterRef, Subquery
import requests
from django.http import HttpResponseRedirect
from django.contrib.auth.models import AnonymousUser
from accounts.authenticate import customAuthentication

# Create your views here.



stripe.api_key = settings.STRIPE_SECRET_KEY


def send_email(request, email, mob=None):
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
    
class SentOTP(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        print(request.data, 'data', request.user)
        email = request.data['email']
        if request.user.is_authenticated:
            if CustomUser.objects.exclude(email=request.user.email).filter(email=email).exists():
                return Response({'message':'Email with this email already exists'}, status=status.HTTP_400_BAD_REQUEST)
        send_email(request, email)
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
        token = request.data.get('token')
        if not token:
            return Response({'message': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)

        google_api_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
        headers = {'Authorization': f'Bearer {token}'}
        google_response = requests.get(google_api_url, headers=headers)
        
        if google_response.status_code != 200:
            return Response({'message': 'Invalid Google token'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_data = google_response.json()
        email = user_data['email']
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
                    first_name=user_data['given_name'], 
                    last_name=user_data['family_name'],
                    profile_pic=user_data['picture'],
                )
            profile.save()
            additional_data = {
                'first_name': user_data.get('given_name', ''),
                'last_name': user_data.get('family_name', ''),
                'profile_pic': user_data.get('picture', '')
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
        
class Verify(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        otp = request.data['otp']
        session_otp = request.session.get('otp')
        email = request.session.get('email')
        print(email, 'mob')
        if session_otp is not None:
            print(session_otp, otp)
            if str(session_otp) == otp:
                del request.session['otp']
                request.user.email = email
                request.user.save()
                user_profile = UserProfile.objects.get(user=request.user)
                serializer = UserGetSerializer(user_profile)
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({'message':'Incorrect OTP'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'message': 'OTP not found or expired'}, status=status.HTTP_400_BAD_REQUEST)

        
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
                file = request.FILES['profile_pic']
                file_extension = os.path.splitext(file.name)[1]
                current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_filename = f"{current_time_str}{file_extension}"
                s3_file_path = f"users/profile_pic/{unique_filename}"
                try:
                    image_url = upload_fileobj_to_s3(file, s3_file_path)
                    if image_url:
                        user_profile.profile_pic = s3_file_path
                        print("Image URL:", image_url)
                    else:
                        return Response({'error': 'File upload failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                except Exception as e:
                    print(e)
                    return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                print(user_profile.profile_pic)

            user_profile.save()
            request.user.save()

            serializer = UserGetSerializer(user_profile)
        
        else:
            return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return Response(serializer.data, status=status.HTTP_200_OK)


class GetCategories(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        category = Categories.objects.annotate(sub_category_count=Count('subcategories')).filter(sub_category_count__gt=0)
        serializer = CategoriesAndSubCategories(category, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class ServicesView(APIView):
    permission_classes = [AuthenticateIfJWTProvided]
    authentication_classes = []

    def get(self, request):
        try:
            search_key = request.query_params.get('search_key', None)
            services = Services.objects.filter(is_active=True, is_deleted=False)
            filters = Q()
            if search_key:
                filters |= Q(service_name__istartswith=search_key) | Q(category__category_name__istartswith=search_key)

            services = Services.objects.filter(filters, is_active=True, is_deleted=False, worker__worker_profile__is_available=True) if filters else Services.objects.filter(is_active=True, is_deleted=False, worker__worker_profile__is_available=True)
            print(request.user, 'user')
            if isinstance(request.user, AnonymousUser):
                lat = request.session.get('lat')
                lng = request.session.get('lng')
                print(request.session.get('location'), 'location', lat, lng)
                services = get_nearby_services_for_anonymoususer(lat, lng, services)
                print(services, 'services')
            elif isinstance(request.user, CustomUser):
                services = get_nearby_services(request.user, services)

            serializer = ServiceListingSerializer(services, many=True)  
            print(serializer, 'ss')
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(e, 'e')
            return Response({"detail": "An error occurred while retrieving services."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        search_key = request.data.get('search_key')
        try:
            filters = Q()
            if search_key:
                filters |= Q(service_name__istartswith=search_key) | Q(category__category_name__istartswith=search_key)
            print('ser', search_key, request.user)
            services = Services.objects.filter(filters, is_active=True, is_deleted=False) if filters else Services.objects.filter(is_active=True, is_deleted=False)
            selected = request.data.get('selected_sub')
            services_q = Q()
            for key, items in selected.items():
                cat = Categories.objects.filter(id=key).first()
                if cat:
                    services_q |= Q(category=cat, subcategory__in=items)
            services = services.filter(services_q).distinct()
            if isinstance(request.user, AnonymousUser):
                lat = request.session.get('lat')
                lng = request.session.get('lng')
                services = get_nearby_services_for_anonymoususer(lat, lng, services)
            elif isinstance(request.user, CustomUser):
                services = get_nearby_services(request.user, services)
            serializer = ServiceListingSerializer(services, many=True)
            print(serializer.data, 'data')
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(e, 'e')
            return Response({"detail": "An error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class ServiceDetail(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            print(pk, 'pk')
            service = Services.objects.get(id=pk)
            if isinstance(request.user, AnonymousUser):
                lat = request.session.get('lat')
                lng = request.session.get('lng')
                if find_distance_for_anonymoususer(lat, lng, service.worker.worker_profile) > 10:
                    return Response({'error':'Service is not available in your city'}, status=status.HTTP_400_BAD_REQUEST)
            elif isinstance(request.user, CustomUser):
                if find_distance(request.user, service.worker.worker_profile) > 10:
                    return Response({'error':'Service is not available in your city'}, status=status.HTTP_400_BAD_REQUEST)
            serializer = ServiceListingDetailSerializer(service, context={'request': request})
            print(serializer.data, 'data')
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Services.DoesNotExist:
            return Response({'message':'Service does not exist'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(e, 'e')
            return Response({"detail": "An error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ServiceRequests(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        print(request.data, 'data')
        worker_id = request.data.get('worker_id')
        service_id = request.data.get('service_id')
        description = request.data.get('description')
        try:
            worker = CustomWorker.objects.get(id=worker_id)
            print(worker, 'worker')
            worker_profile = WorkerProfile.objects.get(user=worker)
            service = Services.objects.get(id=service_id)
        except WorkerProfile.DoesNotExist:
            return Response({'error':'Worker not found'}, status=status.HTTP_404_NOT_FOUND)
        except Services.DoesNotExist:
            return Response({'error':'Service not found or does not belong to this worker'}, status=status.HTTP_404_NOT_FOUND)
        
        usage = worker_profile.subscription_usage
        if usage.can_handle_request():
            service_request, created = Requests.objects.get_or_create(
                user=request.user,
                worker=worker_profile,
                service=service,
                defaults={'status': 'request_sent'},
            )
            service_request.description = description
            service_request.status = 'request_sent'
            service_request.save()
            serailizer = RequestsSerializer(service_request)
            return Response(serailizer.data, status=status.HTTP_201_CREATED)
        else:
            return Response( {'failure':'Something went wrong.'} ,status=status.HTTP_400_BAD_REQUEST)
    
class CancelRequest(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request_id = request.data.get('request_id')
        try:
            request_obj = Requests.objects.get(id=request_id)
            request_obj.status = 'cancelled'
            request_obj.save()
            serailizer = RequestsSerializer(request_obj)
            return Response({'message':'Request is cancelled', 'data':serailizer.data}, status=status.HTTP_200_OK)
        except Requests.DoesNotExist:
            return Response({'error':'Request doesnot exists'}, status=status.HTTP_404_NOT_FOUND)
        
class ChangeLocation(APIView):
    permission_classes = [permissions.AllowAny] 

    def post(self, request):
        lat = request.data.get('lat')
        lng = request.data.get('lng')
        location = request.data.get('location')
        print(request.user, 'user')
        try:
            if isinstance(request.user, AnonymousUser):
                request.session['location'] = location
                request.session['lat'] = lat
                request.session['lng'] = lng
                return Response({'lat':lat, 'lng':lng, 'location':location}, status=status.HTTP_200_OK)
            else:
                user = request.user
                user.lat = lat
                user.lng = lng
                user.location = location
                user.save()
                try:
                    user_profile = UserProfile.objects.get(user=user)
                    serializer = UserGetSerializer(user_profile)
                except UserProfile.DoesNotExist:
                    serializer = CustomUserSerializer(user)
                return Response(serializer.data, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response({'error':'No user'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(e, 'e')
            return Response({'error':'An unexcepted error occured.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OrdersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            filter_key = request.query_params.get('filter_key', 'completed')
            print(filter_key, 'keeeee')
            orders = Orders.objects.filter(user=request.user, status=filter_key)
            if filter_key == 'completed':
                orders = Orders.objects.filter(user=request.user, status=filter_key, order_payment__status='paid')
            elif filter_key == 'working':
                orders = Orders.objects.filter(Q(user=request.user) & (Q(status=filter_key) | Q(status='pending') | Q(order_payment__status='unPaid')))
            print(orders, 'ordersss')
            serializer = UserOrderSerializer(orders, many=True, context={'request':request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Orders.DoesNotExist:
            return Response({'error':'Orders not found'}, status=status.HTTP_400_BAD_REQUEST)

        
class OrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            order = Orders.objects.get(id=pk)
            if order.user.id != request.user.id:
                print('not user')
                return Response({"error": "You do not have permission to view this order."}, status=status.HTTP_403_FORBIDDEN)
            serializer = UserOrderSerializer(order, context={'request':request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Requests.DoesNotExist:
            return Response(f'order not found on {pk}', status=status.HTTP_404_NOT_FOUND)
        
class FindOrderFromRequest(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            request_obj = Requests.objects.get(id=pk)
            order_obj = Orders.objects.filter(request=request_obj).order_by('-created_at').first()
            serializer = UserOrderSerializer(order_obj, context={'request':request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Orders.DoesNotExist:
            return Response(f'Request not found on {pk}', status=status.HTTP_404_NOT_FOUND)
        except Orders.DoesNotExist:
            return Response(f'Order not found with request id {pk}', status=status.HTTP_404_NOT_FOUND)
        
        
class WorkerArrived(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('order_id')
        print(order_id, 'idddd')
        try:
            order = Orders.objects.get(id=order_id)
            print(order.user.id, request.user.id, 'ids')
            if order.user.id != request.user.id:
                print('not user')
                return Response({"error": "You do not have permission to view this order."}, status=status.HTTP_403_FORBIDDEN)
            order.status = 'working'
            order_tracking = order.status_tracking
            order_tracking.is_worker_arrived = True
            order_tracking.arrival_time = datetime.now()
            order_tracking.work_start_time = datetime.now()
            order_tracking.is_work_started = True
            order_tracking.save()
            order.save()
            serializer = UserOrderTrackingSerializer(order_tracking)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Orders.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        except OrderTracking.DoesNotExist:
            return Response({"error": "Order tracking data not found."}, status=status.HTTP_404_NOT_FOUND)

class CreatePayment(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        print('kkkkllll')
        try:
            print(settings.STRIPE_SECRET_KEY, 'kkk')
            order_id = request.data.get('order_id')
            order = Orders.objects.get(id=order_id)
            line_items = []
            service_image_url = create_presigned_url(str(order.service_image_url))
            line_items.append({
                'price_data': {
                    'currency': 'inr',
                    'unit_amount': int(order.order_payment.total_amount * 100),
                    'product_data': {
                            'name': order.service_name,
                            'description': (
                                f"{order.service_description} | "
                                f"Worker Name: {order.service_provider.worker_profile.first_name} | "
                                f"Contact: {order.service_provider.mob}"
                            ),
                            'images': [service_image_url],
                        },
                },
                'quantity':1,
                })
            print(line_items, 'lineee')
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                mode='payment',
                line_items=line_items,
                success_url=f"http://localhost:8000/payment-success/{order.id}/",
                cancel_url=f"http://localhost:8000/payment-cancel/",
                metadata={'order_id': order_id},
            )

            return Response({'id': checkout_session.id}, status=status.HTTP_200_OK)
        except Orders.DoesNotExist:
            return Response({'error': 'Order not found.'}, status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({'error': str(e)}, status.HTTP_403_FORBIDDEN)
        
class PaymentSuccess(APIView):
    permission_classes = []

    def get(self, request, pk):
        try:
            print('kkiii')
            order = Orders.objects.get(id=pk)
            order.order_payment.status = 'paid'
            order.order_payment.save()
            order.save()
            request_obj = order.request
            request_obj.status = 'completed'
            request_obj.save()
            frontend_url = f"http://localhost:3000/payment/success/{pk}/"
            return HttpResponseRedirect(frontend_url)
        except Orders.DoesNotExist:
            return Response({'error':'order not found'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class AddReview(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        review = request.data.get('review')
        order_id = request.data.get('order_id')
        rating = request.data.get('rating')
        try:
            order = Orders.objects.get(id=order_id)
            review = Review.objects.create(order=order, review=review, rating=int(rating))
            Interactions.objects.create(user=request.user, review = review)
            serializer = UserOrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Orders.DoesNotExist:
            return Response({'error':'Order not found'}, status=status.HTTP_400_BAD_REQUEST)
        
class update_interaction(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        is_like = request.data.get('is_like')
        review_id = request.data.get('review_id')
        print(request.user, 'iiii')
        try:
            review = Review.objects.get(id=review_id)
            interaction, created = Interactions.objects.get_or_create(review=review, user=request.user, defaults={'is_liked': None})
            if interaction.is_liked is None:  
                interaction.is_liked = is_like
            elif interaction.is_liked == is_like:
                interaction.is_liked = None
            else:  
                interaction.is_liked = is_like

            interaction.save()
            serializer = WorkerDetailSerializerForUser(review.order.service_provider, context={'request': request})
            print(serializer.data, 'lllddd')
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Review.DoesNotExist:
            return Response({'error':'Review not found'}, status=status.HTTP_404_NOT_FOUND)
        
class   WalletView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            wallet, created = Wallet.objects.get_or_create(user=request.user)
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

            wallet, created = Wallet.objects.get_or_create(user=request.user)
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
            serailizer = WalletSerializer(Wallet.objects.get(user=request.user))
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
