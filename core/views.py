from datetime import datetime

from annoying.functions import get_object_or_None
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.forms import TextInput, ModelForm, CharField, BooleanField
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, CreateView, DetailView

from core.models import Player, Score, Game, Tournament, Points, Match, KeyValue, MatchPoints


class IndexView(TemplateView):
    template_name = "core/index.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        division = self.request.GET.get("division")
        standings, game_scores = Tournament.objects.get_standings_and_game_scores(division)
        active_tournament = get_object_or_None(Tournament, is_active=True)
        context["standings"] = standings
        context["game_scores"] = game_scores
        context["active_tournament"] = active_tournament
        context["has_tiebreak_points"] = False
        context["points"] = Points.objects.all().order_by("-points")
        context["divisions_active"] = False
        context["qualification_rules"] = KeyValue.objects.get_qualification_rules()
        context["display_score_links"] = True

        if active_tournament and (active_tournament.number_of_players_in_a_division
                                  or active_tournament.number_of_players_in_b_division):
            context["divisions_active"] = True

        for standing in standings:
            if standing["tiebreak_points"] != 0:
                context["has_tiebreak_points"] = True

        context["has_match_points"] = False
        for standing in standings:
            if standing["match_points"] != 0:
                context["has_match_points"] = True
        return context


class PlayerForm(ModelForm):

    def clean(self):
        if self.cleaned_data["first_name"] and self.cleaned_data["last_name"] and self.cleaned_data["initials"]:
            player = get_object_or_None(Player, first_name=self.cleaned_data["first_name"],
                                        last_name=self.cleaned_data["last_name"], initials=self.cleaned_data["initials"])
            if player:
                raise ValidationError(_("This player is already registered"))

    class Meta:
        model = Player
        fields = '__all__'


class PlayerCreateView(CreateView):
    template_name = "core/register.html"
    success_url = reverse_lazy('registered')
    model = Player
    form_class = PlayerForm

    def form_valid(self, form):
        # always make the initials to uppercase
        self.object = form.save(commit=False)
        self.object.initials = self.object.initials.upper()
        self.object.save()
        return super().form_valid(form)


class PlayerCreatedView(TemplateView):
    template_name = "core/registered.html"


class RegisteredPlayersView(TemplateView):
    template_name = "core/registered_players.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["players"] = Player.objects.all().order_by("initials")
        return context


class ScoreForm(ModelForm):
    save_player = BooleanField(label=_("Save the selected player for next score registration"), required=False)

    def clean(self):
        if self.cleaned_data["game"] and self.cleaned_data["score"] and self.cleaned_data["player"]:
            tournament = Tournament.objects.get(is_active=True)
            score = get_object_or_None(Score, game=self.cleaned_data["game"], score=self.cleaned_data["score"],
                                       player=self.cleaned_data["player"], tournament=tournament)
            if score:
                raise ValidationError(_("This score has already been registered"))

    def clean_score(self):
        if self.cleaned_data["score"]:
            numbers = ''.join(c for c in self.cleaned_data["score"] if c.isdigit())
            if numbers:
                return numbers

        return self.cleaned_data["score"]

    def save(self, commit=True):
        score = super().save(commit=False)
        if commit:
            score.tournament = Tournament.objects.get(is_active=True)
            score.save()
        return score

    class Meta:
        model = Score
        fields = ["game", "score", "player"]


class ScoreCreateView(CreateView):
    template_name = "core/register_score.html"
    model = Score
    form_class = ScoreForm
    form_id = "score_form"

    def form_valid(self, form):
        response = super().form_valid(form)
        if form.cleaned_data["save_player"]:
            response.set_cookie("preselected_player_id", form.cleaned_data["player"].id,
                                expires=datetime.strptime('2090-02-10' , '%Y-%m-%d'))

        return response

    def get_success_url(self):
        return reverse("registered_score") + "?score_id=%s" % self.object.id

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["score"].widget = TextInput()
        form.fields["score"] = CharField()
        form.fields["score"].help_text = _("Feel free to use separators such as space, comma or dots in the score")
        form.fields["game"].queryset = Game.objects.filter(is_active=True)

        # preselect the player if we have a cookie
        preselected_player_id = self.request.COOKIES.get('preselected_player_id')
        if preselected_player_id:
            player = get_object_or_None(Player, id=preselected_player_id)
            if player:
                form.fields["player"].initial = player


        return form

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        tournament = get_object_or_None(Tournament, is_active=True)
        if tournament and tournament.disable_score_registering:
            if not self.request.user.is_staff:
                raise PermissionDenied()
        context["active_tournament"] = tournament
        context["preselected_player_id"] = self.request.COOKIES.get('preselected_player_id')
        return context


