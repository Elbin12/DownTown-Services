import logging
import boto3
from botocore.exceptions import ClientError
import random
from django.conf import settings

from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.authentication import JWTAuthentication
from .authenticate import customAuthentication
from math import sin, cos, sqrt, atan2, radians


region_name = settings.AWS_S3_REGION_NAME
bucket_name = settings.AWS_STORAGE_BUCKET_NAME

s3 = boto3.client('s3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=region_name)

def upload_fileobj_to_s3(file_obj, object_name):
    """Upload a file object to an S3 bucket"""

    try:
        s3.upload_fileobj(file_obj, bucket_name, object_name, ExtraArgs={ 'ContentType': file_obj.content_type})
        print("Upload Successful")
        image_url = f"https://{bucket_name}.s3.{region_name}.amazonaws.com/{object_name}"
        return image_url
    except ClientError as e:
        logging.error(e)
        return False
    
def create_presigned_url(object_name, expiration=3600):
    """Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client('s3', region_name=region_name)
    try:
        response = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': bucket_name,
                                                            'Key': object_name},
                                                    ExpiresIn=expiration)
    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL
    return response


class AuthenticateIfJWTProvided(BasePermission):
    def has_permission(self, request, view):
        jwt_auth = customAuthentication()
        try:
            user, _ = jwt_auth.authenticate(request)
            if user:
                request.user = user 
        except Exception:
            pass  

        return True
    
def find_distance(user, worker_profile):
    R = 6373.0

    lat1 = radians(user.lat)
    lon1 = radians(user.lng)
    lat2 = radians(worker_profile.lat)
    lon2 = radians(worker_profile.lng)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c

    return distance

def get_nearby_services(user, services):
    new_services = []
    for service in services:
        distance = find_distance(user, service.worker.worker_profile)
        print(distance, 'dist')
        if distance <= 10:
            new_services.append(service)
        print(service, distance)
    return new_services

def find_distance_for_anonymoususer(lat, lng, worker_profile):
    R = 6373.0

    lat1 = radians(lat)
    lon1 = radians(lng)
    lat2 = radians(worker_profile.lat)
    lon2 = radians(worker_profile.lng)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c

    return distance

def get_nearby_services_for_anonymoususer(lat, lng, services):
    new_services = []
    for service in services:
        distance = find_distance_for_anonymoususer(lat, lng, service.worker.worker_profile)
        print(distance, 'distance')
        if distance <= 10:
            new_services.append(service)
    return new_services

def generate_otp():
    otp = random.randint(100000, 999999)
    return otp