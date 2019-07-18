from django.conf.urls import url

from core import views
from core.views import IndexView, PlayerCreateView, PlayerCreatedView, RegisteredPlayersView, ScoreCreateView, \
    ScoreCreatedView, MatchesView, PlayerDetailView, LatestScoresView, TopScoresView, TournamentsView

urlpatterns = [
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^register/$', PlayerCreateView.as_view(), name='register'),
    url(r'^register/done/$', PlayerCreatedView.as_view(), name='registered'),
    url(r'^registered-players/$', RegisteredPlayersView.as_view(), name='registered_players'),
    url(r'^register-score/$', ScoreCreateView.as_view(), name='register_score'),
    url(r'^register-score/done$', ScoreCreatedView.as_view(), name='registered_score'),
    url(r'^matches/$', MatchesView.as_view(), name='matches'),
    url(r'player/(?P<pk>\d+)/$', PlayerDetailView.as_view(), name = 'player_detail'),
    url(r'^playoff-matches/create/$', views.create_playoff_matches, name='create_playoff_matches'),
    url(r'^scores/latest/$', LatestScoresView.as_view(), name='latest_scores'),
    url(r'^scores/top/$', TopScoresView.as_view(), name='top_scores'),
    url(r'^tournaments/$', TournamentsView.as_view(), name='tournaments')
]
