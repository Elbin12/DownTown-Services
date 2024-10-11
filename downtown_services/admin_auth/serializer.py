from rest_framework import serializers
from accounts.models import CustomUser, UserProfile
from worker.models import CustomWorker


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