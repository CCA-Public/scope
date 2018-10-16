from django.db.models import FieldDoesNotExist

import math


def add_if_not_empty(data_dict, key, value):
    """Add key/value to dict if the value is truthy"""
    if value:
        data_dict[key] = value


def convert_size(size):
    """
    Convert size to human-readable form using base 2. Should this be using
    using base 10? https://wiki.ubuntu.com/UnitsPolicy
    """
    size_name = ("bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size / p)
    s = str(s)
    s = s.replace('.0', '')
    return '{} {}'.format(s, size_name[i])


def update_instance_from_dict(instance, dict):
    """
    Update model instance attributes from dict key, value pairs.
    Return the updated instance without saving.
    """
    for field, value in dict.items():
        # Check field existence in model instance
        try:
            instance._meta.get_field(field)
        except FieldDoesNotExist:
            continue
        setattr(instance, field, value)
    return instance
