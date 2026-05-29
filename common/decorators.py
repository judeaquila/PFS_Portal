from django.core.exceptions import PermissionDenied
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from dashboard.models import DocumentType, DocumentStatus

# CUSTOM ROLES
def role_required(allowed_roles=None):
    allowed_roles = allowed_roles or []

    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if str(request.user.role) not in [str(role) for role in allowed_roles]:
                raise PermissionDenied
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# CHECK MANDATORY FILES UPLOADED
def mandatory_docs_required(view_func):
    """
    Django view decorator that ensures a regular User has fully uploaded 
    and verified all mandatory core compliance documents before granting access 
    to deeper platform features.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 1. Fallback guard: ensure we are dealing with an authenticated regular user
        if not request.user.is_authenticated or request.user.role != 'USER':
            return view_func(request, *args, **kwargs)

        # 2. Define the absolute mandatory statutory checklist items
        required_types = [
            DocumentType.BUSINESS_CERT,
            DocumentType.HEALTH_CARD,
            DocumentType.FACILITY_SKETCH
        ]
        required_count = len(required_types)

        # 3. Query the database for valid, payload-containing files matching our checklist
        uploaded_count = request.user.documents.filter(
            document_type__in=required_types
        ).exclude(file="").count()

        # 4. Enforce the gate: if the tally falls short, redirect them to the tracker page
        if uploaded_count < required_count:
            messages.warning(
                request, 
                "Access Restricted: Please complete your mandatory regulatory document uploads to unlock full workspace controls."
            )
            
            return redirect('dashboard:user-dashboard')

        return view_func(request, *args, **kwargs)
        
    return _wrapped_view