class ScoreCreatedView(TemplateView):
    template_name = "core/registered_score.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        score = get_object_or_404(Score, id=self.request.GET.get("score_id"))
        context["score"] = score
        # ouch, again, get the entire game_scores to show points and position
        standings, game_scores = Tournament.objects.get_standings_and_game_scores(skip_standings=True)
        context["points"] = 0
        for game in game_scores:
            if game == score.game:
                for s in game.scores:
                    if s == score:
                        context["points"] = s.points
                        context["position"] = s.position

        context["score_ends_with_zero"] = (score.score % 10 == 0)

        return context


class MatchesView(TemplateView):
    template_name = "core/matches.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        matches = Match.objects.get_active_matches()
        context["matches"] = matches
        context["match_points"] = get_object_or_None(MatchPoints, id=1)
        # to fix a bug that occurs if the number of players to playoffs in the division
        # is higher than the actual number of players that qualified the "rounds"-bit will
        # be messed up
        context["rounds_are_different"] = False
        first_round = matches[0].round
        for match in matches:
            if match.round != first_round:
                print("RUNNING!")
                context["rounds_are_different"] = True

        return context


@staff_member_required
def create_playoff_matches(request):
    tournament = get_object_or_None(Tournament, is_active=True)
    if tournament and tournament.playoff_matches_are_created:
        messages.add_message(request, messages.ERROR, _("The playoff matches have already been created"))
    else:
        try:
            matches = Match.objects.create_playoff_matches()
            if matches:
                messages.add_message(request, messages.INFO, _("%s playoff matches were created") % len(matches))
            else:
                messages.add_message(request, messages.ERROR, _("No playoff matches were created"))
        except Exception as e:
                messages.add_message(request, messages.ERROR, str(e))

    return HttpResponseRedirect(reverse("admin:core_tournament_changelist"))


class PlayerDetailView(DetailView):
    template_name = "core/player.html"
    model = Player

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        standings, game_scores = Tournament.objects.get_standings_and_game_scores()
        score_overview, total_points = Player.objects.get_score_overview(game_scores, self.object)
        context["score_overview"] = score_overview
        context["total_points"] = total_points

        # clear all game scores which aren't this players'
        cleaned_games = []
        for game in game_scores:
            scores = []
            for score in game.scores:
                if score.player == self.object:
                    scores.append(score)

            game.scores = scores
            if game.scores:
                cleaned_games.append(game)

        context["game_scores"] = cleaned_games

        # set the player's position
        position = None
        for standing in standings:
            if standing["player"] == self.object:
                position = standing["position"]
                break

        context["position"] = position
        context["first_points"] = Points.objects.all().order_by("-points").first()
        return context


class LatestScoresView(TemplateView):
    template_name = "core/latest_scores.html"

    def get_context_data(self, *args, **kwargs):
        limit = 100
        context = super().get_context_data(*args, **kwargs)
        tournament = Tournament.objects.get(is_active=True)
        if tournament:
            context["scores"] = Score.objects.filter(tournament=tournament).order_by("-id")[:limit]

        context["limit"] = limit
        return context


class TopScoresView(TemplateView):
    template_name = "core/top_scores.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["top_scores"] = Score.objects.get_top_scores()
        context["points"] = Points.objects.all()
        return context


def clear_preselected_player(request):
    response = HttpResponseRedirect(reverse("register_score"))
    response.delete_cookie("preselected_player_id")
    return response
