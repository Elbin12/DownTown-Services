from rest_framework import serializers
from . models import CustomUser, UserProfile
from admin_auth.models import Categories, SubCategories
from worker.models import Services
from .utils import create_presigned_url



class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['email', 'mob']  

class ProfileSerializer(serializers.ModelSerializer):
    mob = serializers.CharField(source='user.mob')
    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'dob', 'gender', 'profile_pic', 'mob']
    
    def validate(self, data):
        request = self.context.get('request')
        print(request, request.user,data, 'll')
        if CustomUser.objects.filter(mob=data.get('user',{}).get('mob')).exclude(id=request.user.id).exists():
            raise serializers.ValidationError({'mob':'User with this mobile number already exists.'})
        return data

    
    
class UserGetSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email')
    mob = serializers.CharField(source='user.mob')
    is_Active = serializers.BooleanField(source='user.is_active')
    is_Admin = serializers.BooleanField(source='user.is_superuser')
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