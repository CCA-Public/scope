from django import template
from django.contrib.auth.models import Group

register = template.Library()


@register.filter
def sort_by(queryset, order):
    return queryset.order_by(order)


@register.filter(name='has_group')
def has_group(user, group_name):
    group = Group.objects.get(name=group_name)
    return True if group in user.groups.all() else False
