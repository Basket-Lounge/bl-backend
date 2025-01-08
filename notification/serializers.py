import re
from rest_framework import serializers
from api.mixins import DynamicFieldsSerializerMixin
from games.serializers import GameSerializer
from notification.models import (
    Notification, 
    NotificationActor, 
    NotificationRecipient, 
    NotificationTemplate, 
    NotificationTemplateBody, 
    NotificationTemplateType
)
from players.serializers import PlayerSerializer
from teams.serializers import LanguageSerializer, TeamSerializer
from users.serializers import (
    PostCommentReplySerializer, 
    PostCommentSerializer, 
    PostSerializer, 
    UserChatSerializer, 
    UserSerializer
)

from django.conf import settings


class NotificationTemplateTypeSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplateType
        fields = '__all__'


class NotificationTemplateSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    type_data = serializers.SerializerMethodField()
    bodies = serializers.SerializerMethodField()

    class Meta:
        model = NotificationTemplate
        exclude = ['type']

    def get_type_data(self, obj):
        if not hasattr(obj, 'type'):
            return None

        context = self.context.get('notificationtemplatetype', {})
        serializer = NotificationTemplateTypeSerializer(
            obj.type,
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_bodies(self, obj):
        if not hasattr(obj, 'notificationtemplatebody_set'):
            return None
        
        context = self.context.get('notificationtemplatebody', {})
        serializer = NotificationTemplateBodySerializer(
            obj.notificationtemplatebody_set.all(),
            many=True,
            context=self.context,
            **context
        )
        return serializer.data
    

class NotificationTemplateBodySerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    template_data = serializers.SerializerMethodField()
    language_data = serializers.SerializerMethodField()

    class Meta:
        model = NotificationTemplateBody
        exclude = ['template', 'language']

    def get_template_data(self, obj):
        if not hasattr(obj, 'template'):
            return None

        context = self.context.get('notificationtemplate', {})
        serializer = NotificationTemplateSerializer(
            obj.template,
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


class NotificationSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    template_data = serializers.SerializerMethodField()
    actors = serializers.SerializerMethodField()
    picture_url = serializers.SerializerMethodField()
    redirect_url = serializers.SerializerMethodField()
    contents = serializers.SerializerMethodField()
    recipients = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        exclude = ['template']

    def get_nested_value(self, data, keys):
        """Recursively fetch value from a nested dictionary using a list of keys."""
        for key in keys:
            data = data.get(key)
            if data is None:
                return None
        return data
    
    def find_placeholders(self, template):
        # Regular expression to match placeholders
        pattern = r"<([^>]+)>"
        return re.findall(pattern, template)

    def replace_placeholders(self, template, context):
        # Regular expression to match placeholders
        pattern = r"<([^>]+)>"
        
        # Function to replace each match
        def replacer(match):
            placeholder = match.group(1)  # Extract the placeholder without the angle brackets
            keys = placeholder.split(":")  # Split the keys by ':'
            value = self.get_nested_value(context, keys)  # Fetch the nested value
            return str(value) if value is not None else match.group(0)  # Replace or keep original
        
        # Substitute placeholders with their values
        return re.sub(pattern, replacer, template)
    
    def replace_placeholders_for_contents(self, template, context):
        # Regular expression to match placeholders
        pattern = r"<([^>]+)>"
        
        # Function to replace each match
        def replacer(match):
            placeholder = match.group(1)  # Extract the placeholder without the angle brackets
            keys = placeholder.split(":")  # Split the keys by ':'
            value = self.get_nested_value(context, keys)  # Fetch the nested value
            return f'[[{str(value)}]]' if value is not None else match.group(0)  # Replace or keep original
        
        # Substitute placeholders with their values
        return re.sub(pattern, replacer, template)

    def get_template_data(self, obj):
        if not hasattr(obj, 'template'):
            return None

        context = self.context.get('notificationtemplate', {})
        serializer = NotificationTemplateSerializer(
            obj.template,
            context=self.context,
            **context
        )

        return serializer.data
    
    def get_actors(self, obj):
        if not hasattr(obj, 'notificationactor_set'):
            return None
        
        context = self.context.get('notificationactor', {})
        serializer = NotificationActorSerializer(
            obj.notificationactor_set.all(),
            many=True,
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_picture_url(self, obj):
        if not hasattr(obj, 'template'):
            return None

        if not hasattr(obj.template, 'picture_url_template') or not obj.template.picture_url_template:
            return None 
        
        if not self.find_placeholders(obj.template.picture_url_template):
            return obj.template.picture_url_template
        
        if not hasattr(obj, 'notificationactor_set') or not obj.notificationactor_set.all():
            return None

        if not settings.FRONTEND_URL:
            return None
        
        context = self.context.get('notificationactor', {})
        serializer = NotificationActorSerializer(
            obj.notificationactor_set.all(),
            many=True,
            context=self.context,
            **context
        )
        actors = serializer.data
        
        picture_url_template = obj.template.picture_url_template
        picture_url = picture_url_template
        try:
            picture_url = picture_url_template.format(settings.FRONTEND_URL)
        except Exception as e:
            pass

        for actor in actors:
            picture_url = self.replace_placeholders(picture_url, actor)

        if hasattr(obj, 'data') and obj.data:
            picture_url = self.replace_placeholders(picture_url, obj.data)

        ## find if there are any placeholders left
        matches = self.find_placeholders(picture_url)
        if matches:
            return None
        
        return picture_url
    
    def get_redirect_url(self, obj):
        if not hasattr(obj, 'template'):
            return None

        if not hasattr(obj.template, 'redirect_url_template') or not obj.template.redirect_url_template:
            return None 
        
        if not self.find_placeholders(obj.template.redirect_url_template):
            return obj.template.redirect_url_template
        
        if not hasattr(obj, 'notificationactor_set') or not obj.notificationactor_set.all():
            return None

        if not settings.FRONTEND_URL:
            return None
        
        context = self.context.get('notificationactor', {})
        serializer = NotificationActorSerializer(
            obj.notificationactor_set.all(),
            many=True,
            context=self.context,
            **context
        )
        actors = serializer.data
        
        redirect_url_template = obj.template.redirect_url_template
        redirect_url = redirect_url_template
        try:
            redirect_url = redirect_url_template.format(FRONTEND_URL=settings.FRONTEND_URL)
        except Exception as e:
            pass

        for actor in actors:
            redirect_url = self.replace_placeholders(redirect_url, actor)

        if hasattr(obj, 'data') and obj.data:
            redirect_url = self.replace_placeholders(redirect_url, obj.data)

        ## find if there are any placeholders left
        matches = self.find_placeholders(redirect_url)
        if matches:
            return None
        
        return redirect_url
    
    def get_contents(self, obj):
        if not hasattr(obj, 'template'):
            return None
        
        if not hasattr(obj.template, 'notificationtemplatebody_set'):
            return None
        
        context = self.context.get('notificationtemplatebody', {})
        serializer = NotificationTemplateBodySerializer(
            obj.template.notificationtemplatebody_set.all(),
            many=True,
            context=self.context,
            **context
        )

        all_contents = serializer.data
        contents = {}

        for content in all_contents:
            if 'language_data' not in content:
                raise serializers.ValidationError('Language data not found in notification template body')
            
            if 'name' not in content['language_data']:
                raise serializers.ValidationError('Language name not found in notification template body')
            
            if 'body' not in content:
                raise serializers.ValidationError('Body not found in notification template body')

            key = content['language_data']['name']
            contents[key] = content['body']

            if not self.find_placeholders(content['body']):
                continue

            if not hasattr(obj, 'notificationactor_set') or not obj.notificationactor_set.all():
                raise serializers.ValidationError('Actors not found in notification')

            if not hasattr(obj, 'data'):
                raise serializers.ValidationError('Data not found in notification')

            actors = obj.notificationactor_set.all()
            context = self.context.get('notificationactor', {})
            actor_serializer = NotificationActorSerializer(
                actors,
                many=True,
                context=self.context,
                **context
            )
            actors = actor_serializer.data

            for actor in actors:
                contents[key] = self.replace_placeholders_for_contents(contents[key], actor)

            if hasattr(obj, 'data') and obj.data:
                contents[key] = self.replace_placeholders_for_contents(contents[key], obj.data)

            if self.find_placeholders(contents[key]):
                contents[key] = None

        return contents
    
    def get_recipients(self, obj):
        if not hasattr(obj, 'notificationrecipient_set'):
            return None
        
        context = self.context.get('notificationrecipient', {})
        serializer = NotificationRecipientSerializer(
            obj.notificationrecipient_set.all(),
            many=True,
            context=self.context,
            **context
        )
        return serializer.data


class NotificationActorSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    notification_data = serializers.SerializerMethodField()
    user_data = serializers.SerializerMethodField()
    post_data = serializers.SerializerMethodField()
    comment_data = serializers.SerializerMethodField()
    reply_data = serializers.SerializerMethodField()
    game_data = serializers.SerializerMethodField()
    player_data = serializers.SerializerMethodField()
    team_data = serializers.SerializerMethodField()
    chat_data = serializers.SerializerMethodField()

    class Meta:
        model = NotificationActor
        exclude = [
            'notification',
            'user',
            'post',
            'comment',
            'reply',
            'game',
            'player',
            'team',
            'chat'
        ]

    def get_notification_data(self, obj):
        if not hasattr(obj, 'notification'):
            return None
        
        context = self.context.get('actor_notification', {})
        serializer = NotificationSerializer(
            obj.notification,
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_user_data(self, obj):
        if not hasattr(obj, 'user'):
            return None
        
        context = self.context.get('actor_user', {})
        serializer = UserSerializer(
            obj.user,
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_post_data(self, obj):
        if not hasattr(obj, 'post'):
            return None
        
        context = self.context.get('actor_post', {})
        serializer = PostSerializer(
            obj.post,
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_comment_data(self, obj):
        if not hasattr(obj, 'comment'):
            return None
        
        context = self.context.get('actor_postcomment', {})
        serializer = PostCommentSerializer(
            obj.comment,
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_reply_data(self, obj):
        if not hasattr(obj, 'reply'):
            return None
        
        context = self.context.get('actor_postcommentreply', {})
        serializer = PostCommentReplySerializer(
            obj.reply,
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_game_data(self, obj):
        if not hasattr(obj, 'game'):
            return None
        
        context = self.context.get('actor_game', {})
        serializer = GameSerializer(
            obj.game,
            context=self.context,
            **context
        )
        return serializer.data
    

    def get_player_data(self, obj):
        if not hasattr(obj, 'player'):
            return None
        
        context = self.context.get('actor_player', {})
        serializer = PlayerSerializer(
            obj.player,
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_team_data(self, obj):
        if not hasattr(obj, 'team'):
            return None
        
        context = self.context.get('actor_team', {})
        serializer = TeamSerializer(
            obj.team,
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_chat_data(self, obj):
        if not hasattr(obj, 'chat'):
            return None
        
        context = self.context.get('actor_userchat', {})
        serializer = UserChatSerializer(
            obj.chat,
            context=self.context,
            **context
        )
        return serializer.data
    

class NotificationRecipientSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    recipient_data = serializers.SerializerMethodField()
    notification_data = serializers.SerializerMethodField()

    class Meta:
        model = NotificationRecipient
        exclude = ['notification', 'recipient']

    def get_recipient_data(self, obj):
        if not hasattr(obj, 'recipient'):
            return None
        
        context = self.context.get('user', {})
        serializer = UserSerializer(
            obj.recipient,
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_notification_data(self, obj):
        if not hasattr(obj, 'notification'):
            return None
        
        context = self.context.get('notification', {})
        serializer = NotificationSerializer(
            obj.notification,
            context=self.context,
            **context
        )
        return serializer.data