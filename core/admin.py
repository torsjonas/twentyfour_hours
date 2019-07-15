from annoying.functions import get_object_or_None
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.contrib import messages

from core.models import Game, Score, Player, Points, Tournament, Match, KeyValue
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

def activate_games_in_playoff(modeladmin, request, queryset):
    for game in queryset:
        game.is_active_in_playoffs = True
        game.save()

activate_games_in_playoff.short_description = _("Activate game in playoffs")

def inactivate_games_in_playoff(modeladmin, request, queryset):
    for game in queryset:
        game.is_active_in_playoffs = False
        game.save()

inactivate_games_in_playoff.short_description = _("Inactivate game in playoffs")


def inactivate_games(modeladmin, request, queryset):
    for game in queryset:
        game.is_active = False
        game.save()

inactivate_games.short_description = _("Inactivate selected games")

def set_active_tournament(modeladmin, request, queryset):
    if queryset.count() > 1:
        messages.add_message(request, messages.ERROR, _("Please select one tournament only"))

    if queryset.count() == 1:
        tournament = queryset[0]
        tournament.is_active = True
        tournament.save()

        for t in Tournament.objects.all():
            if t != tournament:
                t.is_active = False
                t.save()

set_active_tournament.short_description = _("Set the selected tournament as active")

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
    list_display = ("name", "abbreviation", "is_active", "is_active_in_playoffs")
    list_filter = ("is_active", "is_active_in_playoffs")
    search_fields = ("name", "abbreviation")
    actions = [activate_games, inactivate_games, activate_games_in_playoff, inactivate_games_in_playoff]


class TournamentForm(ModelForm):

    def clean_is_active(self):
        if self.cleaned_data["is_active"]:
            tournament = get_object_or_None(Tournament, is_active=True)
            if tournament and (tournament != self.instance):
                raise ValidationError(_("There can only be one active tournament. The active tournament is: %s")
                                      % tournament.name)

        return self.cleaned_data["is_active"]

    def clean(self):

        if "start_date" in self.cleaned_data and "end_date" in self.cleaned_data:
            if self.cleaned_data["end_date"] < self.cleaned_data["start_date"]:
                raise ValidationError(_("The start date cannot be before the end date"))

        if self.cleaned_data["playoffs_are_active"]:
            if not self.cleaned_data["number_of_players_in_a_division"] and not \
                    self.cleaned_data["number_of_players_in_b_division"]:
                raise ValidationError(_("You must set the number of players in the divisions if playoffs are active"))

            if not self.cleaned_data["match_points"]:
                raise ValidationError(_("You must set match points if playoffs are active"))

            if not self.cleaned_data["number_of_rounds_against_opponents"]:
                raise ValidationError(_("You must set the number of rounds against opponents matches if playoffs are active"))

            if self.cleaned_data["number_of_players_in_b_division"] and not \
                    self.cleaned_data["number_of_players_in_a_division"]:
                raise ValidationError(_("Settings the number of players in the B division only is not allowed"))

        if self.cleaned_data["number_of_players_in_a_division"] and not self.cleaned_data["playoffs_are_active"]:
                raise ValidationError(_("You must set playoffs to active if you set the number of players in A division"))

        if self.cleaned_data["number_of_players_in_b_division"] and \
                not self.cleaned_data["number_of_players_in_a_division"]:
                raise ValidationError(_("You must set the number of players in A division if you set "
                                        "the number of players in B division"))

        if self.cleaned_data["number_of_rounds_against_opponents"] and not self.cleaned_data["number_of_players_in_a_division"]:
            raise ValidationError(_("You must set the number of players in A division if you set the number of rounds "
                                    "against opponents"))

        if self.cleaned_data["number_of_players_in_a_division"] and self.cleaned_data["number_of_players_in_a_division"] < 2:
            raise ValidationError(_("The number of players in A division must be at least 2"))

        if self.cleaned_data["number_of_players_in_b_division"] and self.cleaned_data["number_of_players_in_b_division"] < 2:
            raise ValidationError(_("The number of players in B division must be at least 2"))

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
    actions = [set_active_tournament]

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["active_playoff_games"] = Game.objects.filter(is_active_in_playoffs=True).order_by("name")
        return super().changelist_view(request, extra_context=extra_context)


class ScoreAdmin(BaseAdmin):
    list_display = ("game", "score", "player", "tournament", "date_created")
    search_fields = ("game__name", "score", "player__first_name", "player__last_name", "player__initials", "tournament__name")
    list_filter = (('game', admin.RelatedOnlyFieldListFilter), ('player', admin.RelatedOnlyFieldListFilter),
                   ('tournament', admin.RelatedOnlyFieldListFilter),)
    readonly_fields = ["date_created", "tournament"]


class PlayerAdmin(BaseAdmin):
    list_display = ("initials", "first_name", "last_name", "email", "ifpa_id", "country")
    search_fields = ("initials", "first_name", "last_name", "email", "ifpa_id")
    list_filter = ('country',)


class MatchForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tournament = get_object_or_None(Tournament, is_active=True)
        if "tournament" in self.fields:
            self.fields["tournament"].initial = tournament

    def clean(self):
        if "division" in self.cleaned_data:
            if not self.cleaned_data["division"]:
                raise ValidationError(_("You must select the division"))

                if self.cleaned_data["division"] != "A" and self.cleaned_data["division"] != "B":
                    raise ValidationError(_("The division must be A or B"))

    def clean_winner(self):
        if self.cleaned_data["winner"]:
            if "player1" in self.cleaned_data and "player2" in self.cleaned_data:
                if self.cleaned_data["player1"] and self.cleaned_data["player2"]:
                    if (self.cleaned_data["winner"] != self.cleaned_data["player1"]) and (self.cleaned_data["winner"] != self.cleaned_data["player2"]):
                        raise ValidationError(_("The winner must be one of the selected players"))
        return self.cleaned_data["winner"]

    class Meta:
        model = Match
        fields = "__all__"


class MatchAdmin(BaseAdmin):
    list_display = ("player1", "player2", "game", "winner", "tournament", "is_tiebreaker", "date_created", "division")
    search_fields = ("player1__first_name", "player1__last_name", "player1__initials", "player2__first_name",
                     "player2__last_name", "player2__initials", "tournament__name")
    list_filter = (('tournament', admin.RelatedOnlyFieldListFilter), "division", "is_tiebreaker")
    readonly_fields = ["date_created"]
    form = MatchForm

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if request.GET.get("set_winner") == "true":
            readonly_fields.append('is_tiebreaker')
            readonly_fields.append('date_created')
            readonly_fields.append('division')
            readonly_fields.append('game')
            readonly_fields.append('tournament')
        return readonly_fields

    class Media:
        js = ("js/match.js",)

admin.site.register(Game, GameAdmin)
admin.site.register(Player, PlayerAdmin)
admin.site.register(Score, ScoreAdmin)
admin.site.register(Points)
admin.site.register(Tournament, TournamentAdmin)
admin.site.register(Match, MatchAdmin)
admin.site.register(KeyValue)
