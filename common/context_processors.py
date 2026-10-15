from accounts.models import UserRole
from common.utils import get_required_document_types

def client_onboarding_status(request):
    """
    Globally injects a boolean variable into all templates 
    indicating if the logged-in regular user completed core uploads.
    """
    if request.user.is_authenticated and request.user.role == UserRole.USER:
        # Check for initial onboarding completion
        initial_required = get_required_document_types(request.user, is_initial=True)
        initial_uploaded_count = request.user.documents.filter(
            document_type__in=initial_required
        ).exclude(file="").count()

        # Check for full compliance approval
        full_required = get_required_document_types(request.user, is_initial=False)
        full_uploaded_count = request.user.documents.filter(
            document_type__in=full_required
        ).exclude(file="").count()
        
        return {
            'is_onboarding_complete': initial_uploaded_count >= len(initial_required),
            'is_fully_compliant': full_uploaded_count >= len(full_required),
        }
        
    return {
        'is_onboarding_complete': False,
        'is_fully_compliant': False,
    }