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

    def validate(self, data):
        if not data.first_name:
            raise serializers.ValidationError("First Name is requierd.")
        if not data.last_name:
            raise serializers.ValidationError("First Name is requierd.")
        
        return data
    
    
    
class UserGetSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email')
    mob = serializers.CharField(source='user.mob')
    class Meta:
        model = UserProfile
        fields = ['email', 'mob', 'first_name', 'last_name', 'dob', 'gender', 'profile_pic']
