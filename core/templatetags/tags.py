from django import template
from django.utils import numberformat

register = template.Library()

@register.filter(name='intdot')
def intdot(value):
    return numberformat.format(value, decimal_sep='', decimal_pos=0, grouping=3, thousand_sep='.', force_grouping=True)
