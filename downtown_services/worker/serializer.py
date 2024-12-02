from rest_framework import serializers
from .models import CustomWorker, Services, Requests, WorkerProfile
from django.contrib.auth.hashers import make_password   
from accounts.serializer import ProfileSerializer, ReviewSerializer
import os, json
from datetime import datetime
from accounts.utils import upload_fileobj_to_s3, create_presigned_url
from admin_auth.models import Categories
from accounts.models import Review, Orders
from django.db.models import Avg

class WorkerRegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)
    location = serializers.CharField(source='worker_profile.location', required=True)
    lat = serializers.DecimalField(source='worker_profile.lat', max_digits=25, decimal_places=20, required=False)
    lng = serializers.DecimalField(source='worker_profile.lng', max_digits=25, decimal_places=20, required=False)
    aadhaar_no = serializers.CharField(source='worker_profile.aadhaar_no', required=True, allow_blank=True)
    experience = serializers.IntegerField(source='worker_profile.experience', required=True)
    certificate = serializers.ImageField(source='worker_profile.certificate', required=True)
    services = services = serializers.ListField(
        required=True,
        allow_empty=True,   
        write_only=True 
    )

    class Meta:
        model = CustomWorker
        fields = ['email', 'mob', 'password', 'confirm_password', 'location', 'lat', 'lng', 'aadhaar_no', 'experience', 'certificate', 'services']
        extra_kwargs = {
            'password': {'write_only': True} 
        }

    
    def validate(self, data):
        print(data, 'daata')
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({'password': "Passwords do not match."})
        
        workerprofile = data.get('worker_profile', {})
        services = data.pop('services', [])
        print(services, workerprofile, 'iiii')
        if services:
            if isinstance(services, list):
                workerprofile['services'] = [item for sublist in services for item in sublist]
                print('Flattened services:', workerprofile['services'])
        data['worker_profile'] = workerprofile
        return data

    
    def create(self, validated_data):
        profile_data = validated_data.pop('worker_profile', {})
        cert_img = profile_data.pop('certificate', None)
        services = profile_data.pop('services', [])

        validated_data.pop('confirm_password')
        validated_data['password'] = make_password(validated_data['password'])

        groups_data = validated_data.pop('groups', None)
        permissions_data = validated_data.pop('user_permissions', None)
        
        worker = CustomWorker.objects.create(**validated_data)
        profile = WorkerProfile.objects.create(user=worker, **profile_data)

        if cert_img:
            file_extension = os.path.splitext(cert_img.name)[1]
            current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{current_time_str}{file_extension}"
            s3_file_path = f"workers/certificate/{unique_filename}"
            try:
                image_url = upload_fileobj_to_s3(cert_img, s3_file_path)
                if image_url:
                    profile.certificate = s3_file_path
                    print("Image URL:", image_url)
                else:
                    raise Exception("File upload to S3 failed")
            except Exception as e:
                print(e)
                raise serializers.ValidationError({'certificate': str(e)})

        if services:
            profile.services.set(services)
        
        profile.save()

        if groups_data:
            worker.groups.set(groups_data)
        if permissions_data:
            worker.user_permissions.set(permissions_data)

        return worker
    
class WorkerLoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomWorker
        fields = ['email', 'password']

class WorkerDetailSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='worker_profile.id', read_only=True)
    first_name = serializers.CharField(source='worker_profile.first_name')
    last_name = serializers.CharField(source='worker_profile.last_name',required=False, allow_null=True)
    dob = serializers.DateField(source='worker_profile.dob', required=False, allow_null=True)
    gender = serializers.CharField(source='worker_profile.gender', required=False, allow_null=True)
    profile_pic = serializers.SerializerMethodField()
    email = serializers.EmailField(required=False)
    mob = serializers.CharField()
    isWorker = serializers.BooleanField(source='is_staff')
    lat = serializers.DecimalField(source='worker_profile.lat',max_digits=9, decimal_places=6, read_only = True)
    lng = serializers.DecimalField(source='worker_profile.lng',max_digits=9, decimal_places=6, read_only = True)
    location = serializers.CharField(source='worker_profile.location', read_only = True)
    rating = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()

    class Meta:
        model = CustomWorker
        fields = [
            'id', 'email', 'mob', 'status', 'is_active', 'isWorker', 'date_joined',
            'first_name', 'last_name', 'dob', 'gender', 'profile_pic', 'lat', 'lng', 'location', 'reviews', 'rating'
        ]

    def validate(self, data):
        request = self.context.get('request')
        print(request, request.user, 'll')
        if CustomWorker.objects.filter(mob=data.get('mob')).exclude(id=request.user.id).exists():
            raise serializers.ValidationError({'mob':'worker with this mobile number already exists.'})
        return data
    
    def get_profile_pic(self, obj):
        image_url = create_presigned_url(str(obj.worker_profile.profile_pic))
        if image_url:
            return image_url
        return None
    
    def get_reviews(self, obj):
        orders = Orders.objects.filter(service_provider=obj)
        reviews = Review.objects.filter(order__in=orders)
        return ReviewSerializer(reviews, many=True,context=self.context).data
    
    def get_rating(self, obj):
        orders = Orders.objects.filter(service_provider=obj)
        average_rating = (
            Review.objects.filter(order__in=orders)
            .aggregate(avg_rating=Avg('rating'))['avg_rating']
        )
        return round(average_rating, 1) if average_rating else 0
    
class RequestsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requests
        fields = '__all__'


class ServiceListingSerializer(serializers.ModelSerializer):
    pic = serializers.SerializerMethodField()
    class Meta:
        model = Services
        fields = '__all__'

    def get_pic(self, instance):
        image_url = create_presigned_url(str(instance.pic))
        if image_url:
            return image_url
        return None

class ServiceSerializer(serializers.ModelSerializer):
    workerProfile = WorkerDetailSerializer(source='worker', read_only=True)
    category_name = serializers.CharField(source='category.category_name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.subcategory_name', read_only=True) 
    pic = serializers.SerializerMethodField()
    status = serializers.BooleanField(default=True, read_only=True)

    class Meta:
        model = Services
        fields = ['workerProfile', 'id', 'worker', 'service_name', 'description','category', 'subcategory', 'category_name', 'subcategory_name', 'pic', 'price', 'is_active', 'status' ]
        read_only_fields = ['worker']
    
    def validate(self, attrs):
        service_name = attrs.get('service_name')
        worker = self.context['request'].user
        if self.instance is None:
            if Services.objects.filter(service_name__icontains=service_name, worker=worker).exists():
                raise serializers.ValidationError({
                    'status': False,
                    'message': 'A service with this name already exists'
                })
        else:
            if Services.objects.filter(service_name=service_name, worker=worker).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError({'message': 'A service with this name already exists'})
        return attrs
    
    def create(self, validated_data):
        worker = self.context.get('request').user
        validated_data['worker'] = worker
        print(validated_data, 'validated')
        validated_data['is_active'] = True
        pic = self.context['request'].FILES.get('pic')
        if pic:
            file_extension = os.path.splitext(pic.name)[1]
            current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{current_time_str}{file_extension}"
            s3_file_path = f"services/{unique_filename}"
            image_url = upload_fileobj_to_s3(pic, s3_file_path)
            validated_data['pic'] = s3_file_path
            print("Image URL:", image_url)
        return Services.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        pic = self.context.get('request').FILES.get('pic')
        if pic:
            file_extension = os.path.splitext(pic.name)[1]
            current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{current_time_str}{file_extension}"
            s3_file_path = f"services/{unique_filename}"
            image_url = upload_fileobj_to_s3(pic, s3_file_path)
            validated_data['pic'] = s3_file_path
        for attr in ['service_name', 'description', 'category', 'subcategory', 'pic', 'price']:
            value = validated_data.get(attr, getattr(instance, attr))
            setattr(instance, attr, value)
        instance.save()
        return instance
    
    def get_pic(self, instance):
        image_url = create_presigned_url(str(instance.pic))
        if image_url:
            return image_url
        return None

class ServiceListingDetailSerializer(serializers.ModelSerializer):
    workerProfile = WorkerDetailSerializer(source='worker', read_only=True)
    category_name = serializers.CharField(source='category.category_name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.subcategory_name', read_only=True) 
    pic = serializers.SerializerMethodField()
    status = serializers.BooleanField(default=True, read_only=True)
    request = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Services
        fields = ['workerProfile', 'request', 'id', 'worker', 'service_name', 'description','category', 'subcategory', 'category_name', 'subcategory_name', 'pic', 'price', 'status' ]
        read_only_fields = ['worker']

    def get_request(self, obj):
        user = self.context.get('request').user
        print(user)
        if user.is_authenticated:
            service_request = Requests.objects.filter(user=user, service=obj).first()
            if service_request:
                return RequestsSerializer(service_request).data
        return False
    
    def get_pic(self, instance):
        image_url = create_presigned_url(str(instance.pic))
        if image_url:
            return image_url
        return None
    
class RequestListingDetails(serializers.ModelSerializer):
    user = ProfileSerializer(source='user.user_profile')
    service = ServiceListingSerializer()
    class Meta:
        model = Requests
        fields = [ 'id', 'user', 'service', 'description', 'status']