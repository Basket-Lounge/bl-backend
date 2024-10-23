from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from games.models import Game, LineScore
from games.serializers import GameSerializer, LineScoreSerializer, PlayerStatisticsSerializer
from games.services import combine_game_and_linescores, combine_games_and_linescores, get_today_games
from players.models import PlayerStatistics


class GameViewSet(viewsets.ViewSet):
    @method_decorator(cache_page(60*5))
    @action(detail=False, methods=['get'])
    def today(self, request):
        games, linescores = get_today_games()
        serializer = GameSerializer(
            games,
            many=True,
            fields_exclude=[
                'line_scores',
                'home_team_statistics',
                'visitor_team_statistics',
                'home_team_player_statistics',
                'visitor_team_player_statistics'
            ],
            context={
                'team': {'fields': ('id', 'symbol', 'teamname_set')},
                'teamname': {'fields': ('name', 'language')},
                'language': {'fields': ('name',)}
            }
        )

        linescore_serializer = LineScoreSerializer(
            linescores,
            many=True,
            context={
                'game': {'fields': ('game_id',)},
                'team': {'fields': ('id',)},
            }
        )

        return Response(combine_games_and_linescores(serializer.data, linescore_serializer.data))

    @method_decorator(cache_page(60*5)) 
    def retrieve(self, request, pk=None):
        game = Game.objects.select_related(
            'home_team', 'visitor_team'
        ).prefetch_related(
            'teamstatistics_set',
        ).get(game_id=pk)

        serializer = GameSerializer(
            game,
            fields_exclude=[
                'line_scores',
                'home_team_player_statistics',
                'visitor_team_player_statistics'
            ],
            context={
                'team': {'fields': ('id', 'symbol', 'teamname_set')},
                'teamname': {'fields': ('name', 'language')},
                'language': {'fields': ('name',)},
                'teamstatistics': {'fields_exclude': ('game',)},
            }
        )

        linescores = LineScore.objects.filter(
            game=game
        ).select_related(
            'game',
            'team'
        ).order_by(
            'game__game_date_est',
            'game__game_sequence'
        )

        linescore_serializer = LineScoreSerializer(
            linescores,
            many=True,
            context={
                'game': {'fields': ('game_id',)},
                'team': {'fields': ('id',)},
            }
        )

        return Response(combine_game_and_linescores(serializer.data, linescore_serializer.data))

    @action(detail=True, methods=['get'], url_path='player-statistics')
    def get_game_players_statistics(self, request, pk=None):
        players_statistics = PlayerStatistics.objects.filter(
            game__game_id=pk
        ).select_related(
            'player',
            'team'
        ).order_by(
            'team__id',
            'order',
            '-starter'
        ).defer(
            'game'
        )

        serializer = PlayerStatisticsSerializer(
            players_statistics,
            many=True,
            fields_exclude=['game'],
            context={
                'player': {'fields': ('id', 'first_name', 'last_name')},
                'team': {'fields': ('id',)},
            }
        )

        return Response(serializer.data)
    