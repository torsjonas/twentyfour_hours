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


class KeyValueManager(models.Manager):

    def get_qualification_rules(self):
        return get_object_or_None(KeyValue, key="qualification_rules")

class MatchManager(models.Manager):

    def get_division_matches(self, matches, division):
        division_matches = []
        for match in matches:
            if match.division == division:
                division_matches.append(match)

        return division_matches

    def get_active_matches(self, tournament):
        matches = Match.objects.filter(is_tiebreaker=False, tournament=tournament)
        # set the round of the matches
        a_division_matches = self.get_division_matches(matches, "A")
        b_division_matches = self.get_division_matches(matches, "B")
        self.set_round_of_matches(a_division_matches, "A", tournament)
        self.set_round_of_matches(b_division_matches, "B", tournament)
        return matches

    def set_round_of_matches(self, matches, division, tournament):
        round_number = 1
        division_standings = tournament.get_division_standings(division)
        odd = False
        if len(division_standings) % 2 != 0:
            odd = True

        if not odd:
            number_of_matches_per_round = len(division_standings) / 2
        else:
            number_of_matches_per_round = round(len(division_standings) / 2)

        for index, match in enumerate(matches):
            match_number = index + 1
            match.round = round_number
            if match_number % number_of_matches_per_round == 0:
                round_number += 1

    def create_playoff_matches(self, tournament):
        if not tournament or not tournament.is_active:
            raise Exception("There's no active tournament")

        if not tournament.playoffs_are_active:
            raise Exception("Playoffs are not active for the active tournament")

        if tournament.playoff_matches_are_created:
            raise Exception("The playoff matches have already been created for the active tournament")

        standings, dummy = tournament.get_standings_and_game_scores(get_game_scores=False)
        a_division_standings = []
        b_division_standings = []
        for standing in standings:
            if "division" in standing:
                if standing["division"] == "A":
                    a_division_standings.append(standing)
                if standing["division"] == "B":
                    b_division_standings.append(standing)

        for i in range(0, tournament.number_of_rounds_against_opponents):
            matches = self.create_and_save_matches(a_division_standings, tournament, "A")

        if b_division_standings:
            for i in range(0, tournament.number_of_rounds_against_opponents):
                matches.extend(self.create_and_save_matches(b_division_standings, tournament, "B"))

        if matches:
            tournament.playoff_matches_are_created = True
            tournament.save()

        return matches

    def get_player_ids_from_standings(self, standings):
        player_ids = []
        for standing in standings:
            player_ids.append(standing["player"].id)
        return player_ids

    def pair_players_and_matches(self, standings, odd=False):
        # make this player 1-5 to make it debuggable
        paired_matches = []
        upper_half_standings = standings[:len(standings)//2]
        lower_half_standings = standings[len(standings)//2:]
        first_player_ids = self.get_player_ids_from_standings(upper_half_standings)
        second_player_ids = self.get_player_ids_from_standings(lower_half_standings)

        rounds_paired = 0
        first_player_id = first_player_ids[0]

        if odd:
            # add a dummy player if it's odd
            first_player_ids.append("dummy")

        # special case for only two players
        if len(standings) == 2:
            first_player_ids.append("dummy")
            second_player_ids.append("dummy")

        while rounds_paired < len(first_player_ids + second_player_ids) - 1:
            for i, player_id in enumerate(first_player_ids):
                match = dict()
                match["player_1"] = first_player_ids[i]
                match["player_2"] = second_player_ids[i]
                paired_matches.append(match)

            rounds_paired += 1
            first_second_players_id = second_player_ids[0]
            last_first_players_id = first_player_ids[-1]

            # move all values in first_player_ids to the right, except the first, and add the first second_player_ids
            # id to the 2nd position
            first_player_ids = [first_player_ids[-1]] + first_player_ids[:-1]
            first_player_ids[0] = first_player_id
            first_player_ids[1] = first_second_players_id

            # move all values in second_player_ids to the left and add the last first_players_id to the last position
            # of second_player_ids
            second_player_ids = second_player_ids[1:] + second_player_ids[:1]
            second_player_ids[-1] = last_first_players_id

        return paired_matches

    def create_and_save_matches(self, standings, tournament, division):
        matches = []
        odd = False
        if len(standings) % 2 != 0:
            odd = True

        paired_matches = self.pair_players_and_matches(standings, odd=odd)
        number_of_players = len(standings)
        number_of_active_games = Game.objects.filter(is_active_in_playoffs=True).count()

        if number_of_players > number_of_active_games:
            raise Exception("There are not enough active games to create playoff matches")

        # store the player's standings to determine the playing order
        player_standings = dict()
        for standing in standings:
            player_standings[standing["player"].id] = standing["position"]

        matches_per_round = len(standings) - 1
        games_in_round = []

        for index, paired_match in enumerate(paired_matches):
            create_match = True
            if paired_match["player_1"] == "dummy" or paired_match["player_2"] == "dummy":
                create_match = False

            if create_match:
                if matches_per_round > number_of_active_games:
                    # there are not enough active games to cover the rounds, just get a random game
                    game = self.get_random_playoff_game()
                else:
                    if len(games_in_round) == 0:
                        game = self.get_random_playoff_game()
                        games_in_round.append(game)
                    else:
                        game = self.get_distributed_game(games_in_round)
                        games_in_round.append(game)

                    player_1_position = player_standings[paired_match["player_1"]]
                    player_2_position = player_standings[paired_match["player_2"]]

                    if player_1_position > player_2_position:
                        player1 = Player.objects.get(id=paired_match["player_1"])
                        player2 = Player.objects.get(id=paired_match["player_2"])
                    else:
                        player1 = Player.objects.get(id=paired_match["player_2"])
                        player2 = Player.objects.get(id=paired_match["player_1"])

                    if len(games_in_round) == matches_per_round:
                        # empty the games in the round then
                        games_in_round = []

                    match = self.create_match(player1, player2, game, tournament, division)
                    matches.append(match)

        return matches

    def get_distributed_game(self, games_in_round):
        game = self.get_random_playoff_game()
        if game in games_in_round:
            return self.get_distributed_game(games_in_round)
        else:
            return game

    def get_random_playoff_game(self):
        return Game.objects.filter(is_active_in_playoffs=True).order_by('?').first()

    def create_match(self, player1, player2, game, tournament, division):
        match = Match()
        match.game = game
        match.player1 = player1
        match.player2 = player2
        match.game = game
        match.tournament = tournament
        match.division = division
        match.save()
        return match


class GameManager(models.Manager):

    def get_all_scores(self, tournament):
        points = get_points_in_dict()
        games = []
        for game in Game.objects.filter(is_active=True).order_by("name"):
            games.append(game)
            game.scores = []
            player_ids = []

            scores = Score.objects.filter(tournament=tournament, game=game).order_by("-score")
            for index, score in enumerate(scores):
                position = index + 1
                score.position = position
                score.points = 0
                if position <= list(points.keys())[-1]:
                    if not score.player.id in player_ids:
                        # don't award multiple points for the same game for the player
                        score.points = points[position]
                game.scores.append(score)
                player_ids.append(score.player.id)

        return games


class PlayerManager(models.Manager):

    def get_score_overview(self, game_scores, player):
        # now these loops truly suck ... the game_scores are used since they have the position and points
        score_overview = []
        total_points = 0

        for ordered_game in Game.objects.filter(is_active=True).order_by("name"):
            overview = dict()
            for game in game_scores:
                # mixing dicts and object properties here, d-oh
                overview["game"] = game
                overview["score"] = None
                overview["points"] = 0
                overview["position"] = None

                if ordered_game == game:
                    for score in game.scores:
                        if score.player == player:
                            overview["score"] = score
                            overview["points"] = score.points
                            overview["position"] = score.position
                            total_points += score.points
                        if score.player == player:
                            break
                        else:
                            continue
                    break

            score_overview.append(overview)

        return score_overview, total_points


class ScoreManager(models.Manager):

    def active(self):
        tournament = get_object_or_None(Tournament, is_active=True)
        if tournament:
            return Score.objects.filter(tournament=tournament)

        return Score.objects.none()

    def get_top_scores(self, tournament):
        limit = Points.objects.all().count()
        standings, game_scores = tournament.get_standings_and_game_scores(skip_standings=True)
        for game in game_scores:
            game.top_scores = []
            for index, score in enumerate(game.scores):
                if (index + 1) > limit:
                    break
                game.top_scores.append(score)

        # make sure we fill out the positions in the game scores:
        for game in game_scores:
            if len(game.top_scores) != limit:
                for i in range(len(game.top_scores), limit):
                    game.top_scores.append(None)

        return game_scores


class Game(models.Model):
    name = models.CharField(max_length=255, unique=True)
    abbreviation = models.CharField(max_length=16, unique=True)
    is_active = models.BooleanField(default=False, null=False, blank=False)
    is_active_in_playoffs = models.BooleanField(default=False)
    is_canceled = models.BooleanField(default=False)

    objects = GameManager()

    @staticmethod
    def get_qualification_url(game, tournament):
        return "/?tournament=" + str(tournament.id) + "&q=true#" + str(game.id)

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

    objects = PlayerManager()

    @staticmethod
    def get_url(player, tournament):
        return "/player/" + str(player.id) + "?tournament=" + str(tournament.id)

    def get_ifpa_url(self):
        if self.ifpa_id:
            return "https://www.ifpapinball.com/player.php?p=%s" % self.ifpa_id
        return None

    def get_initials_and_name(self):
        return self.initials + " - " + self.first_name + " " + self.last_name

    class Meta:
        ordering = ["initials"]

    def __str__(self):
        return self.initials + " - " + self.first_name + " " + self.last_name


class Score(BaseModel):
    game = models.ForeignKey(Game, null=False, blank=False, on_delete=models.PROTECT)
    score = models.BigIntegerField(null=False, blank=False)
    date_created = models.DateTimeField(auto_now_add=True, null=False, blank=False)
    player = models.ForeignKey(Player, null=False, blank=False, on_delete=models.PROTECT)
    tournament = models.ForeignKey("Tournament", null=False, blank=False, on_delete=models.PROTECT)

    objects = ScoreManager()

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
    match_points = models.IntegerField(null=True, blank=True)
    number_of_players_in_a_division = models.IntegerField(null=True, blank=True)
    number_of_players_in_b_division = models.IntegerField(null=True, blank=True)
    number_of_rounds_against_opponents = models.IntegerField(null=True, blank=True)
    disable_score_registering = models.BooleanField(default=False)
    playoff_matches_are_created = models.BooleanField(default=False,
          help_text=_("Don't touch this unless you really know what you are doing"))

    def a_division_is_finalized(self):
        for match in Match.objects.filter(tournament=self, division="A"):
            if not match.winner:
                return False

        return True

    def b_division_is_finalized(self):
        # duplicated-ish code from a_division_is_finalized ... d-oh!
        for match in Match.objects.filter(tournament=self, division="B"):
            if not match.winner:
                return False

        return True

    def is_a_division_only(self):
        if self.number_of_players_in_a_division and not self.number_of_players_in_b_division:
            return True
        return False

    def is_multiple_division(self):
        if self.number_of_players_in_a_division and self.number_of_players_in_b_division:
            return True
        return False

    def has_playoff_matches(self):
        if Match.objects.filter(tournament=self).count() > 0:
            return True
        return False

    def get_standings_and_game_scores(self, division=None, get_game_scores=True, skip_standings=False):
        standings = []

        if not skip_standings:
            points = get_points_in_dict()
            standings = dict()
            for game in Game.objects.filter(is_active=True):
                player_ids = []
                scores = Score.objects.filter(tournament=self, game=game).order_by("-score")

                for index, score in enumerate(scores):
                    position = index + 1
                    if not score.player.id in player_ids:
                        # don't award multiple points for the same game for the player
                        if not score.player.id in standings:
                            # no key exists for this player
                            standings[score.player.id] = dict()
                            standings[score.player.id]["player_id"] = score.player.id
                            if position <= list(points.keys())[-1]:
                                if not game.is_canceled:
                                    standings[score.player.id]["total_points"] = points[position]
                                else:
                                    # don't award points on canceled games
                                    standings[score.player.id]["total_points"] = 0
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
                                if not game.is_canceled:
                                    standings[score.player.id]["total_points"] += points[position]
                                else:
                                    # don't award points on canceled games
                                    standings[score.player.id]["total_points"] += 0

                    player_ids.append(score.player.id)

            # add tiebreak points
            for match in Match.objects.filter(tournament=self, is_tiebreaker=True):
                standings[match.winner.id]["tiebreak_points"] += 1

            if self.match_points:
                # set the high score points and match points for all players
                for player_id in standings:
                    standings[player_id]["high_score_points"] = standings[player_id]["total_points"]
                    standings[player_id]["match_points"] = 0
                    if self.playoffs_are_active and division:
                        for match in Match.objects.filter(tournament=self, winner=standings[player_id]["player"]):
                            standings[player_id]["total_points"] += self.match_points
                            standings[player_id]["match_points"] += self.match_points

        if get_game_scores:
            game_scores = Game.objects.get_all_scores(self)
        else:
            game_scores = None

        if not skip_standings:
            return self.fix_and_sort_standings(standings, points, game_scores, division), game_scores
        else:
            return standings, game_scores

    def fix_and_sort_standings(self, standings, points, game_scores, division=None):
        # well, do some weird sorting

        # add number of positions to the player
        if game_scores and points:
            for game in game_scores:
                position = 1
                for score in game.scores:
                    if position > list(points.keys())[-1]:
                        break
                    standings[score.player.id][position] += 1
                    position += 1

        position_standings = []

        if points:
            n = list(points.keys())[-1]
            # https://stackoverflow.com/questions/56947847/sort-nested-dictionary-by-variable-number-of-keys
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

    def set_division_for_standings(self, standings):
        # set the divisions for the standings, if any)
        total_number_of_players_in_playoffs = self.number_of_players_in_a_division
        if self.number_of_players_in_b_division:
            total_number_of_players_in_playoffs += self.number_of_players_in_b_division

        if self.playoffs_are_active:
            for index, standing in enumerate(standings):
                position = index + 1
                if position <= self.number_of_players_in_a_division:
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
            if ("division" in standing) and standing["division"] == division:
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

    def get_division_standings(self, division):
        standings, dummy = self.get_standings_and_game_scores(get_game_scores=False)
        filtered_standings = []
        for standing in standings:
            if standing["division"] == division:
                filtered_standings.append(standing)

        return filtered_standings

    objects = models.Manager()

    def __str__(self):
        return str(self.name) + " - " + str(self.start_date) + "-" + str(self.end_date)


class Match(BaseModel):
    winner_help_text = """If you need other options in the select please select Player 1 and Player 2 and click 'Save and continue editing'"""

    player1 = models.ForeignKey(Player, null=False, blank=False, on_delete=models.PROTECT, related_name='match_player1')
    player2 = models.ForeignKey(Player, null=False, blank=False, on_delete=models.PROTECT, related_name='match_player2')
    game = models.ForeignKey(Game, null=False, blank=False, on_delete=models.PROTECT)
    is_tiebreaker = models.BooleanField(default=False)
    winner = models.ForeignKey(Player, null=True, blank=True, on_delete=models.PROTECT, related_name='match_winner',
                               help_text=winner_help_text)
    date_created = models.DateTimeField(auto_now_add=True, null=False, blank=False)
    division = models.CharField(max_length=1, null=True, blank=True)
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


class KeyValue(models.Model):
    key = models.CharField(max_length=255, null=False, blank=False)
    value = models.TextField(max_length=49152, null=False, blank=False)

    objects = KeyValueManager()

    def __str__(self):
        return self.key


