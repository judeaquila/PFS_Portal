from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Look up a key in a dictionary dynamically inside Django templates.
    Usage: {{ my_dict|get_item:key_variable }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None