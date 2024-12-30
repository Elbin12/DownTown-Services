from rest_framework import serializers
from accounts.models import CustomUser, UserProfile
from worker.models import CustomWorker
from .models import Categories, SubCategories, Subscription
from worker.models import Services
from accounts.utils import create_presigned_url
import stripe


class GetUsers(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user_profile.first_name', default=None)  
    last_name = serializers.CharField(source='user_profile.last_name', default=None)
    profile_pic = serializers.ImageField(source='user_profile.profile_pic', default=None)
    Name = serializers.SerializerMethodField()
    profile_pic = serializers.SerializerMethodField()
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'mob', 'Name', 'profile_pic', 'is_active']
    
    def get_Name(self, obj):
        user_profile = getattr(obj, 'user_profile', None)
        if user_profile:
            return f"{user_profile.first_name} {user_profile.last_name if user_profile.last_name is not None else ''}"
        return ""
    
    def get_profile_pic(self, instance):
        user_profile = getattr(instance, 'user_profile', None)
        if user_profile:
            image_url = create_presigned_url(str(user_profile.profile_pic))
            if image_url:
                return image_url
        return None
    
class GetWorkers(serializers.ModelSerializer):
    first_name = serializers.CharField(source='worker_profile.first_name', default=None)  
    last_name = serializers.CharField(source='worker_profile.last_name', default=None)
    Name = serializers.SerializerMethodField()
    profile_pic = serializers.SerializerMethodField()
    location = serializers.CharField(source='worker_profile.location', required=True)
    lat = serializers.DecimalField(source='worker_profile.lat', max_digits=25, decimal_places=20)
    lng = serializers.DecimalField(source='worker_profile.lng', max_digits=25, decimal_places=20)
    aadhaar_no = serializers.CharField(source='worker_profile.aadhaar_no')
    experience = serializers.CharField(source='worker_profile.experience')
    certificate = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()
    class Meta:
        model = CustomWorker
        fields = ['first_name', 'last_name', 'email', 'mob', 'Name', 'profile_pic', 'is_active', 'status', 'id', 'location', 'lat', 'lng', 'aadhaar_no', 'experience', 'certificate', 'services']

    def get_services(self, obj):
        worker_profile = getattr(obj, 'worker_profile', None)
        if worker_profile and worker_profile.services.exists():
            services = worker_profile.services.all()
            return GetCategoriesOnly(services, many=True).data
        return []
    
    def get_Name(self, obj):
        worker_profile = getattr(obj, 'worker_profile', None)
        if worker_profile:
            return f"{worker_profile.first_name} {worker_profile.last_name if worker_profile.last_name else ''}"
        return ""
    
    def get_profile_pic(self, instance):
        worker_profile = getattr(instance, 'worker_profile', None)
        if worker_profile and worker_profile.profile_pic:
            image_url = create_presigned_url(str(worker_profile.profile_pic))
            if image_url:
                return image_url
        return None
    
    def get_certificate(self, instance):
        worker_profile = getattr(instance, 'worker_profile', None)
        if worker_profile and worker_profile.certificate:
            image_url = create_presigned_url(str(worker_profile.certificate))
            if image_url:
                return image_url
        return None	
    
class GetCategoriesOnly(serializers.ModelSerializer):
    class Meta:
        model = Categories
        fields = '__all__'

class GetSubcategories(serializers.ModelSerializer):
    class Meta:
        model = SubCategories
        fields = '__all__'
    

class GetCategories(serializers.ModelSerializer):
    subcategories = GetSubcategories(many=True, read_only=True)
    class Meta:
        model = Categories
        fields = ['id', 'category_name', 'subcategories']

    def validate(self, attrs):
        category_name = attrs.get('category_name')
        if self.instance is None:
            if Categories.objects.filter(category_name=category_name).exists():
                raise serializers.ValidationError("A category with this name already exists.")
        else:
            if Categories.objects.filter(category_name=category_name).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError("A category with this name already exists.")
        return attrs
    
    def create(self, validated_data):
        return Categories.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        category_name = validated_data.get('category_name', instance.category_name)

        if category_name is None:
            raise serializers.ValidationError("Category name cannot be null.")

        instance.category_name = category_name
        instance.save()
        return instance
    
class SubcategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategories
        fields = '__all__'

    def validate(self, attrs):
        subcategory_name = attrs.get('subcategory_name')
        if self.instance is None:
            if SubCategories.objects.filter(subcategory_name=subcategory_name).exists():
                raise serializers.ValidationError('A sub-category with this name is already exist.')
        else:
            if SubCategories.objects.filter(subcategory_name=subcategory_name).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError('A sub-category with this name is already exist.')
        return attrs
    
    def create(self, validated_data):
        return SubCategories.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        subcategory_name = validated_data.get('subcategory_name', instance.subcategory_name)

        if not subcategory_name:
            raise serializers.ValidationError('Sub-category name cannot be null')
        
        category_id = validated_data.get('category_id')
        if category_id:
            try:
                category = Categories.objects.get(id=category_id)
                instance.category = category
            except Categories.DoesNotExist:
                raise serializers.ValidationError('Category with this ID does not exist.')

        instance.subcategory_name = subcategory_name
        instance.save()
        return instance
    

        
class SubscriptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ['id', 'tier_name', 'price', 'is_active', 'created_at', 'platform_fee_perc', 'service_add_limit', 'service_update_limit', 'user_requests_limit', 'analytics']

    def validate(self, attrs):
        tier_name = attrs.get('tier_name')
        if self.instance is None:
            if Subscription.objects.filter(tier_name=tier_name).exists():
                raise serializers.ValidationError('A subscription with this tier name is already exist.')
        else:
            if Subscription.objects.filter(tier_name=tier_name).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError('A subscription with this tier name is already exist.')
        return attrs
    
    def create(self, validated_data):
        print(validated_data, 'data')
        try:
            product = stripe.Product.create(name=validated_data.get('tier_name'))
            price = stripe.Price.create(
                unit_amount=int(validated_data.get('price') * 100),
                currency="inr",
                recurring={"interval": "month"},
                product=product.id,
            )
            validated_data['stripe_product_id'] = product.id
            validated_data['stripe_price_id'] = price.id
        except Exception as e:
            return serializers.ValidationError(f'Error at stripe :{e}')
        subscription = Subscription.objects.create(**validated_data)
        return subscription
    
    def update(self, instance, validated_data):
        print(validated_data, 'ddd')
        tier_name = validated_data.get('tier_name', instance.tier_name)
        price = validated_data.get('price', instance.price)
        platform_fee_perc = validated_data.get('platform_fee_perc', instance.platform_fee_perc)
        service_add_limit = validated_data.get('service_add_limit', instance.service_add_limit)
        service_update_limit = validated_data.get('service_update_limit', instance.service_update_limit)
        user_requests_limit = validated_data.get('user_requests_limit', instance.user_requests_limit)
        analytics = validated_data.get('analytics', instance.analytics)

        print(price, 'price')
        if not tier_name:
            raise serializers.ValidationError('Tier name cannot be null')
        if price is None:
            raise serializers.ValidationError('Price cannot be null')

        instance.tier_name = tier_name
        instance.price = price
        instance.platform_fee_perc = platform_fee_perc
        instance.service_add_limit = service_add_limit
        instance.service_update_limit = service_update_limit
        instance.user_requests_limit = user_requests_limit
        instance.analytics = analytics
        
        instance.save()
        return instance