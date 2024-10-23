from rest_framework import serializers

from api.mixins import DynamicFieldsSerializerMixin
from games.models import Game, LineScore, TeamStatistics
from players.models import PlayerStatistics
from players.serializers import PlayerSerializer
from teams.serializers import TeamSerializer


class LineScoreSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    team = serializers.SerializerMethodField()
    game = serializers.SerializerMethodField()

    class Meta:
        model = LineScore
        fields = '__all__'

    def get_game(self, obj):
        if not hasattr(obj, 'game'):
            return None
        
        context = self.context.get('game', {})
        serializer = GameSerializer(
            obj.game,
            context=self.context,
            **context
        )
        return serializer.data

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


class GameSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    line_scores = serializers.SerializerMethodField()
    home_team = serializers.SerializerMethodField()
    visitor_team = serializers.SerializerMethodField()
    home_team_statistics = serializers.SerializerMethodField()
    visitor_team_statistics = serializers.SerializerMethodField()
    home_team_player_statistics = serializers.SerializerMethodField()
    visitor_team_player_statistics = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = '__all__'

    def get_line_scores(self, obj):
        line_scores = obj.line_scores
        context = self.context.get('linescore', {})
        serializer = LineScoreSerializer(
            line_scores,
            many=True,
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_home_team(self, obj):
        if not hasattr(obj, 'home_team'):
            return None
        
        context = self.context.get('team', {})
        serializer = TeamSerializer(
            obj.home_team,
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_visitor_team(self, obj):
        if not hasattr(obj, 'visitor_team'):
            return None
        
        context = self.context.get('team', {})
        serializer = TeamSerializer(
            obj.visitor_team,
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_home_team_statistics(self, obj):
        context = self.context.get('teamstatistics', {})
        team_statistics = obj.teamstatistics_set.get(team=obj.home_team)
        serializer = TeamStatisticsSerializer(
            team_statistics,
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_visitor_team_statistics(self, obj):
        context = self.context.get('teamstatistics', {})
        team_statistics = obj.teamstatistics_set.get(team=obj.visitor_team)
        serializer = TeamStatisticsSerializer(
            team_statistics,
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_home_team_player_statistics(self, obj):
        context = self.context.get('player_statistics', {})
        serializer = PlayerStatisticsSerializer(
            PlayerStatistics.objects.filter(game=obj, team=obj.home_team),
            many=True,
            context=self.context,
            **context
        )
        return serializer.data


class TeamStatisticsSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    team = serializers.SerializerMethodField()
    game = serializers.SerializerMethodField()

    class Meta:
        model = TeamStatistics
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
    
    def get_game(self, obj):
        if not hasattr(obj, 'game'):
            return None
        
        context = self.context.get('game', {})
        serializer = GameSerializer(
            obj.game,
            context=self.context,
            **context
        )
        return serializer.data
    

class PlayerStatisticsSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    player = serializers.SerializerMethodField()
    game = serializers.SerializerMethodField()
    team = serializers.SerializerMethodField()
    
    class Meta:
        model = PlayerStatistics
        fields = '__all__'

    def get_player(self, obj):
        if not hasattr(obj, 'player'):
            return None
        
        context = self.context.get('player', {})
        serializer = PlayerSerializer(
            obj.player, 
            context=self.context,
            **context    
        )
        return serializer.data
    
    def get_game(self, obj):
        if not hasattr(obj, 'game'):
            return None
        
        context = self.context.get('game', {})
        serializer = GameSerializer(
            obj.game, 
            context=self.context,
            **context    
        )
        return serializer.data
    
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