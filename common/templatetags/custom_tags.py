from django import template
from dashboard.models import DocumentType

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if dictionary:
        return dictionary.get(key)
    return None


@register.filter
def choice_label(doc_key):
    try:
        return DocumentType[doc_key].label
    except (KeyError, AttributeError):
        return doc_key.replace('_', ' ').title()