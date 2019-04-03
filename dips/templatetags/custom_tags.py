from django import template

import os

register = template.Library()


@register.filter
def sort_by(queryset, order):
    return queryset.order_by(order)


@register.simple_tag
def update_and_encode_params(querydict, *args, **kwargs):
    """Format parameters for relative URL.

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


@register.filter
def render_label(field):
    """Render field label tag without suffix."""
    return field.label_tag(label_suffix="")


@register.filter
def render_label_with_class(field, class_attr):
    """Add class attribute to field label tag and render without suffix."""
    return field.label_tag(attrs={"class": class_attr}, label_suffix="")


@register.filter
def basename(path):
    """Returns the filename from a path."""
    return os.path.basename(path)
