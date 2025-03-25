from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED, 
)
from rest_framework.permissions import IsAuthenticated

from api.exceptions import CustomError
from api.paginators import CustomPageNumberPagination
from games.serializers import GameSerializer, LineScoreSerializer
from games.services import (
    GameChatSerializerService,
    GameChatService,
    GameSerializerService, 
    GameService, 
    combine_game_and_linescores, 
    combine_games_and_linescores, 
    get_today_games
)
from users.authentication import CookieJWTAccessAuthentication


class GameViewSet(viewsets.ViewSet):
    authentication_classes = [CookieJWTAccessAuthentication]

    def get_permissions(self):
        permission_classes = []
        if self.action == 'post_chat_message':
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

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
        games = GameService.get_games(request)

        pagination = CustomPageNumberPagination()
        paginated_games = pagination.paginate_queryset(games, request)

        serializer = GameSerializerService.serialize_games(
            paginated_games
        )
        return pagination.get_paginated_response(serializer.data)

    @method_decorator(cache_page(60*1)) 
    def retrieve(self, request, pk=None):
        game = GameService.get_game(pk)
        game_serializer = GameSerializerService.serialize_game(game)

        linescores = GameService.get_game_line_scores(game)
        linescore_serializer = GameSerializerService.serialize_line_scores(linescores)

        return Response(combine_game_and_linescores(game_serializer.data, linescore_serializer.data))

    @action(detail=True, methods=['get'], url_path='player-statistics')
    def get_game_players_statistics(self, request, pk=None):
        players_statistics = GameService.get_game_players_statistics(pk)
        serializer = GameSerializerService.serialize_game_players_statistics(players_statistics)
        return Response(serializer.data)
    
    @action(
        detail=True, 
        methods=['post'], 
        url_path='chat', 
    )
    def post_chat_message(self, request, pk=None):
        try:
            next_message_datetime_str = GameChatService.create_game_chat_message(request, pk)
            return Response(
                status=HTTP_201_CREATED, 
                data={'next_message_datetime': next_message_datetime_str}
            )
        except CustomError as e:
            return Response(status=e.code, data={'error': e.message})
    
    @action(
        detail=True, 
        methods=['patch'], 
        url_path=r'chat/messages/(?P<message_id>[0-9a-f-]+)',
    )
    def patch_chat_message(self, request, pk=None, message_id=None):
        try:
            GameChatService.update_game_chat_message(request, pk, message_id)
            return Response(status=HTTP_200_OK)
        except CustomError as e:
            return Response(status=e.code, data={'error': e.message})

    @patch_chat_message.mapping.delete    
    def delete_chat_message(self, request, pk=None, message_id=None):
        try:
            GameChatService.delete_game_chat_message(request, pk, message_id)
            return Response(status=HTTP_200_OK)
        except CustomError as e:
            return Response(status=e.code, data={'error': e.message})


class GameChatViewSet(viewsets.ViewSet):
    authentication_classes = [CookieJWTAccessAuthentication]

    def retrieve(self, request, pk=None):
        chat = GameChatService.get_game_chat(pk)
        serializer = GameChatSerializerService.serialize_game_chat(chat)
        return Response(serializer.data)
    
    @action(
        detail=True, 
        methods=['post'], 
        url_path='messages',
    )
    def post_chat_message(self, request, pk=None):
        try:
            next_message_datetime_str = GameChatService.create_game_chat_message(request, pk)
            return Response(
                status=HTTP_201_CREATED, 
                data={'next_message_datetime': next_message_datetime_str}
            )
        except CustomError as e:
            return Response(status=e.code, data={'error': e.message})