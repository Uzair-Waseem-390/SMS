from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def sb_url(context, url_name, *args, **kwargs):
    """
    URL tag that automatically injects school_id and branch_id.
    Usage:
        {% sb_url 'finance:dashboard' %}
        {% sb_url 'finance:fee_detail' fee.id %}
        {% sb_url 'finance:fee_detail' fee_id=fee.id %}
    """
    request = context.get('request')
    school = getattr(request, 'current_school', None) if request else None
    branch = getattr(request, 'current_branch', None) if request else None

    if not school:
        school = context.get('current_school')
    if not branch:
        branch = context.get('current_branch')

    if school and branch:
        if args:
            args = (school.id, branch.id) + args
            return reverse(url_name, args=args)
        else:
            kwargs['school_id'] = school.id
            kwargs['branch_id'] = branch.id
            return reverse(url_name, kwargs=kwargs)

    if args:
        return reverse(url_name, args=args)
    return reverse(url_name, kwargs=kwargs if kwargs else None)
