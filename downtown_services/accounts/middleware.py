from django.conf import settings

class TokenRefreshMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        new_access_token = request.META.get('NEW_ACCESS_TOKEN', None)
        if new_access_token:
            print('from middleware', new_access_token)
            if request.META['USER_TYPE'] == 'worker':
                access = 'worker_access_token'
            else:
                access = settings.SIMPLE_JWT['AUTH_COOKIE']
            response.set_cookie(
            key = access,
            value = new_access_token,
            secure = settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
            httponly = settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
            samesite = settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE']
        )
        return response
        