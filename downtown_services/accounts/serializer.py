from rest_framework import serializers
from . models import CustomUser, UserProfile, Orders, OrderTracking, OrderPayment, Additional_charges, Review, Interactions
from admin_auth.models import Categories, SubCategories
from .utils import create_presigned_url

from worker.models import Requests



class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = '__all__'

class ProfileSerializer(serializers.ModelSerializer):
    mob = serializers.CharField(source='user.mob')
    profile_pic = serializers.SerializerMethodField()
    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'dob', 'gender', 'profile_pic', 'mob']
    
    def validate(self, data):
        request = self.context.get('request')
        print(request, request.user,data, 'll')
        if CustomUser.objects.filter(mob=data.get('user',{}).get('mob')).exclude(id=request.user.id).exists():
            raise serializers.ValidationError({'mob':'User with this mobile number already exists.'})
        return data
    
    def get_profile_pic(self, obj):
        image_url = create_presigned_url(str(obj.profile_pic))
        print(image_url, 'kk')
        if image_url:
            print(image_url, 'll')
            return image_url
        return None

    
    
class UserGetSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email')
    mob = serializers.CharField(source='user.mob')
    is_Active = serializers.BooleanField(source='user.is_active')
    is_Admin = serializers.BooleanField(source='user.is_superuser')
    location = serializers.CharField(source='user.location')
    lat = serializers.DecimalField(source='user.lat', max_digits=25, decimal_places=20)
    lng = serializers.DecimalField(source='user.lng', max_digits=25, decimal_places=20)
    profile_pic = serializers.SerializerMethodField()
    class Meta:
        model = UserProfile
        fields = ['email', 'mob', 'first_name', 'last_name', 'dob','lat', 'lng', 'location', 'gender', 'profile_pic', 'is_Active', 'is_Admin']
    
    def get_profile_pic(self, obj):
        image_url = create_presigned_url(str(obj.profile_pic))
        print(image_url, 'kk')
        if image_url:
            print(image_url, 'll')
            return image_url
        return None


class SubcategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategories
        fields = '__all__'

class CategoriesAndSubCategories(serializers.ModelSerializer):
    subcategories = SubcategorySerializer(many=True)
    class Meta:
        model = Categories
        fields = [ 'category_name', 'id', 'subcategories' ]

class UserOrderTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderTracking
        fields = '__all__'

class AdditionalChargesSerializer(serializers.ModelSerializer):
    reciept_img = serializers.SerializerMethodField()
    class Meta:
        model = Additional_charges
        fields = ['id', 'order_payment', 'description', 'reciept_img', 'price']
    
    def get_reciept_img(self, instance):
        image_url = create_presigned_url(str(instance.image))
        if image_url:
            return image_url
        return None
    
class PaymentSerializer(serializers.ModelSerializer):
    additional_charges = AdditionalChargesSerializer(many=True, read_only=True)
    class Meta:
        model = OrderPayment
        fields = ['id', 'order', 'total_amount', 'status', 'created_at', 'updated_at', 'additional_charges']

class ReviewSerializer(serializers.ModelSerializer):
    user = ProfileSerializer(source = 'order.user.user_profile')
    total_likes = serializers.SerializerMethodField()
    total_dislikes = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'review', 'rating', 'user', 'total_likes', 'total_dislikes', 'is_liked']

    def get_total_likes(self, obj):
        return Interactions.objects.filter(review=obj, is_liked=True).count()
    
    def get_total_dislikes(self, obj):
        return Interactions.objects.filter(review=obj, is_liked=False).count()
    
    def get_is_liked(self, obj):
        interaction = Interactions.objects.get(review=obj, user=obj.order.user)
        return interaction.is_liked


class UserOrderSerializer(serializers.ModelSerializer):
    from worker.serializer import WorkerDetailSerializer

    user = UserGetSerializer(source='user.user_profile', read_only = True)
    order_tracking = UserOrderTrackingSerializer(source='status_tracking',read_only = True)
    worker = serializers.SerializerMethodField(read_only = True)
    service_image = serializers.SerializerMethodField()
    payment_details = serializers.SerializerMethodField()
    user_review = ReviewSerializer(source='review', many=True, read_only=True)
    class Meta:
        model = Orders
        fields = ['id', 'user', 'worker', 'order_tracking', 'service_name', 'service_description', 'service_price', 'status', 'service_image', 'user_description', 'created_at', 'payment_details', 'user_review']

    def get_service_image(self, instance):
        image_url = create_presigned_url(str(instance.service_image_url))
        if image_url:
            return image_url
        return None
    
    def get_worker(self, instance):
        from worker.serializer import WorkerDetailSerializer
        return WorkerDetailSerializer(instance.service_provider).data
    
    def get_payment_details(self, instance):
        if hasattr(instance, 'order_payment'):  
            payment = instance.order_payment  
            payment_data = PaymentSerializer(payment).data  
            if hasattr(payment, 'additional_charges'):
                additional_charges = payment.additional_charges.all()  
                additional_charges_data = AdditionalChargesSerializer(additional_charges, many=True).data
                payment_data['additional_charges'] = additional_charges_data
            return payment_data
        return None
    
class RequestListingDetails(serializers.ModelSerializer):
    worker = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()
    class Meta:
        model = Requests
        fields = [ 'id', 'worker', 'service', 'description', 'status']

    def get_worker(self, instance):
        from worker.serializer import WorkerDetailSerializer
        return WorkerDetailSerializer(instance.worker.user).data
    
    def get_service(self, instance):
        from worker.serializer import ServiceListingSerializer
        return ServiceListingSerializer(instance.service).data

