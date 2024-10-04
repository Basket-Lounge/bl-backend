from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
import datetime

# Create your views here.
class PlayersViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'], url_path='top-10')
    def get_top_10_players(self, request):
        return Response({'today': datetime.date.today()})