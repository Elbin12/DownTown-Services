from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings

from rest_framework.authentication import CSRFCheck
from rest_framework import exceptions



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

        validated_token = self.get_validated_token(raw_token)
        enforce_csrf(request)
        user = self.get_user(validated_token)
        print(f'Authenticated user: {user}')
        return self.get_user(validated_token), validated_token