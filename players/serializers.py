from rest_framework import serializers

from api.mixins import DynamicFieldsSerializerMixin
from players.models import Player, PlayerCareerStatistics
from teams.serializers import TeamSerializer


class PlayerSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    team = serializers.SerializerMethodField()
    
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