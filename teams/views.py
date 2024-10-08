from django.db.models import Prefetch

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
import datetime

from nba_api.stats.endpoints.franchisehistory import FranchiseHistory

from teams.models import Team, TeamName
from teams.serializers import TeamSerializer

# Create your views here.
class TeamViewSet(viewsets.ViewSet):
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

        return Response(serializer.data)
    
class TeamsPostViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'], url_path='top-5')
    def get_today_top_5_popular_posts(self, request):
        franchise_history = FranchiseHistory(
            league_id='00'
        ).get_dict()['resultSets'][0]['rowSet']

        active_teams = set()
        for team in franchise_history:
            if team[5] == "2023":
                active_teams.add(tuple([
                    team[1],
                    team[2],
                    team[3]
                ]))

        return Response(active_teams)
    