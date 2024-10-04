from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
import datetime

# Create your views here.
class TeamsPostViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'], url_path='top-5')
    def get_today_top_5_popular_posts(self, request):
        return Response({'today': datetime.date.today()})