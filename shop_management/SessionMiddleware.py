from django.utils import timezone
from .models import CustomSession

class CustomSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print('\nCookies from the browser:\n',request.COOKIES)
        request.shopkeeper = None
        request.customer = None

        shop_session_id = request.COOKIES.get("SHOPKEEPER_SESSIONID")
        cust_session_id = request.COOKIES.get("CUSTOMER_SESSIONID")
        super_session_id = request.COOKIES.get("SUPERUSER_SESSIONID")
        
        if super_session_id:
            try:
                session = CustomSession.objects.get(session_id = super_session_id)
                if session.expires_at >= timezone.now() and session.user:
                    request.user = session.user
            except CustomSession.DoesNotExist:
                pass
            
        if shop_session_id:
            try:
                session = CustomSession.objects.get(session_id=shop_session_id)
                if session.expires_at >= timezone.now() and session.shopkeeper:
                    request.shopkeeper = session.shopkeeper
            except CustomSession.DoesNotExist:
                pass

        elif cust_session_id:
            try:
                session = CustomSession.objects.get(session_id=cust_session_id)
                if session.expires_at >= timezone.now() and session.customer:
                    request.customer = session.customer
            except CustomSession.DoesNotExist:
                pass

        return self.get_response(request)
