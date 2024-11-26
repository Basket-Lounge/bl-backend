from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Prefetch

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from players.models import Player
from players.serializers import PlayerSerializer
from teams.models import TeamName


# Create your views here.
class PlayersViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'], url_path='top-10')
    def get_top_10_players(self, request):
        top_players = Player.objects.filter(
            playerranking__ranking__lte=10
        ).select_related('team').prefetch_related(
            Prefetch(
                'team__teamname_set',
                queryset=TeamName.objects.select_related('language')
            ),
            'playerranking_set'
        ).order_by('playerranking__ranking')

        serializer = PlayerSerializer(
            top_players, 
            many=True,
            context={
                'team': {
                    'fields': ('id', 'symbol', 'teamname_set')
                },
                'teamname': {
                    'fields': ('name', 'language')
                },
                'language': {
                    'fields': ('name',)
                }
            }
        )

        return Response(serializer.data)