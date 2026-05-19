from django import template

register = template.Library()


@register.filter
def attr(obj, attr_name):
    """Get an attribute from an object by string name."""
    try:
        return getattr(obj, attr_name)
    except (AttributeError, TypeError):
        return None


@register.filter
def replace(value, arg):
    """Replace substring in value. Arg format: 'old,new'"""
    if not isinstance(value, str):
        value = str(value)
    if ',' in arg:
        old, new = arg.split(',', 1)
        return value.replace(old, new)
    return value


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key."""
    return dictionary.get(key)
