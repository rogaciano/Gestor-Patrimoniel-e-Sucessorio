import json
from .models import OperacaoLog

class AuditlogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Logar apenas ações de modificação (POST, PUT, DELETE)
        # Check if user is authenticated to avoid errors
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE'] and getattr(request, 'user', None) and request.user.is_authenticated:
            try:
                # Capture payload safely
                payload = None
                if request.POST:
                    payload = json.dumps(request.POST.dict())
                
                OperacaoLog.objects.create(
                    usuario=request.user,
                    acao=request.method,
                    tabela=request.path,
                    ip_address=self.get_client_ip(request),
                    payload_depois=payload
                    # Note: payload_antes requires pre-fetching object which is harder in generic middleware without specific signals or pre-process checks.
                )
            except Exception as e:
                # Fail silently or log error to system log to not crash request
                print(f"Audit Log Error: {e}")
                pass
                
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
