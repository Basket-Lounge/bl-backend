from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
import datetime

from games.services import get_today_games

# Create your views here.
class GameViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'])
    def today(self, request):
        games_data = get_today_games()
        games = games_data['resultSets']

        return Response(games)