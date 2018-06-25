"""Helper functions for dips app"""


def add_if_not_empty(data_dict, key, value):
    """Add key/value to dict if the value is truthy"""
    if value:
        data_dict[key] = value
