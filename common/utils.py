from dashboard.models import DocumentType, ProductCategory

def get_required_document_types(user):
    """
    Returns a list of DocumentType choices mandatory for the given user 
    based on their business sector.
    """
    # Base mandatory documents for ALL users
    required = [
        DocumentType.BUSINESS_CERT,
        DocumentType.COMPANY_LOGO,
        DocumentType.BRAND_LOGO,
        DocumentType.PRODUCT_LABEL,
        DocumentType.PRODUCT_PICS,
        DocumentType.FACILITY_SKETCH,
    ]

    if not user or not user.is_authenticated:
        return required

    # Get sector directly from user, or fall back to profile if present
    sector = getattr(user, 'sector', None)
    if sector is None and hasattr(user, 'profile'):
        sector = getattr(user.profile, 'sector', None)

    if not sector:
        return required

    # Convert to uppercase string to prevent Enum comparison mismatches
    sector_str = str(sector).upper()

    # Define sector values as strings
    food_val = str(ProductCategory.FOOD).upper()
    pharma_val = str(ProductCategory.PHARMA).upper()
    food_service_val = str(ProductCategory.FOOD_SERVICE).upper()
    herbal_val = str(ProductCategory.HERBAL).upper()

    # Sector-specific logic
    if sector_str in [food_val, pharma_val, herbal_val]:
        required.extend([
            DocumentType.HEALTH_CARD,
            DocumentType.LAB_RESULTS,
        ])
    elif sector_str == food_service_val:
        required.extend([
            DocumentType.HEALTH_CARD,
            DocumentType.MENU,
            DocumentType.RECIPE_STEPS,
        ])

    return required