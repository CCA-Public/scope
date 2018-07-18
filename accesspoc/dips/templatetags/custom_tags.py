from django import template

register = template.Library()


@register.filter
def sort_by(queryset, order):
    return queryset.order_by(order)


@register.simple_tag
def update_and_encode_params(querydict, *args, **kwargs):
    """
    Copy the request GET QueryDict and update it with the key/value pairs
    sent in kwargs. Removes key if the value sent is None. Return the updated
    parameters encoded to use in a relative URL.
    """
    copy = querydict.copy()
    for key, value in kwargs.items():
        if not value:
            copy.pop(key, None)
        else:
            copy[key] = value
    return copy.urlencode()
