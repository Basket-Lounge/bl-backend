from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from nba_api.stats.endpoints.leagueleaders import LeagueLeaders

# Create your views here.
class PlayersViewSet(viewsets.ViewSet):
    @method_decorator(cache_page(60*60))
    @action(detail=False, methods=['get'], url_path='top-10')
    def get_top_10_players(self, request):
        leaders = LeagueLeaders(
            league_id='00',
            per_mode48='PerGame',
            scope='S',
            season='2023-24',
            season_type_all_star='Regular Season',
            stat_category_abbreviation='PTS'
        )
        results = leaders.get_dict()
        top_10 = results['resultSet']['rowSet'][:10]
        results['resultSet']['rowSet'] = top_10

        return Response(results)