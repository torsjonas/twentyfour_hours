import random

import math

from decimal import Decimal
from pprint import pprint

from django.core.management import BaseCommand

from core.models import TournamentManager, Game, Tournament, Player, Score, Match


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        round = 1
        matches_in_round = []
        for match in Match.objects.get_active_matches():
            matches_in_round.append(match)
            if match.round != round:
                print("SHISH: %s" % match.round)
                for match in matches_in_round:
                    print(match)
                matches_in_round = []

            round = match.round