from annoying.functions import get_object_or_None

from core.models import Tournament
from django.utils.translation import ugettext as _

def globals(request):
    tournament = get_object_or_None(Tournament, is_active=True)
    page_title = _("Pinball tournament system 0.6")
    if tournament:
        page_title = tournament.name

    return {
        'TOURNAMENT': tournament,
        'PAGE_TITLE': page_title
    }
