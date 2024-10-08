from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from games.services import get_today_games

# Create your views here.
class GameViewSet(viewsets.ViewSet):
    @method_decorator(cache_page(60))
    @action(detail=False, methods=['get'])
    def today(self, request):
        games_data = get_today_games()
        games = games_data['resultSets']

        return Response(games)
    
