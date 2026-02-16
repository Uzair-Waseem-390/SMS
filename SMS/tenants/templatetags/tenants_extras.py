# tenants/templatetags/tenants_extras.py
from django import template

register = template.Library()

# @register.filter
# def get_item(dictionary, key):
#     """Get an item from a dictionary by key."""
#     return dictionary.get(key)

@register.filter
def get_item(obj, key):
    try:
        return obj[key]
    except (TypeError, KeyError):
        return None

@register.filter
def add(value, arg):
    """Add the arg to the value."""
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        return value