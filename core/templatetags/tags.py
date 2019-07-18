from django import template

from core.number_util import NumberUtil
from core.models import Game, Player

register = template.Library()

@register.filter(name='intdot')
def intdot(value):
    return NumberUtil.format_score(value)

@register.simple_tag
def get_qualification_url(game, tournament):
    return Game.get_qualification_url(game, tournament)

@register.simple_tag
def get_player_url(player, tournament):
    return Player.get_url(player, tournament)