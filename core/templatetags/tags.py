from django import template

from core.number_util import NumberUtil

register = template.Library()

@register.filter(name='intdot')
def intdot(value):
    return NumberUtil.format_score(value)

