from rest_framework import serializers
from . models import CustomUser, UserProfile



class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['email', 'mob']  

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'dob', 'gender', 'profile_pic']

    
    
class UserGetSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email')
    mob = serializers.CharField(source='user.mob')
    is_Active = serializers.BooleanField(source='user.is_active')
    is_Admin = serializers.BooleanField(source='user.is_superuser')
    class Meta:
        model = UserProfile
        fields = ['email', 'mob', 'first_name', 'last_name', 'dob', 'gender', 'profile_pic', 'is_Active', 'is_Admin']
