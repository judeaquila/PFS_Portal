from django.core.exceptions import PermissionDenied

def role_required(allowed_roles=None):
    allowed_roles = allowed_roles or []

    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if str(request.user.role) not in [str(role) for role in allowed_roles]:
                raise PermissionDenied
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator