from __future__ import unicode_literals

from operator import itemgetter
from pprint import pprint

from annoying.functions import get_object_or_None
from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext as _
from django_countries.fields import CountryField


class BaseModel(models.Model):

    def get_admin_url(self):
        return reverse("admin:%s_%s_change" % (self._meta.app_label, self._meta.model_name), args=(self.id,))

    class Meta:
        abstract = True

def get_points_in_dict():
    points = dict()
    for point in Points.objects.all().order_by("position"):
        points[point.position] = point.points
    return points

class TournamentManager(models.Manager):

    def fix_and_sort_standings(self, standings, points, game_scores, division=None):
        # well, do some weird sorting

        # add number of positions to the player
        if game_scores:
            for game in game_scores:
                position = 1
                for score in game.scores:
                    if position > list(points.keys())[-1]:
                        break
                    standings[score.player.id][position] += 1
                    position += 1

        n = list(points.keys())[-1]
        sorting_method = itemgetter('total_points', 'tiebreak_points', 'player_id', *range(1, n + 1))
        sorted_player_ids = reversed(sorted(standings, key=lambda x: sorting_method(standings[x])))

        sorted_standings = []
        for player_id in sorted_player_ids:
            sorted_standings.append(standings[player_id])

        position_standings = self.add_tiebreak_points_and_position(sorted_standings, points)
        standings = self.set_division_for_standings(position_standings)

        if division:
            position_standings = self.filter_by_division_and_set_position(position_standings, division)

        return position_standings

    def set_division_for_standings(self, standings):
        # set the divisions for the standings, if any
        tournament = get_object_or_None(Tournament, is_active=True)
        if tournament:
            total_number_of_players_in_playoffs = tournament.number_of_players_in_a_division
            if tournament.number_of_players_in_b_division:
                total_number_of_players_in_playoffs += tournament.number_of_players_in_b_division

            if tournament.playoffs_are_active:
                for index, standing in enumerate(standings):
                    position = index + 1
                    if position <= tournament.number_of_players_in_a_division:
                        standing["division"] = "A"
                    elif position <= total_number_of_players_in_playoffs:
                         standing["division"] = "B"
                    else:
                        standing["division"] = None

        return standings

    def filter_by_division_and_set_position(self, standings, division):
        # ouch, getting the entire standings again, without division just to filter out the one's
        # that are in the selected division
        total_standings, dummy = self.get_standings_and_game_scores(get_game_scores=False)
        filtered_standings_player_ids = []
        for standing in total_standings:
            if standing["division"] == division:
                filtered_standings_player_ids.append(standing["player"].id)

        # filter out by division if we have a division, and set the position
        if division:
            division_standings = []
            position = 1
            for standing in standings:
                if standing["player"].id in filtered_standings_player_ids:
                    standing["position"] = position
                    # force the division
                    standing["division"] = division
                    position += 1
                    division_standings.append(standing)

            standings = division_standings

        return standings

    def add_tiebreak_points_and_position(self, standings, points):
        position = 0
        position_standings = []
        previous_standing = None
        for standing in standings:
            increase_position = False
            if not previous_standing or (previous_standing["total_points"] != standing["total_points"]) \
                    or previous_standing["tiebreak_points"]:
                increase_position += True

            if previous_standing and not increase_position:
                for point in points:
                    if previous_standing[point] != standing[point]:
                        increase_position = True

            if increase_position:
                position += 1

            standing["position"] = position
            previous_standing = standing
            position_standings.append(standing)

        return position_standings

    def get_standings_and_game_scores(self, division=None, get_game_scores=True, skip_standings=False):
        standings = []

        if not skip_standings:
            points = get_points_in_dict()
            standings = dict()
            for game in Game.objects.filter(is_active=True):
                player_ids = []
                for index, score in enumerate(Score.objects.active().filter(game=game).order_by("-score")):
                    position = index + 1
                    if not score.player.id in player_ids:
                        # don't award multiple points for the same game for the player
                        if not score.player.id in standings:
                            # no key exists for this player
                            standings[score.player.id] = dict()
                            standings[score.player.id]["player_id"] = score.player.id
                            if position <= list(points.keys())[-1]:
                                standings[score.player.id]["total_points"] = points[position]
                            else:
                                standings[score.player.id]["total_points"] = 0
                            standings[score.player.id]["tiebreak_points"] = 0
                            standings[score.player.id]["match_points"] = 0
                            for point in points:
                                standings[score.player.id][point] = 0
                            standings[score.player.id]["player"] = score.player
                        else:
                            # a key exists for this player
                            if position <= list(points.keys())[-1]:
                                standings[score.player.id]["total_points"] += points[position]
                    player_ids.append(score.player.id)

            # add tiebreak points
            tournament = get_object_or_None(Tournament, is_active=True)
            if tournament:
                for match in Match.objects.filter(tournament=tournament, is_tiebreaker=True):
                    standings[match.winner.id]["tiebreak_points"] += 1

            match_points = MatchPoints.objects.get(id=1)

            # set the high score points and match points for all players
            for player_id in standings:
                standings[player_id]["high_score_points"] = standings[player_id]["total_points"]
                standings[player_id]["match_points"] = 0
                if tournament.playoffs_are_active and division:
                    for match in Match.objects.filter(tournament=tournament, winner=standings[player_id]["player"]):
                        standings[player_id]["total_points"] += match_points.points
                        standings[player_id]["match_points"] += match_points.points

        if get_game_scores:
            game_scores = Game.objects.get_all_scores()
        else:
            game_scores = None

        if not skip_standings:
            return self.fix_and_sort_standings(standings, points, game_scores, division), game_scores
        else:
            return standings, game_scores

class MatchManager(models.Manager):

    def get_active_matches(self):
        tournament = Tournament.objects.get(is_active=True)
        # ouch, get the entire standings just to set the division of the match
        standings, game_scores = Tournament.objects.get_standings_and_game_scores()
        matches = []
        for match in Match.objects.filter(is_tiebreaker=False, tournament=tournament):
            # not an ideal loop, nevertheless
            for standing in standings:
                if standing["player"] == match.player1:
                    match.division = standing["division"]
                    matches.append(match)
                    break

        return matches

    def create_playoff_matches(self):
        tournament = get_object_or_None(Tournament, is_active=True)
        if not tournament:
            raise Exception("There's no active tournament")

        if tournament.playoff_matches_are_created:
            raise Exception("The playoff matches have already been created for the active tournament")


        standings, game_scores = Tournament.objects.get_standings_and_game_scores()
        a_division_standings = []
        b_division_standings = []
        for standing in standings:
            if standing["division"] == "A":
                a_division_standings.append(standing)
            if standing["division"] == "B":
                b_division_standings.append(standing)

        a_division_paired_standings = self.pair_standings(a_division_standings)
        b_division_paired_standings = self.pair_standings(b_division_standings)
        self.create_and_save_matches(a_division_paired_standings, tournament)
        if b_division_paired_standings:
            self.create_and_save_matches(b_division_paired_standings, tournament)

        tournament.playoff_matches_are_created = True
        tournament.save()

    def create_and_save_matches(self, standings, tournament):
        for index in range(0, len(standings), 2):
            player1 = standings[index]["player"]
            player2 = standings[index + 1]["player"]
            # create random playoff matches then
            for game in Game.objects.filter(is_active=True).order_by('?')[:tournament.number_of_playoff_matches]:
                print(game)
                match = Match()
                match.player1 = player1
                match.player2 = player2
                match.game = game
                match.tournament = tournament
                match.save()

    def pair_standings(self, standings):
        upper_standings = standings[:len(standings)//2]
        lower_standings = standings[len(standings)//2:]
        paired_standings = []
        lower_standings_index = len(lower_standings)
        for standing in upper_standings:
            lower_standings_index -= 1
            paired_standings.append(standing)
            paired_standings.append(lower_standings[lower_standings_index])

        return paired_standings

class GameManager(models.Manager):

    def get_all_scores(self):
        points = get_points_in_dict()
        games = []
        for game in Game.objects.filter(is_active=True).order_by("name"):
            games.append(game)
            game.scores = []
            player_ids = []

            for index, score in enumerate(Score.objects.active().filter(game=game).order_by("-score")):
                position = index + 1
                score.position = position
                if position <= list(points.keys())[-1]:
                    if not score.player.id in player_ids:
                        # don't award multiple points for the same game for the player
                        score.points = points[position]
                game.scores.append(score)
                player_ids.append(score.player.id)

        return games

class ScoreManager(models.Manager):

    def active(self):
        tournament = get_object_or_None(Tournament, is_active=True)
        if tournament:
            return Score.objects.filter(tournament=tournament)

        return Score.objects.none()

class Game(models.Model):
    name = models.CharField(max_length=255, unique=True)
    abbreviation = models.CharField(max_length=16, unique=True)
    is_active = models.BooleanField(default=False, null=False, blank=False)

    objects = GameManager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Player(models.Model):
    initials = models.CharField(max_length=3, null=False, blank=False)
    first_name = models.CharField(max_length=4096, null=False, blank=False)
    last_name = models.CharField(max_length=4096, null=False, blank=False)
    email = models.EmailField(null=False, blank=False)
    ifpa_id = models.IntegerField(null=True, blank=True, help_text=_("Not required"))
    country = CountryField(null=False, blank=False)

    def get_url(self):
        return reverse("player_detail", args=[self.id])

    def get_initials_and_name(self):
        return self.initials + " - " + self.first_name + " " + self.last_name

    class Meta:
        ordering = ["initials"]

    def __str__(self):
        return self.initials + " - " + self.first_name + " " + self.last_name


class Score(models.Model):
    game = models.ForeignKey(Game, null=False, blank=False, on_delete=models.PROTECT)
    score = models.BigIntegerField(null=False, blank=False)
    player = models.ForeignKey(Player, null=False, blank=False, on_delete=models.PROTECT)
    tournament = models.ForeignKey("Tournament", null=False, blank=False, on_delete=models.PROTECT)

    objects = ScoreManager()

    class Meta:
        ordering = ["-score"]

    def __str__(self):
        return str(self.game) + " - " + str(self.score) + " - " + str(self.player)

class Points(models.Model):
    position = models.IntegerField(null=False, blank=False)
    points = models.IntegerField(null=False, blank=False)

    class Meta:
        verbose_name_plural = _("Points")
        ordering = ["points"]

    def __str__(self):
        return str(self.position) + " - " + str(self.points)

class Tournament(models.Model):
    is_active = models.BooleanField(default=False)
    start_date = models.DateTimeField(null=False, blank=False)
    end_date = models.DateTimeField(null=False, blank=False)
    name = models.CharField(max_length=255)
    playoffs_are_active = models.BooleanField(default=False)
    playoffs_are_finalized = models.BooleanField(default=False)
    number_of_playoff_matches = models.IntegerField(null=True, blank=True)
    number_of_players_in_a_division = models.IntegerField(null=True, blank=True)
    number_of_players_in_b_division = models.IntegerField(null=True, blank=True)
    playoff_matches_are_created = models.BooleanField(default=False)
    disable_score_registering = models.BooleanField(default=False)

    objects = TournamentManager()

    def __str__(self):
        return str(self.name) + " - " + str(self.start_date) + "-" + str(self.end_date)


class Match(BaseModel):
    player1 = models.ForeignKey(Player, null=False, blank=False, on_delete=models.PROTECT, related_name='match_player1')
    player2 = models.ForeignKey(Player, null=False, blank=False, on_delete=models.PROTECT, related_name='match_player2')
    game = models.ForeignKey(Game, null=False, blank=False, on_delete=models.PROTECT)
    is_tiebreaker = models.BooleanField(default=False)
    winner = models.ForeignKey(Player, null=True, blank=True, on_delete=models.PROTECT, related_name='match_winner')
    tournament = models.ForeignKey(Tournament, null=False, blank=False, on_delete=models.PROTECT)

    objects = MatchManager()

    def player_ids_string(self):
        return str(self.player1) + str(self.player2)

    class Meta:
        verbose_name_plural = _("Matches")

    def __str__(self):
        str =  self.player1.initials + " - " + self.player2.initials
        if self.winner:
            str += " | " + self.winner.initials
        return str

class MatchPoints(models.Model):
    points = models.IntegerField(null=False, blank=False)

    class Meta:
        verbose_name_plural = _("Match points")

    def __str__(self):
        return str(self.points)
