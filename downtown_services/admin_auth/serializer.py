from rest_framework import serializers
from accounts.models import CustomUser, UserProfile
from worker.models import CustomWorker
from .models import Categories, SubCategories
from worker.models import Services


class GetUsers(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user_profile.first_name', default=None)  
    last_name = serializers.CharField(source='user_profile.last_name', default=None)
    profile_pic = serializers.ImageField(source='user_profile.profile_pic', default=None)
    Name = serializers.SerializerMethodField()
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'mob', 'Name', 'profile_pic', 'is_active']
    
    def get_Name(self, obj):
        user_profile = getattr(obj, 'user_profile', None)
        if user_profile:
            return f"{user_profile.first_name} {user_profile.last_name}"
        return ""
    
class GetWorkers(serializers.ModelSerializer):
    first_name = serializers.CharField(source='worker_profile.first_name', default=None)  
    last_name = serializers.CharField(source='worker_profile.last_name', default=None)
    profile_pic = serializers.ImageField(source='worker_profile.profile_pic', default=None)
    Name = serializers.SerializerMethodField()
    class Meta:
        model = CustomWorker
        fields = ['first_name', 'last_name', 'email', 'mob', 'Name', 'profile_pic', 'is_active']
    
    def get_Name(self, obj):
        worker_profile = getattr(obj, 'worker_profile', None)
        if worker_profile:
            return f"{worker_profile.first_name} {worker_profile.last_name}"
        return ""
    

class GetCategories(serializers.ModelSerializer):
    class Meta:
        model = Categories
        fields = '__all__'

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
    

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Services
        fields = '__all__'
    
    def validate(self, attrs):
        service_name = attrs.get('service_name')
        if Services.objects.filter(service_name=service_name).exists():
            raise serializers.ValidationError('A service with this name is already exists')
        return attrs
    
    def create(self, validated_data):
        return Services.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        for attr in ['service_name', 'description', 'category', 'subcategory', 'pic']:
            value = validated_data.get(attr, getattr(instance, attr))
            setattr(instance, attr, value)
        instance.save()
        return instance
        
