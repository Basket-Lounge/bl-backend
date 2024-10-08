from django.conf import settings
from django.db.models import Prefetch
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from teams.models import Team, TeamName
from teams.serializers import TeamSerializer
from teams.services import get_all_teams_season_stats, get_last_n_games_log, get_team_franchise_history, get_team_season_stats


# Create your views here.
class TeamViewSet(viewsets.ViewSet):
    @method_decorator(cache_page(60*60*24))
    def retrieve(self, request, pk=None):
        team = Team.objects.prefetch_related(
            Prefetch(
                'teamname_set',
                queryset=TeamName.objects.select_related(
                    'language'
                ).filter(
                    team__id=pk
                ).only('name', 'language__name'),
            )
        ).only(
            'id', 'symbol'
        ).get(
            id=pk
        )

        serializer = TeamSerializer(
            team,
            context={
                'teamname': {
                    'fields': ['name', 'language'],
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        data = serializer.data
        data['stats'] = get_team_season_stats(settings.SEASON_YEAR, pk)

        return Response(data)

    @method_decorator(cache_page(60*60*24)) 
    @action(detail=True, methods=['get'], url_path='franchise-history')
    def get_franchise_history(self, request, pk=None):
        team_franchise_history = get_team_franchise_history(pk)
        return Response(team_franchise_history)

    ## Cache the standings for 10 minutes
    @method_decorator(cache_page(60*10)) 
    @action(detail=False, methods=['get'], url_path='standings')
    def get_standings(self, request):
        relevant_keys = [
            'TeamID',
            'TeamCity',
            'TeamName',
            'Conference',
            'ConferenceRecord',
            'WINS',
            'LOSSES',
            'WinPCT',
            'HOME',
            'ROAD',
            'L10',
            'ClinchedPostSeason',
            'PlayoffSeeding',
        ]
        standings = get_all_teams_season_stats(settings.SEASON_YEAR)

        ## Remove irrelevant keys
        for conference in standings:
            for team in standings[conference]:
                for key in list(team.keys()):
                    if key not in relevant_keys:
                        team.pop(key)

        return Response(standings)

    ## Cache the last 4 games for 1 minute to avoid unnecessary API calls and maintain the freshness of the data
    @method_decorator(cache_page(60*1)) 
    @action(detail=True, methods=['get'], url_path='last-4-games')
    def get_last_4_games(self, request, pk=None):
        game_logs = get_last_n_games_log(pk, 4)
        return Response(game_logs)


class TeamsPostViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'], url_path='top-5')
    def get_today_top_5_popular_posts(self, request):
        return Response({})
    