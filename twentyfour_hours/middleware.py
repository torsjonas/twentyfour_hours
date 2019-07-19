from annoying.functions import get_object_or_None
from core.models import Tournament

class SetTournamentMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # On each request before the views are called, set the tournament on the request object
        # to avoid repeating this in all views.
        tournament_id = request.GET.get("tournament")
        if tournament_id:
            request.tournament = get_object_or_None(Tournament, id=tournament_id)
        else:
            request.tournament = get_object_or_None(Tournament, is_active=True)

        response = self.get_response(request)
        return response