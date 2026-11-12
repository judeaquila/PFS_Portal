from django import template
from dashboard.models import DocumentType
from common.utils import get_document_help_text

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


@register.filter
def document_help(doc_key):
    return get_document_help_text(doc_key)