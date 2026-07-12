from django import template

register = template.Library()


@register.filter
def dict_get(collection, key):
    """Look up `key` in a dict or index a list, safely, from a template."""
    if collection is None:
        return None
    try:
        return collection[key]
    except (KeyError, IndexError, TypeError):
        try:
            return collection.get(key)
        except AttributeError:
            return None
