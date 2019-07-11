from django import template
from django.db.models import Avg

from core.models import Score, Tournament, median_value
from core.number_util import NumberUtil

from django.utils.translation import ugettext as _

register = template.Library()

@register.filter(name='intdot')
def intdot(value):
    return NumberUtil.format_score(value)

@register.filter(name="game_stats")
def game_stats(game):
    tournament = Tournament.objects.get(is_active=True)
    scores = Score.objects.filter(tournament=tournament, game=game)
    if scores:
        average_score = scores.aggregate(Avg('score'))
        average_score = NumberUtil.format_score(round(average_score["score__avg"], 0))
        median_score = NumberUtil.format_score(median_value(scores, "score"))

        text = ""
        text += _("Number of scores: ") + str(scores.count())
        text += " | "
        text += _("Average score: ") + str(average_score)
        text += " | "
        text += _("Median score: ") + str(median_score)

    return text
