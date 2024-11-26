from datetime import datetime
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Prefetch

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_201_CREATED, 
    HTTP_400_BAD_REQUEST, 
    HTTP_404_NOT_FOUND, 
    HTTP_500_INTERNAL_SERVER_ERROR
)

from api.paginators import CustomPageNumberPagination
from api.websocket import send_message_to_centrifuge
from games.models import Game, GameChat, GameChatMessage, LineScore
from games.serializers import GameSerializer, LineScoreSerializer, PlayerStatisticsSerializer
from games.services import combine_game_and_linescores, combine_games_and_linescores, create_game_queryset_without_prefetch, get_today_games
from players.models import PlayerStatistics
from teams.models import TeamName
from users.utils import validate_websocket_subscription_token


class GameViewSet(viewsets.ViewSet):
    @method_decorator(cache_page(60*1))
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
    
    def list(self, request):
        all_team_names = TeamName.objects.select_related('language')

        games = create_game_queryset_without_prefetch(
            request
        ).prefetch_related(
            Prefetch(
                'line_scores',
                queryset=LineScore.objects.select_related('team').prefetch_related(
                    Prefetch(
                        'team__teamname_set',
                        queryset=all_team_names
                    )
                )
            ),
            Prefetch(
                'home_team__teamname_set',
                queryset=all_team_names
            ),
            Prefetch(
                'visitor_team__teamname_set',
                queryset=all_team_names
            )
        ).select_related(
            'home_team', 'visitor_team'
        ).all()

        pagination = CustomPageNumberPagination()
        paginated_games = pagination.paginate_queryset(games, request)

        serializer = GameSerializer(
            paginated_games,
            many=True,
            fields_exclude=[
                'home_team_statistics',
                'visitor_team_statistics',
                'home_team_player_statistics',
                'visitor_team_player_statistics'
            ],
            context={
                'linescore': {
                    'fields_exclude': ['id', 'game']
                },
                'team': {
                    'fields': ['id', 'symbol', 'teamname_set']
                },
                'teamname': {
                    'fields': ['name', 'language']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        return pagination.get_paginated_response(serializer.data)

    @method_decorator(cache_page(60*1)) 
    def retrieve(self, request, pk=None):
        game = Game.objects.select_related(
            'home_team', 'visitor_team'
        ).prefetch_related(
            'teamstatistics_set',
        ).get(game_id=pk)

        game_fields_exclude = [
            'line_scores',
            'home_team_player_statistics',
            'visitor_team_player_statistics'
        ]

        if game.game_status_id == 1:
            game_fields_exclude.extend([
                'home_team_statistics',
                'visitor_team_statistics'
            ])

        game_serializer_context = {
            'team': {'fields': ('id', 'symbol', 'teamname_set')},
            'teamname': {'fields': ('name', 'language')},
            'language': {'fields': ('name',)},
        }

        if game.game_status_id > 1:
            game_serializer_context.update({
                'teamstatistics': {'fields_exclude': ('game',)},
            })

        serializer = GameSerializer(
            game,
            fields_exclude=game_fields_exclude,
            context=game_serializer_context
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
            fields_exclude=['game_data', 'game'],
            context={
                'player': {'fields': ('id', 'first_name', 'last_name')},
                'team': {'fields': ('id',)},
            }
        )

        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='chat')
    def get_chat(self, request, pk=None):
        channel = f'games/{pk}/live-chat'

        subscription_token = request.data.get('subscription_token', None)
        if subscription_token is None:
            return Response(
                {'error': 'Subscription token is required'}, 
                status=HTTP_400_BAD_REQUEST
            )
        if not validate_websocket_subscription_token(
            subscription_token, 
            channel, 
            request.user.id
        ):
            return Response(
                {'error': 'Invalid subscription token'}, 
                status=HTTP_400_BAD_REQUEST
            )

        message = request.data.get('message', None)
        if message is None:
            return Response(
                {'error': 'Message is required'}, 
                status=HTTP_400_BAD_REQUEST
            )

        try:
            game = Game.objects.get(game_id=pk)
        except Game.DoesNotExist:
            return Response(
                {'error': 'Game not found'}, 
                status=HTTP_404_NOT_FOUND
            )
        
        resp_json = send_message_to_centrifuge(channel, {
            'message': message,
            'user': {
                'id': request.user.id,
                'username': request.user.get_username()
            },
            'game': game.game_id,
            'created_at': int(datetime.now().timestamp())
        })
        if resp_json.get('error', None):
            return Response(
                {'error': 'Message Delivery Unsuccessful'}, 
                status=HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        game_chat, created = GameChat.objects.get_or_create(game=game)
        GameChatMessage.objects.create(
            chat=game_chat,
            message=message,
            user=request.user
        )

        return Response(status=HTTP_201_CREATED)