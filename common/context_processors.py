from dashboard.models import DocumentType

def client_onboarding_status(request):
    """
    Globally injects a boolean variable into all templates 
    indicating if the logged-in regular user completed core uploads.
    """
    if request.user.is_authenticated and request.user.role == 'USER':
        required_types = [
            DocumentType.BUSINESS_CERT,
            DocumentType.HEALTH_CARD,
            DocumentType.FACILITY_SKETCH
        ]
        uploaded_count = request.user.documents.filter(
            document_type__in=required_types
        ).exclude(file="").count()
        
        return {
            'is_onboarding_complete': uploaded_count >= len(required_types)
        }
        
    return {'is_onboarding_complete': False}