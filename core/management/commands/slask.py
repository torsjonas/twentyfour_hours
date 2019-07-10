import random

import math

from decimal import Decimal
from django.core.management import BaseCommand

from core.models import TournamentManager, Game, Tournament, Player, Score, Match


def roundup(x):
    return int(math.ceil(Decimal(x) / Decimal(10.0))) * 10

class Command(BaseCommand):


    def handle(self, *args, **kwargs):

        #for match in Match.objects.all():
        #    match.delete()

        #tournament = Tournament.objects.get(is_active=True)
        #tournament.playoff_matches_are_created = False
        #tournament.save()

        #Match.objects.create_playoff_matches()

        #Match.objects.get_active_matches()
        Tournament.objects.get_standings_and_game_scores(division="B")
        #self.generate_scores()

    def generate_scores(self):
        tournament = Tournament.objects.get(is_active=True)
        for x in range(300):
            score = Score()
            score.tournament = tournament
            score.game = Game.objects.filter(is_active=True).order_by('?').first()
            score.player = Player.objects.order_by('?').first()
            score.score = roundup(random.randint(1000000, 15000000000))
            score.save()