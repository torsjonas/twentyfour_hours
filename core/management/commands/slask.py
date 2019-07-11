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
        Match.objects.get_active_matches()