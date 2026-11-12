from dashboard.models import DocumentType, ProductCategory

DOCUMENT_HELP_TEXTS = {
    DocumentType.BUSINESS_CERT: "Upload a clear, scanned copy of your business certificate.",
    DocumentType.COMPANY_LOGO: "Provide a high-resolution PNG or JPEG image of your company logo.",
    DocumentType.BRAND_LOGO: "Provide a high-resolution PNG or JPEG image of your brand logo.",
    DocumentType.PRODUCT_LABEL: "Provide a high-resolution PNG or JPEG image of your product label.",
    DocumentType.PRODUCT_PICS: "Provide photos of your product(s) with the label on it.",
    DocumentType.FACILITY_SKETCH: "A simple layout drawn with a pen on paper or an actual architectural floor plan.",
    DocumentType.HEALTH_CARD: "You can get this from your district assembly.",
    DocumentType.LAB_RESULTS: "Upload copies of laboratory results for your product(s).",
}

def get_document_help_text(doc_key):
    """Returns the custom help text for a given document type key, or a default message."""
    # Convert key to string/enum safe lookup
    return DOCUMENT_HELP_TEXTS.get(
        doc_key, 
        f"Please upload clear, legible files for this requirement."
    )

def get_required_document_types(user, is_initial=False):
    """
    Returns a list of DocumentType choices mandatory for the given user 
    based on their business sector and registration stage.
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
        if not is_initial:
            required.extend([
                DocumentType.HEALTH_CARD,
                DocumentType.LAB_RESULTS,
            ])
    elif sector_str == food_service_val:
        if not is_initial:
            required.append(DocumentType.HEALTH_CARD)
        
        required.extend([
            DocumentType.MENU,
            DocumentType.RECIPE_STEPS,
        ])

    return required