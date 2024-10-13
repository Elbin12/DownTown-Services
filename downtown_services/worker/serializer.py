from rest_framework import serializers
from .models import WorkerProfile, CustomWorker
from django.contrib.auth.hashers import make_password   



class WorkerRegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)
    class Meta:
        model = CustomWorker
        fields = ['email', 'mob', 'password', 'confirm_password']
        extra_kwargs = {
            'password': {'write_only': True} 
        }

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({'password': "Passwords do not match."})
        return data

    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        validated_data['password'] = make_password(validated_data['password'])
        groups_data = validated_data.pop('groups', None)
        permissions_data = validated_data.pop('user_permissions', None)
        
        worker = CustomWorker.objects.create(**validated_data)

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
    first_name = serializers.CharField(source='worker_profile.first_name')
    last_name = serializers.CharField(source='worker_profile.last_name',required=False, allow_null=True)
    dob = serializers.DateField(source='worker_profile.dob', required=False, allow_null=True)
    gender = serializers.CharField(source='worker_profile.gender', required=False, allow_null=True)
    profile_pic = serializers.ImageField(source='worker_profile.profile_pic', allow_null=True, required=False)
    email = serializers.EmailField(required=False)
    mob = serializers.CharField()
    isWorker = serializers.BooleanField(source='is_staff')

    class Meta:
        model = CustomWorker
        fields = [
            'email', 'mob', 'status', 'is_active', 'isWorker', 'date_joined',
            'first_name', 'last_name', 'dob', 'gender', 'profile_pic'
        ]

    def validate(self, data):
        request = self.context.get('request')
        print(request, request.user, 'll')
        if CustomWorker.objects.filter(mob=data.get('mob')).exclude(id=request.user.id).exists():
            raise serializers.ValidationError({'mob':'worker with this mobile number already exists.'})
        return data

