from django.conf import settings
from django.db.models import Prefetch
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_404_NOT_FOUND
from rest_framework.permissions import IsAuthenticated

from games.services import combine_games_and_linescores
from teams.models import Team, TeamName
from teams.serializers import TeamSerializer
from teams.services import (
    get_all_games_for_team_this_season,
    get_all_teams_season_stats, 
    get_last_n_games_log,
    get_player_last_n_games_log,
    get_monthly_games_for_team_this_season,
    get_player_career_stats,
    get_player_current_season_stats, 
    get_team_franchise_history,
    get_team_players, 
    get_team_season_stats
)
from teams.utils import convert_month_string_to_int

from users.authentication import CookieJWTAccessAuthentication

from nba_api.stats.endpoints.scoreboardv2 import ScoreboardV2


# Create your views here.
class TeamViewSet(viewsets.ViewSet):
    authentication_classes = [CookieJWTAccessAuthentication]

    # def get_permissions(self):
    #     permission_classes = []
    #     if self.action == 'retrieve':
    #         permission_classes = [IsAuthenticated]

    #     return [permission() for permission in permission_classes]

    @method_decorator(cache_page(60*5))
    def retrieve(self, request, pk=None):
        print(request.user)
        team = None
        try:
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
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=HTTP_404_NOT_FOUND)

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
    def list(self, request):
        teams = Team.objects.prefetch_related(
            Prefetch(
                'teamname_set',
                queryset=TeamName.objects.select_related(
                    'language'
                ).all()
            )
        ).only(
            'id', 'symbol'
        ).order_by('symbol').all()

        serializer = TeamSerializer(
            teams,
            many=True,
            context={
                'teamname': {
                    'fields': ['name', 'language'],
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        return Response(serializer.data)

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
            'TeamAbbreviation',
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
    
    @method_decorator(cache_page(60*10))
    @action(detail=True, methods=['get'], url_path='players')
    def get_players(self, request, pk=None):
        players = get_team_players(pk)
        return Response(players)

    @method_decorator(cache_page(60*10))
    @action(detail=True, methods=['get'], url_path=r'players/(?P<player_id>[^/.]+)/career-stats') 
    def get_specific_player(self, request, pk=None, player_id=None):
        players = get_team_players(pk)
        for player in players:
            if player['PERSON_ID'] == int(player_id):
                return Response(get_player_career_stats(player_id))

        return Response(status=HTTP_404_NOT_FOUND)
    
    @method_decorator(cache_page(60*10))
    @action(detail=True, methods=['get'], url_path=r'players/(?P<player_id>[^/.]+)/season-stats')
    def get_specific_player_season_stats(self, request, pk=None, player_id=None):
        players = get_team_players(pk)
        for player in players:
            if player['PERSON_ID'] == int(player_id):
                return Response(get_player_current_season_stats(player_id, team_id=pk))

        return Response(status=HTTP_404_NOT_FOUND)

    @method_decorator(cache_page(60*10)) 
    @action(detail=True, methods=['get'], url_path=r'players/(?P<player_id>[^/.]+)/last-5-games')
    def get_specific_player_last_5_games(self, request, pk=None, player_id=None):
        players = get_team_players(pk)
        for player in players:
            if player['PERSON_ID'] == int(player_id):
                return Response(get_player_last_n_games_log(player_id, 5))

        return Response(status=HTTP_404_NOT_FOUND)

    ## Cache the last 4 games for 1 minute to avoid unnecessary API calls and maintain the freshness of the data
    @method_decorator(cache_page(60*1)) 
    @action(detail=True, methods=['get'], url_path='last-4-games')
    def get_last_4_games(self, request, pk=None):
        game_data, linescore_data = get_last_n_games_log(pk, 4)
        return Response(combine_games_and_linescores(game_data, linescore_data))

    @method_decorator(cache_page(60*2))
    @action(detail=True, methods=['get'], url_path='games')
    def get_all_games(self, request, pk=None):
        filter_value = request.query_params.get('filter', None)
        month = convert_month_string_to_int(filter_value) if filter_value else None

        games = None
        if month:
            games = get_monthly_games_for_team_this_season(pk, month)
        else:
            games = get_all_games_for_team_this_season(pk)

        return Response(games)

class TeamsPostViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'], url_path='top-5')
    def get_today_top_5_popular_posts(self, request):
        scoreboard = ScoreboardV2(
            game_date='2024-10-22',
            league_id='00',
            day_offset=0
        ).get_dict()

        return Response(scoreboard)
    