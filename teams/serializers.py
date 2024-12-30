from rest_framework import serializers

from api.mixins import DynamicFieldsSerializerMixin
from teams.models import PostCommentStatus, PostCommentStatusDisplayName, PostStatus, PostStatusDisplayName, Team, TeamLike, TeamName, Language


class LanguageSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = '__all__'


class TeamNameSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    team = serializers.SerializerMethodField()
    language = serializers.SerializerMethodField()

    class Meta:
        model = TeamName
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

    def get_language(self, obj):
        if not hasattr(obj, 'language'):
            return None
        
        context = self.context.get('language', None)
        serializer = LanguageSerializer(
            obj.language, 
            context=self.context,
            **context    
        )
        return serializer.data


class TeamSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    teamname_set = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    liked = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = '__all__'

    def get_teamname_set(self, obj):
        teamnames = obj.teamname_set
        context = self.context.get('teamname', {})
        serializer = TeamNameSerializer(
            teamnames, 
            many=True, 
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_likes_count(self, obj):
        return obj.teamlike_set.count()
    
    def get_liked(self, obj):
        return obj.liked
    

class TeamLikeSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    team = serializers.SerializerMethodField()

    class Meta:
        model = TeamLike
        fields = '__all__'
        read_only_fields = ('user',)

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


class PostStatusSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    poststatusdisplayname_set = serializers.SerializerMethodField()

    class Meta:
        model = PostStatus
        fields = '__all__'

    def get_poststatusdisplayname_set(self, obj):
        poststatusdisplaynames = obj.poststatusdisplayname_set
        context = self.context.get('poststatusdisplayname', {})
        serializer = PostStatusDisplayNameSerializer(
            poststatusdisplaynames, 
            many=True, 
            context=self.context,
            **context
        )
        return serializer.data


class PostStatusDisplayNameSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    post_status_data = serializers.SerializerMethodField()
    language_data = serializers.SerializerMethodField()

    class Meta:
        model = PostStatusDisplayName
        exclude = ('post_status', 'language')

    def get_post_status_data(self, obj):
        if not hasattr(obj, 'post_status'):
            return None
        
        context = self.context.get('post_status', {})
        serializer = PostStatusSerializer(
            obj.post_status, 
            context=self.context,
            **context    
        )
        return serializer.data
    
    def get_language_data(self, obj):
        if not hasattr(obj, 'language'):
            return None
        
        context = self.context.get('language', {})
        serializer = LanguageSerializer(
            obj.language, 
            context=self.context,
            **context    
        )
        return serializer.data
    

class PostCommentStatusSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    postcommentstatusdisplayname_set = serializers.SerializerMethodField()

    class Meta:
        model = PostCommentStatus
        fields = '__all__'

    def get_postcommentstatusdisplayname_set(self, obj):
        postcommentstatusdisplaynames = obj.postcommentstatusdisplayname_set
        context = self.context.get('postcommentstatusdisplayname', {})
        serializer = PostCommentStatusDisplayNameSerializer(
            postcommentstatusdisplaynames, 
            many=True, 
            context=self.context,
            **context
        )
        return serializer.data

class PostCommentStatusDisplayNameSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    post_comment_status_data = serializers.SerializerMethodField()
    language_data = serializers.SerializerMethodField()

    class Meta:
        model = PostCommentStatusDisplayName
        exclude = ('post_comment_status', 'language')

    def get_post_comment_status_data(self, obj):
        if not hasattr(obj, 'post_comment_status'):
            return None
        
        context = self.context.get('post_comment_status', {})
        serializer = PostCommentStatusSerializer(
            obj.post_comment_status, 
            context=self.context,
            **context    
        )
        return serializer.data
    
    def get_language_data(self, obj):
        if not hasattr(obj, 'language'):
            return None
        
        context = self.context.get('language', {})
        serializer = LanguageSerializer(
            obj.language, 
            context=self.context,
            **context    
        )
        return serializer.data