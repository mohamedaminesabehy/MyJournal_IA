from django import template

register = template.Library()

@register.filter
def dict_key(key, dictionary):
    """Retrieve a value from a dict safely in templates"""
    return dictionary.get(key, key)
