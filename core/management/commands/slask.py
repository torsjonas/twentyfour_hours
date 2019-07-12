import random

import math

from decimal import Decimal
from pprint import pprint

from django.core.management import BaseCommand

from core.models import TournamentManager, Game, Tournament, Player, Score, Match


def roundup(x):
    return int(math.ceil(Decimal(x) / Decimal(10.0))) * 10


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        '''
        for match in Match.objects.get_active_matches():
            print(match.round)
        '''
        for match in Match.objects.all():
            match.delete()

        '''
        tournament = Tournament.objects.get(is_active=True)
        tournament.playoff_matches_are_created = False
        tournament.save()
        Match.objects.create_playoff_matches()
        '''