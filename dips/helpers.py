from django.db.models import FieldDoesNotExist
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

import math


def add_if_not_empty(data_dict, key, value):
    """Add key/value to dict if the value is truthy"""
    if value:
        data_dict[key] = value


def convert_size(size):
    """Convert size to human-readable form using base 2.

    Should this be using using base 10? https://wiki.ubuntu.com/UnitsPolicy
    """
    size_name = ("bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size / p)
    s = str(s)
    s = s.replace(".0", "")
    return "{} {}".format(s, size_name[i])


def update_instance_from_dict(instance, dict):
    """Update instance attributes from dict key, value pairs without saving."""
    for field, value in dict.items():
        # Check field existence in model instance
        try:
            instance._meta.get_field(field)
        except FieldDoesNotExist:
            continue
        setattr(instance, field, value)
    return instance


def get_sort_params(params, options, default):
    """Get sort option and direction from params.

    Check options dict. for available choices and use default if no option is passed
    on the paramsor if the option is not valid. Defaults to asc. sort direction.
    """
    option = params.get("sort", default)
    if option not in list(options.keys()):
        option = default

    direction = params.get("sort_dir", "asc")
    if direction not in ["asc", "desc"]:
        direction = "asc"

    return (option, direction)


def get_page_from_search(search, params):
    """Create paginator and return current page.

    Based on the current search and the page and limit parameters. Limit
    defaults to 10 and can't be set over 100. The search parameter can be an
    Elasticsearch search or a Django model QuerySet.
    """
    try:
        limit = int(params.get("limit", 10))
        if limit <= 0 or limit > 100:
            raise ValueError
    except ValueError:
        limit = 10

    paginator = Paginator(search, limit)
    page_no = params.get("page")
    try:
        page = paginator.page(page_no)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    return page
