from django import template

register = template.Library()

@register.filter
def get_teacher_choices(field):
    """Get teacher choices for the template."""
    if hasattr(field, 'queryset'):
        return field.queryset
    return []

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary."""
    return dictionary.get(key)

@register.simple_tag
def define(val=None):
    """Define a variable in template."""
    return val