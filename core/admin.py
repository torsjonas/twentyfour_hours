from annoying.functions import get_object_or_None
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.core.exceptions import ValidationError
from django.forms import ModelForm

from core.models import Game, Score, Player, Points, Tournament, Match, MatchPoints
from django.utils.translation import ugettext as _


def activate_games(modeladmin, request, queryset):
    for game in queryset:
        game.is_active = True
        game.save()

activate_games.short_description = _("Activate selected games")


def inactivate_games(modeladmin, request, queryset):
    for game in queryset:
        game.is_active = False
        game.save()

inactivate_games.short_description = _("Inactivate selected games")

class BaseAdmin(admin.ModelAdmin):

    @property
    def media(self):
        media = super().media
        css = {
            "all": (
                "https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.7/css/select2.min.css",
            )
        }
        js = [
            "js/admin.js",
            "js/jquery_fix.js",
            "https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.7/js/select2.min.js",
        ]
        # somewhat hacky to add this to the "private" lists but the code below doesn't work anymore (with Django > 2.0)
        media._css_lists.append(css)
        media._js_lists.append(js)
        #media.add_css(css)
        #media.add_js(js)
        return media

class GameAdmin(ModelAdmin):
    list_display = ("name", "abbreviation", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "abbreviation")
    actions = [activate_games, inactivate_games]


class TournamentForm(ModelForm):

    def clean_is_active(self):
        if self.cleaned_data["is_active"]:
            tournament = get_object_or_None(Tournament, is_active=True)
            if tournament and (tournament != self.instance):
                raise ValidationError(_("There can only be one active tournament. The active tournament is: %s")
                                      % tournament.name)

        return self.cleaned_data["is_active"]

    def clean(self):
        if self.cleaned_data["start_date"] and self.cleaned_data["end_date"]:
            if self.cleaned_data["end_date"] < self.cleaned_data["start_date"]:
                raise ValidationError(_("The start date cannot be before the end date"))

        if self.cleaned_data["playoffs_are_active"]:
            if not self.cleaned_data["number_of_players_in_a_division"] and not \
                    self.cleaned_data["number_of_players_in_b_division"]:
                raise ValidationError(_("You must set the number of players in the divisions if playoffs are active"))

            if not self.cleaned_data["number_of_playoff_matches"]:
                raise ValidationError(_("You must set the number of playoff matches if playoffs are active"))

            if self.cleaned_data["number_of_players_in_b_division"] and not \
                    self.cleaned_data["number_of_players_in_a_division"]:
                raise ValidationError(_("Settings the number of players in the B division only is not allowed"))

        if self.cleaned_data["number_of_players_in_a_division"] and not self.cleaned_data["playoffs_are_active"]:
                raise ValidationError(_("You must set playoffs to active if you set the number of players in A division"))

        if self.cleaned_data["number_of_players_in_a_division"] \
                and self.cleaned_data["number_of_players_in_a_division"] % 2 != 0:
                raise ValidationError(_("Number of players in A division must be an even number"))

        if self.cleaned_data["number_of_players_in_b_division"] \
                and self.cleaned_data["number_of_players_in_b_division"] % 2 != 0:
                raise ValidationError(_("Number of players in B division must be an even number"))

        if self.cleaned_data["number_of_players_in_b_division"] and \
                not self.cleaned_data["number_of_players_in_a_division"]:
                raise ValidationError(_("You must set the number of players in A division if you set "
                                        "the number of players in B division"))

        if self.cleaned_data["number_of_playoff_matches"] and not self.cleaned_data["number_of_players_in_a_division"]:
            raise ValidationError(_("You must set the number of players in A division if you set the number of playoff "
                                    "matches"))

    class Meta:
        model = Tournament
        fields = "__all__"


class TournamentAdmin(BaseAdmin):
    form = TournamentForm
    change_list_template = 'core/admin/tournament_change_list.html'

    search_fields = ("name",)
    list_display = ("name", "is_active", "playoffs_are_active", "start_date", "end_date",
                    "number_of_players_in_a_division", "number_of_players_in_b_division",  "disable_score_registering",
                    "playoff_matches_are_created")
    list_filter = ("is_active", "playoffs_are_active", "start_date",)

class ScoreAdmin(BaseAdmin):
    list_display = ("game", "score", "player", "tournament")
    search_fields = ("game__name", "score", "player__first_name", "player__last_name", "player__initials", "tournament__name")
    list_filter = (('game', admin.RelatedOnlyFieldListFilter), ('player', admin.RelatedOnlyFieldListFilter),
                   ('tournament', admin.RelatedOnlyFieldListFilter),)


class PlayerAdmin(BaseAdmin):
    list_display = ("initials", "first_name", "last_name", "email", "ifpa_id", "country")
    search_fields = ("initials", "first_name", "last_name", "email", "ifpa_id", "country__name")
    list_filter = (('country', admin.RelatedOnlyFieldListFilter),)


class MatchForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tournament = get_object_or_None(Tournament, is_active=True)
        if tournament:
            self.fields["tournament"].initial = tournament

    def clean_winner(self):
        if self.cleaned_data["player1"] and self.cleaned_data["player2"]:
            if (self.cleaned_data["winner"] != self.cleaned_data["player1"]) and (self.cleaned_data["winner"] != self.cleaned_data["player2"]):
                raise ValidationError(_("The winner must be one of the selected players"))
        return self.cleaned_data["winner"]

    class Meta:
        model = Match
        fields = "__all__"


class MatchAdmin(BaseAdmin):
    list_display = ("player1", "player2", "winner", "tournament", "is_tiebreaker")
    search_fields = ("player1__first_name", "player1__last_name", "player1__initials", "player2__first_name",
                     "player2__last_name", "player2__initials", "tournament__name")
    list_filter = (('tournament', admin.RelatedOnlyFieldListFilter), "is_tiebreaker")

    form = MatchForm

admin.site.register(Game, GameAdmin)
admin.site.register(Player, PlayerAdmin)
admin.site.register(Score, ScoreAdmin)
admin.site.register(Points)
admin.site.register(Tournament, TournamentAdmin)
admin.site.register(Match, MatchAdmin)
admin.site.register(MatchPoints)
