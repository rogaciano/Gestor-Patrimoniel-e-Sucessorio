from django import template

register = template.Library()

@register.filter
def class_name(obj):
    """Retorna o nome da classe do objeto"""
    return obj.__class__.__name__
