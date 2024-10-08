from django.urls import include, path
from games.views import GameViewSet
from players.views import PlayersViewSet
from rest_framework.routers import DefaultRouter

from teams.views import TeamViewSet, TeamsPostViewSet

router = DefaultRouter()
router.register(r'games', GameViewSet, basename='game')
router.register(r'players', PlayersViewSet, basename='player')
router.register(r'teams', TeamViewSet, basename='team')
router.register(r'teams/posts', TeamsPostViewSet, basename='post')

urlpatterns = [
    path('', include(router.urls)),
]