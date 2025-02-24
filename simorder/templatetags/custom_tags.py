from django import template
import re
register = template.Library()

@register.filter
def index(indexable, i):
    return indexable[i]

@register.filter
def getattribute(obj, attr):
    return getattr(obj, attr, '')

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def is_hex_color(value):
    if isinstance(value, str):
        return bool(re.match(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', value))
    return False

@register.filter
def get_field_type(model, field_name):
    return model._meta.get_field(field_name).get_internal_type()