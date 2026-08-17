import functools
from django.core.exceptions import PermissionDenied
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from dashboard.models import DocumentType, DocumentStatus
from .utils import get_required_document_types
from accounts.models import UserRole


# CUSTOM ROLES
def role_required(allowed_roles=None):
    allowed_roles = allowed_roles or []
    allowed_roles_str = [str(role) for role in allowed_roles]

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')

            user_role = getattr(request.user, 'role', None)
            
            if str(user_role) not in allowed_roles_str and not request.user.is_superuser:
                raise PermissionDenied

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator



# CONTROL FRONTEND ACCESS
def restrict_to_regular_users(view_func):
    """
    Redirects logged-in non-regular users to the dashboard dispatcher.
    Allows unauthenticated visitors and regular users through.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            if str(request.user.role) != UserRole.USER:
                return redirect('dashboard:redirect-dashboard')
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


# RESTRICT ACCESS TO LOGIN & REGISTRATION PAGES
def anonymous_required(view_func):
    """
    Prevents authenticated users from accessing login/registration pages.
    Redirects them to the dashboard dispatcher instead.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard:redirect-dashboard')
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


# CHECK MANDATORY FILES UPLOADED
def mandatory_docs_required(view_func):
    """
    Django view decorator that ensures a regular User has fully uploaded 
    and verified all mandatory core compliance documents before granting access 
    to deeper platform features.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'USER':
            return view_func(request, *args, **kwargs)

        # Dynamic required list based on client's industry/sector
        required_types = get_required_document_types(request.user)
        required_count = len(required_types)

        # Exclude rejected or empty files from valid uploads count
        valid_uploaded_count = request.user.documents.filter(
            document_type__in=required_types,
            status__in=[DocumentStatus.PENDING, DocumentStatus.APPROVED]
        ).exclude(file="").count()

        if valid_uploaded_count < required_count:
            messages.warning(
                request, 
                "Access Restricted: Please upload all required compliance documents for your business."
            )
            return redirect('dashboard:user-dashboard')

        return view_func(request, *args, **kwargs)

    return _wrapped_view