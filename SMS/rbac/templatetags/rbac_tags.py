from django import template
from rbac.services import RBACService

register = template.Library()

@register.filter
def has_permission(user, permission_code):
    return RBACService().user_has_permission(user, permission_code)

@register.filter
def has_any_permission(user, permission_codes):
    codes = permission_codes.split(',')
    return RBACService().user_has_any_permission(user, codes)