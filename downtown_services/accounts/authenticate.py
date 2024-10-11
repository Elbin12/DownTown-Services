from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings

from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser
from worker.models import CustomWorker

from rest_framework.authentication import CSRFCheck
import jwt
import requests
from rest_framework.exceptions import APIException
from rest_framework.test import APIRequestFactory


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
            validated_token = self.get_validated_token(raw_token)
        except Exception as e:
            if request.path.startswith('/worker'):
                refresh_token = request.COOKIES.get('worker_refresh_token')
            else:
                refresh_token = request.COOKIES.get('refresh_token')
            if refresh_token is None:
                    raise AuthenticationFailed('Authentication credentials were not provided.')
            try:
                factory = APIRequestFactory()
                token_refresh_request = factory.post('/api/token/refresh/', {'refresh': refresh_token})

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
            raise AuthenticationFailed({'message':'You are blocked by admin.'})
        request.user = user
        return self.get_user(validated_token), validated_token
