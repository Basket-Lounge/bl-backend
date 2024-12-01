from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from allauth.account import app_settings as allauth_settings
from allauth.socialaccount.helpers import complete_social_login

from dj_rest_auth.registration.serializers import SocialLoginSerializer

from requests.exceptions import HTTPError

from api.mixins import DynamicFieldsSerializerMixin
from teams.models import Post, PostComment, PostCommentReply, PostCommentReplyStatus, PostCommentStatus, PostStatus
from teams.serializers import PostCommentStatusSerializer, PostStatusSerializer, TeamLikeSerializer, TeamSerializer
from users.models import Role, UserChat, UserChatParticipant, UserChatParticipantMessage
from users.utils import calculate_level


class CustomSocialLoginSerializer(SocialLoginSerializer):
    def get_social_login(self, adapter, app, token, response):
        """
        :param adapter: allauth.socialaccount Adapter subclass.
            Usually OAuthAdapter or Auth2Adapter
        :param app: `allauth.socialaccount.SocialApp` instance
        :param token: `allauth.socialaccount.SocialToken` instance
        :param response: Provider's response for OAuth1. Not used in the
        :returns: A populated instance of the
            `allauth.socialaccount.SocialLoginView` instance
        """
        request = self._get_request()
        social_login = adapter.complete_login(request, app, token, response=response)
        social_login.token = token
        return social_login

    def validate(self, attrs):
        view = self.context.get('view')
        request = self._get_request()

        if not view:
            raise serializers.ValidationError(
                _("View is not defined, pass it as a context variable")
            )

        adapter_class = getattr(view, 'adapter_class', None)
        if not adapter_class:
            raise serializers.ValidationError(_("Define adapter_class in view"))

        adapter = adapter_class(request)
        app = adapter.get_provider().app

        # More info on code vs access_token
        # http://stackoverflow.com/questions/8666316/facebook-oauth-2-0-code-and-token

        # Case 2: We received the authorization code
        if attrs.get('code'):
            self.callback_url = getattr(view, 'callback_url', None)
            self.client_class = getattr(view, 'client_class', None)

            if not self.callback_url:
                raise serializers.ValidationError(
                    _("Define callback_url in view")
                )
            if not self.client_class:
                raise serializers.ValidationError(
                    _("Define client_class in view")
                )

            code = attrs.get('code')

            provider = adapter.get_provider()
            scope = provider.get_scope()
            client = self.client_class(
                request,
                app.client_id,
                app.secret,
                adapter.access_token_method,
                adapter.access_token_url,
                self.callback_url,
                scope,
            )
            token = client.get_access_token(code)

        else:
            raise serializers.ValidationError(
                _("Incorrect input. access_token or code is required."))

        social_token = adapter.parse_token(token)
        social_token.app = app

        ## Delay for 2 seconds to prevent rate limit
        # import time
        # time.sleep(2)

        try:
            login = self.get_social_login(adapter, app, social_token, token)
            complete_social_login(request, login)
        except HTTPError:
            raise serializers.ValidationError(_("Incorrect value"))

        if not login.is_existing:
            # We have an account already signed up in a different flow
            # with the same email address: raise an exception.
            # This needs to be handled in the frontend. We can not just
            # link up the accounts due to security constraints
            if allauth_settings.UNIQUE_EMAIL:
                # Do we have an account already with this email address?
                account_exists = get_user_model().objects.filter(
                    email=login.user.email,
                ).exists()
                if account_exists:
                    raise serializers.ValidationError(
                        _("User is already registered with this e-mail address.")
                    )

            login.lookup()
            login.save(request, connect=True)

        attrs['user'] = login.account.user
        return attrs


class RoleSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'


class UserSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    role_data = serializers.SerializerMethodField()
    teamlike_set = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    liked = serializers.SerializerMethodField()
    favorite_team = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        exclude = ('role',)
    
    def get_role_data(self, obj):
        if not hasattr(obj, 'role'):
            return None
        
        context = self.context.get('role', {})
        serializer = RoleSerializer(
            obj.role, 
            context=self.context,
            **context    
        )
        return serializer.data
    
    def get_level(self, obj):
        if not hasattr(obj, 'experience'):
            return None

        return calculate_level(obj.experience)
    
    def get_teamlike_set(self, obj):
        if not hasattr(obj, 'teamlike_set'):
            return None
        
        context = self.context.get('teamlike', {})
        serializer = TeamLikeSerializer(
            obj.teamlike_set, 
            many=True,
            context=self.context,
            **context    
        )
        return serializer.data

    def get_likes_count(self, obj):
        if not hasattr(obj, 'liked_user'):
            return None

        return obj.liked_user.all().count()
    
    def get_liked(self, obj):
        return obj.liked
    
    def get_favorite_team(self, obj):
        if not hasattr(obj, 'teamlike_set'):
            return None
        
        for teamlike in obj.teamlike_set.all():
            if teamlike.favorite:
                context = self.context.get('team', {})
                serializer = TeamSerializer(
                    teamlike.team, 
                    context=self.context,
                    **context    
                )
                return serializer.data
            
        return None
    

