from rest_framework import serializers
from accounts.models import CustomUser, UserProfile
from worker.models import CustomWorker
from .models import Categories, SubCategories, Services


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
        if Categories.objects.filter(category_name=category_name).exists():
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