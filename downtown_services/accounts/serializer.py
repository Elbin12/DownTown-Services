from rest_framework import serializers
from . models import CustomUser, UserProfile, Orders, OrderTracking
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

class UserOrderSerializer(serializers.ModelSerializer):
    from worker.serializer import WorkerDetailSerializer

    user = UserGetSerializer(source='user.user_profile', read_only = True)
    order_tracking = UserOrderTrackingSerializer(source='status_tracking',read_only = True)
    worker = serializers.SerializerMethodField(read_only = True)
    service_image = serializers.SerializerMethodField()
    class Meta:
        model = Orders
        fields = ['id', 'user', 'worker', 'order_tracking', 'service_name', 'service_description', 'service_price', 'status', 'service_image', 'user_description', 'created_at']

    def get_service_image(self, instance):
        image_url = create_presigned_url(str(instance.service_image_url))
        if image_url:
            return image_url
        return None
    
    def get_worker(self, instance):
        from worker.serializer import WorkerDetailSerializer
        return WorkerDetailSerializer(instance.service_provider).data
    
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