class UserUpdateSerializer(serializers.Serializer):
    introduction = serializers.CharField(min_length=1)
    is_profile_visible = serializers.BooleanField()
    chat_blocked = serializers.BooleanField()
    username = serializers.CharField(min_length=1, max_length=128)

    def update(self, instance, validated_data):
        introduction = validated_data.get('introduction', None)
        is_profile_visible = validated_data.get('is_profile_visible', None)
        chat_blocked = validated_data.get('chat_blocked', None)
        username = validated_data.get('username', None)

        if introduction:
            stripped_introduction = introduction.strip()
            if not stripped_introduction:
                raise serializers.ValidationError('Introduction cannot be empty')

            instance.introduction = stripped_introduction

        if is_profile_visible is not None:
            instance.is_profile_visible = is_profile_visible

        if chat_blocked is not None:
            instance.chat_blocked = chat_blocked

        if username:
            User = get_user_model()
            stripped_username = username.strip()
            if not stripped_username:
                raise serializers.ValidationError('Username cannot be empty')

            if instance.username != stripped_username:
                if User.objects.filter(username=stripped_username).exists():
                    raise serializers.ValidationError('Username already exists')

            instance.username = username

        instance.save()
        return instance


class PostSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    status_data = serializers.SerializerMethodField()
    team_data = serializers.SerializerMethodField()
    user_data = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        exclude = ('status', 'team', 'user')

    def get_status_data(self, obj):
        if not hasattr(obj, 'status'):
            return None
        
        context = self.context.get('status', {})
        serializer = PostStatusSerializer(
            obj.status, 
            context=self.context,
            **context    
        )
        return serializer.data
    
    def get_team_data(self, obj):
        if not hasattr(obj, 'team'):
            return None
        
        context = self.context.get('team', {})
        serializer = TeamSerializer(
            obj.team, 
            context=self.context,
            **context    
        )
        return serializer.data
    
    def get_user_data(self, obj):
        if not hasattr(obj, 'user'):
            return None
        
        context = self.context.get('user', {})
        serializer = UserSerializer(
            obj.user, 
            context=self.context,
            **context    
        )
        return serializer.data
    
    def get_likes_count(self, obj):
        return obj.postlike_set.count()
    
    def get_comments_count(self, obj):
        return obj.postcomment_set.count()
    
    def get_liked(self, obj):
        return obj.liked


class PostUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(min_length=1, max_length=128)
    content = serializers.CharField(min_length=1)
    status = serializers.IntegerField()

    def update(self, instance, validated_data):
        status = validated_data.get('status', None)
        title = validated_data.get('title', None)
        content = validated_data.get('content', None)

        if title:
            instance.title = title

        if content:
            instance.content = content

        if status is not None:
            status_obj = PostStatus.objects.filter(id=status).first()
            if status_obj:
                instance.status = status_obj

        instance.save()
        return instance


class PostCommentSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    post_data = serializers.SerializerMethodField()
    user_data = serializers.SerializerMethodField()
    status_data = serializers.SerializerMethodField()
    replies_count = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    liked = serializers.SerializerMethodField()

    class Meta:
        model = PostComment
        exclude = ('post', 'user', 'status')

    def get_post_data(self, obj):
        if not hasattr(obj, 'post'):
            return None
        
        context = self.context.get('post', {})
        serializer = PostSerializer(
            obj.post, 
            context=self.context,
            **context    
        )
        return serializer.data
    
    def get_user_data(self, obj):
        if not hasattr(obj, 'user'):
            return None
        
        context = self.context.get('user', {})
        serializer = UserSerializer(
            obj.user, 
            context=self.context,
            **context    
        )
        return serializer.data
    
    def get_status_data(self, obj):
        if not hasattr(obj, 'status'):
            return None
        
        context = self.context.get('status', {})
        serializer = PostCommentStatusSerializer(
            obj.status, 
            context=self.context,
            **context    
        )
        return serializer.data
    
    def get_replies_count(self, obj):
        return obj.postcommentreply_set.count()
    
    def get_likes_count(self, obj):
        return obj.postcommentlike_set.count()
    
    def get_liked(self, obj):
        if not hasattr(obj, 'liked'):
            return None

        return obj.liked
    

class PostCommentUpdateSerializer(serializers.Serializer):
    content = serializers.CharField(min_length=1)
    status = serializers.IntegerField()

    def update(self, instance, validated_data):
        status = validated_data.get('status', None)
        content = validated_data.get('content', None)

        if content:
            instance.content = content

        if status is not None:
            status_obj = PostCommentStatus.objects.filter(id=status).first()
            if status_obj:
                instance.status = status_obj

        instance.save()
        return instance
    

class PostCommentReplyStatusSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = PostCommentReplyStatus
        fields = '__all__'
    

class PostCommentReplySerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    post_comment_data = serializers.SerializerMethodField()
    user_data = serializers.SerializerMethodField()
    status_data = serializers.SerializerMethodField()

    class Meta:
        model = PostCommentReply
        exclude = ('post_comment', 'user', 'status')

    def get_post_comment_data(self, obj):
        if not hasattr(obj, 'post_comment'):
            return None
        
        context = self.context.get('post_comment', {})
        serializer = PostCommentSerializer(
            obj.post_comment, 
            context=self.context,
            **context    
        )
        return serializer.data
    
    def get_user_data(self, obj):
        if not hasattr(obj, 'user'):
            return None
        
        context = self.context.get('user', {})
        serializer = UserSerializer(
            obj.user, 
            context=self.context,
            **context    
        )
        return serializer.data
    
    def get_status_data(self, obj):
        if not hasattr(obj, 'status'):
            return None
        
        context = self.context.get('status', {})
        serializer = PostCommentReplyStatusSerializer(
            obj.status, 
            context=self.context,
            **context    
        )
        return serializer.data


class UserChatParticipantMessageSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    sender_data = serializers.SerializerMethodField()
    user_data = serializers.SerializerMethodField()

    class Meta:
        model = UserChatParticipantMessage
        exclude = ('sender',)

    def get_sender_data(self, obj):
        if not hasattr(obj, 'sender'):
            return None
        
        context = self.context.get('userchatparticipant', {})
        serializer = UserChatParticipantSerializer(
            obj.sender, 
            context=self.context,
            **context    
        )
        return serializer.data
    
    def get_user_data(self, obj):
        context = self.context.get('user', {})
        serializer = UserSerializer(
            obj.sender.user,
            context=self.context,
            **context    
        )

        return serializer.data
    
class UserChatParticipantMessageCreateSerializer(serializers.Serializer):
    message = serializers.CharField(min_length=1)
    
    def create(self, validated_data):
        sender = validated_data.get('sender', None)
        receiver = validated_data.get('receiver', None)

        if sender is None:
            raise serializers.ValidationError('Sender is required')

        if receiver is None: 
            raise serializers.ValidationError('Receiver is required')
        
        if receiver.chat_deleted:
            receiver.chat_deleted = False
            receiver.last_deleted_at = datetime.now(timezone.utc)
            receiver.save()

        ## remove the receiver from the validated data
        validated_data.pop('receiver', None)

        with transaction.atomic():
            return UserChatParticipantMessage.objects.create(**validated_data)


class UserChatParticipantSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    chat_data = serializers.SerializerMethodField()
    user_data = serializers.SerializerMethodField()
    messages = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_messages_count = serializers.SerializerMethodField()

    class Meta:
        model = UserChatParticipant
        exclude = ('chat', 'user')

    def get_chat_data(self, obj):
        if not hasattr(obj, 'chat'):
            return None
        
        context = self.context.get('chat', {})
        serializer = UserChatSerializer(
            obj.chat, 
            context=self.context,
            **context    
        )
        return serializer.data
    
    def get_user_data(self, obj):
        if not hasattr(obj, 'user'):
            return None
        
        context = self.context.get('user', {})
        serializer = UserSerializer(
            obj.user, 
            context=self.context,
            **context    
        )
        return serializer.data

    def get_messages(self, obj):
        if not hasattr(obj, 'userchatparticipantmessage_set'):
            return None
        
        context = self.context.get('userchatparticipantmessage', {})
        extra_context = self.context.get('userchatparticipantmessage_extra', {})

        ## get the last 50 messages
        messages = obj.userchatparticipantmessage_set.all()[:50]

        user = extra_context.get('user_last_deleted_at', None)
        if user:
            last_deleted_at = user.get('last_deleted_at', None)
            messages = [message for message in messages if message.created_at > last_deleted_at]

        serializer = UserChatParticipantMessageSerializer(
            messages,
            many=True,
            context=self.context,
            **context    
        )
        return serializer.data

    def get_last_message(self, obj):
        if not hasattr(obj, 'userchatparticipantmessage_set'):
            return None
        
        context = self.context.get('userchatparticipantmessage', {})
        last_message = obj.userchatparticipantmessage_set.all().first()

        if not last_message:
            return None

        serializer = UserChatParticipantMessageSerializer(
            last_message,
            context=self.context,
            **context    
        )
        return serializer.data
    
    def get_unread_messages_count(self, obj):
        if not hasattr(obj, 'userchatparticipantmessage_set'):
            return None

        last_read_at = obj.last_read_at

        count = 0
        for message in obj.userchatparticipantmessage_set.all():
            if message.created_at > last_read_at:
                count += 1

        return count
    

class UserChatSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    participants = serializers.SerializerMethodField()

    class Meta:
        model = UserChat
        fields = '__all__'

    def get_participants(self, obj):
        if not hasattr(obj, 'userchatparticipant_set'):
            return None
        
        context = self.context.get('userchatparticipant', {})
        serializer = UserChatParticipantSerializer(
            obj.userchatparticipant_set.all(),
            many=True,
            context=self.context,
            **context    
        )
        return serializer.data