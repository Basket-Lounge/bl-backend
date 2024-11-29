from rest_framework import serializers

from api.mixins import DynamicFieldsSerializerMixin
from players.models import Player
from teams.serializers import TeamSerializer

class PlayerSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    team = serializers.SerializerMethodField()
    season_stats = serializers.SerializerMethodField()
    
    class Meta:
        model = Player
        fields = '__all__'

    def get_team(self, obj):
        if not hasattr(obj, 'team'):
            return None
        
        context = self.context.get('team', {})
        serializer = TeamSerializer(
            obj.team, 
            context=self.context,
            **context    
        )
        return serializer.data
    
    def get_season_stats(self, obj):
        if not hasattr(obj, 'playerstatistics_set'):
            return None

        season_avg = {
            'games_played': 0,
            'points': 0,
            'assists': 0,
            'rebounds_total': 0,
            'steals': 0,
            'blocks': 0,
            'field_goals_percentage': 0,
            'three_pointers_percentage': 0,
            'free_throws_percentage': 0,
        }

        for stats in obj.playerstatistics_set.all():
            if stats.status == 'INACTIVE':
                continue

            season_avg['games_played'] += 1
            season_avg['points'] += stats.points
            season_avg['assists'] += stats.assists
            season_avg['rebounds_total'] += stats.rebounds_total
            season_avg['steals'] += stats.steals
            season_avg['blocks'] += stats.blocks
            season_avg['field_goals_percentage'] += stats.field_goals_percentage * 100
            season_avg['three_pointers_percentage'] += stats.three_pointers_percentage * 100
            season_avg['free_throws_percentage'] += stats.free_throws_percentage * 100
        
        for key in season_avg:
            if key == 'games_played':
                continue

            season_avg[key] = season_avg[key] / season_avg['games_played']
        
        return season_avg