from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings

from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken


from rest_framework.authentication import CSRFCheck
import jwt
import requests


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
    def authenticate(self, request):
        print('hello')
        header = self.get_header(request)
        print('Header:', header)

        if header is None:
            print('header')
            raw_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE'])
        else:
            print('else')
            raw_token = self.get_raw_token(header)
            print('raw_tokenn', raw_token)
        if raw_token is None:
            return None
        print('raw_token', raw_token)

        try:
            print('entered')
            validated_token = self.get_validated_token(raw_token)
            print('valid')
        except Exception as e:
            print(e, 'err')
            print('jhjhj')
            refresh_token = request.COOKIES.get('refresh_token')
            if refresh_token is None:
                    raise AuthenticationFailed('Authentication credentials were not provided.')
            try:
                print('kkk')
                # refresh = RefreshToken(refresh_token)
                response = requests.post(
                    "http://localhost:8000/api/token/refresh/",
                    data={'refresh': refresh_token}
                )
                if response.status_code == 200:
                    new_access_token = response.json().get('access')
                    print(new_access_token, 'new')
                validated_token = self.get_validated_token(new_access_token)
                print('created', new_access_token)
            except Exception as e:
                    print('jjjj', e)
                    raise AuthenticationFailed('Refresh token is expired.')


        enforce_csrf(request)
        user = self.get_user(validated_token)
        request.user = user
        print(f'Authenticated user: {user}')
        return self.get_user(validated_token), validated_token