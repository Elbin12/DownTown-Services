from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed

from .models import CustomUser
from worker.models import CustomWorker

from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import APIException
from rest_framework.test import APIRequestFactory

from django.http import JsonResponse
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
import json


class BlockedUserException(APIException):
    status_code = 403  # Forbidden status code
    default_detail = 'You are blocked by admin.'
    default_code = 'blocked_user'

def enforce_csrf(get_response):
    def middleware(request):
        check = CSRFCheck()
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise AuthenticationFailed(f'CSRF Failed: {reason}')
        response = get_response(request)
        return response
    return middleware




class customAuthentication(JWTAuthentication):

    def get_user(self, validated_token):
        user_type = validated_token.get('user_type')
        if user_type == 'user':
            try:
                user = CustomUser.objects.get(id = validated_token['user_id'])
            except CustomUser.DoesNotExist:
                raise AuthenticationFailed('User not found')
            return user
        
        elif user_type == 'worker':
            try:
                worker = CustomWorker.objects.get(id = validated_token['worker_id'])
            except CustomWorker.DoesNotExist:
                raise AuthenticationFailed('User not found')
            return worker
        
        raise AuthenticationFailed('Invalid user type')
             

    def authenticate(self, request):
        from rest_framework_simplejwt.views import TokenRefreshView
        header = self.get_header(request)

        if header is None:
            if request.path.startswith('/worker'):
                raw_token = request.COOKIES.get('worker_access_token')
            elif request.path.startswith('/admin'):
                raw_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE'])
            else:
                raw_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE'])
        else:
            if 'worker' in request.path:
                raw_token = request.headers.get('worker_access_token')
            elif 'admin' in request.path:
                raw_token = request.headers.get(settings.SIMPLE_JWT['AUTH_COOKIE'])
            else:
                raw_token = request.headers.get(settings.SIMPLE_JWT['AUTH_COOKIE'])
        if raw_token is None:
            return None

        try:
            print(raw_token, 'raw')
            validated_token = self.get_validated_token(raw_token)
        except Exception as e:
            print('hi')
            if request.path.startswith('/worker'):
                refresh_token = request.COOKIES.get('worker_refresh_token')
            else:
                refresh_token = request.COOKIES.get('refresh_token')
            if refresh_token is None:
                    raise AuthenticationFailed('Authentication credentials were not provided.')
            try:
                factory = APIRequestFactory()
                token_refresh_request = factory.post('/api/token/refresh/', data=json.dumps({'refresh': refresh_token}), content_type='application/json')

                token_refresh_view = TokenRefreshView.as_view()
                response = token_refresh_view(token_refresh_request)

                if response.status_code == 200:
                    new_access_token = response.data.get('access')
                    validated_token = self.get_validated_token(new_access_token)
                    request.META['NEW_ACCESS_TOKEN'] = new_access_token
            except Exception as e:
                    raise AuthenticationFailed('Refresh token is expired.')

        enforce_csrf(request)
        user = self.get_user(validated_token)
        if not user.is_active:
            if request.path.startswith('/worker'):
                access = 'worker_access_token'
                refresh = 'worker_refresh_token'
                refresh_token = request.COOKIES.get('worker_refresh_token')
            else:
                access = 'access_token'
                refresh = 'refresh_token'
                refresh_token = request.COOKIES.get("refresh_token")
            token = RefreshToken(refresh_token)
            token.blacklist()
            response = JsonResponse({'message': 'You are blocked by admin.'}, status=401)
            response.delete_cookie(refresh)
            response.delete_cookie(access)
            response.delete_cookie('csrftoken')
            raise AuthenticationFailed({'message':'User is blocked by admin.'})
        request.user = user
        return self.get_user(validated_token), validated_token
