from datetime import datetime, timezone

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK, 
    HTTP_201_CREATED, 
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)

from api.paginators import CustomPageNumberPagination
from api.websocket import send_message_to_centrifuge
from games.models import Game
from management.models import (
    Inquiry, 
)
from management.serializers import (
    InquiryMessageCreateSerializer, 
    InquiryMessageSerializer, 
)
from teams.services import PostSerializerService, TeamSerializerService, TeamService
from users.authentication import CookieJWTAccessAuthentication, CookieJWTRefreshAuthentication
from users.models import Role, User, UserChat
from users.serializers import (
    CustomSocialLoginSerializer, 
    RoleSerializer,
)

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

from dj_rest_auth.registration.views import SocialLoginView

from users.services import (
    InquirySerializerService, 
    InquiryService,
    PostCommentSerializerService, 
    UserChatSerializerService, 
    UserChatService, 
    UserSerializerService, 
    UserService, 
    UserViewService, 
    send_update_to_all_parties_regarding_chat, 
    send_update_to_all_parties_regarding_inquiry
)

from users.utils import (
    generate_websocket_connection_token, 
    generate_websocket_subscription_token
)

import logging

logger = logging.getLogger(__name__)


class CustomGoogleOAuth2Adapter(GoogleOAuth2Adapter):
    def complete_login(self, request, app, token, response, **kwargs):
        id_token = response.get("id_token")
        if response:
            data = self._decode_id_token(app, id_token)
            if self.fetch_userinfo and "picture" not in data:
                info = self._fetch_user_info(token.token)
                picture = info.get("picture")
                if picture:
                    data["picture"] = picture
        else:
            data = self._fetch_user_info(token.token)

        login = self.get_provider().sociallogin_from_response(request, data)
        return login


class GoogleLoginView(SocialLoginView):
    adapter_class = CustomGoogleOAuth2Adapter
    callback_url = settings.SOCIAL_AUTH_GOOGLE_CALLBACK
    client_class = OAuth2Client
    serializer_class = CustomSocialLoginSerializer


class UserViewSet(ViewSet):
    authentication_classes = [CookieJWTAccessAuthentication]

    def get_permissions(self):
        permission_classes = []
        if self.action == 'retrieve':
            permission_classes = [AllowAny]
        elif self.action == 'post_favorite_team':
            permission_classes = [IsAuthenticated]
        elif self.action == 'delete_favorite_team':
            permission_classes = [IsAuthenticated]
        elif self.action == 'get_favorite_teams':
            permission_classes=[IsAuthenticated]
        elif self.action == 'put_favorite_teams':
            permission_classes=[IsAuthenticated]
        elif self.action == 'me':
            permission_classes = [IsAuthenticated]
        elif self.action == 'patch_me':
            permission_classes = [IsAuthenticated]
        elif self.action == 'delete_chat':
            permission_classes = [IsAuthenticated]
        elif self.action == 'enable_chat':
            permission_classes=[IsAuthenticated]
        elif self.action == 'post_like':
            permission_classes=[IsAuthenticated]
        elif self.action == 'delete_like':
            permission_classes=[IsAuthenticated]
        elif self.action == 'get_comments':
            permission_classes=[IsAuthenticated]
        elif self.action == 'get_posts':
            permission_classes=[IsAuthenticated]
        elif self.action == 'get_chats':
            permission_classes=[IsAuthenticated]
        elif self.action == 'get_chat':
            permission_classes=[IsAuthenticated]
        elif self.action == 'delete_chat':
            permission_classes=[IsAuthenticated]
        elif self.action == 'post_chat_message':
            permission_classes=[IsAuthenticated]
        elif self.action == 'mark_chat_messages_as_read':
            permission_classes=[IsAuthenticated]
        elif self.action == 'block_chat':
            permission_classes=[IsAuthenticated]
        elif self.action == 'get_inquiries':
            permission_classes=[IsAuthenticated]
        elif self.action == 'get_inquiry':
            permission_classes=[IsAuthenticated]
        elif self.action == 'mark_inquiry_messages_as_read':
            permission_classes=[IsAuthenticated]
        elif self.action == 'post_inquiry_message':
            permission_classes=[IsAuthenticated]

        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        user_serializer = UserSerializerService.serialize_user(request.user)
        return Response(user_serializer.data)
    
    @me.mapping.patch
    def patch_me(self, request):
        user = request.user
        UserService.update_user(request, user)

        user = UserService.get_user_by_id(user.id)
        serializer = UserSerializerService.serialize_user(user)

        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        user = UserService.get_user_with_liked_by_id(request, pk)
        if not user:
            return Response(status=HTTP_404_NOT_FOUND)

        if request.user.is_authenticated:
            serializer = UserSerializerService.serialize_another_user_with_liked(user)
        else:
            serializer = UserSerializerService.serialize_another_user(user)

        return Response(serializer.data)
    
    @action(
        detail=True,
        methods=['get'],
        url_path='favorite-teams',
    )
    def get_user_favorite_teams(self, request, pk=None):
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)

        teams = TeamService.get_team_with_user_like(user)
        data = TeamSerializerService.serialize_teams_with_user_favorite(teams, user)
        return Response(data)
    
    @action(
        detail=False, 
        methods=['get'], 
        url_path=r'me/favorite-teams', 
    )
    def get_favorite_teams(self, request, pk=None):
        teams = TeamService.get_team_with_user_like(request.user)
        data = TeamSerializerService.serialize_teams_with_user_favorite(teams, request.user)
        return Response(data)

    @get_favorite_teams.mapping.put
    def put_favorite_teams(self, request):
        created, error = TeamService.update_user_favorite_teams(request)
        if error:
            return Response(status=HTTP_400_BAD_REQUEST, data=error)

        return Response(status=HTTP_201_CREATED)
    
    @action(
        detail=False,
        methods=['post'],
        url_path=r'me/favorite-teams/(?P<team_id>[0-9a-f-]+)',
        permission_classes=[IsAuthenticated]
    )
    def post_favorite_team(self, request, team_id):
        team = TeamService.add_user_favorite_team(request, team_id)
        serializer = TeamSerializerService.serialize_team_without_teamname(team)    
        return Response(status=HTTP_201_CREATED, data=serializer.data)
    
    @post_favorite_team.mapping.delete
    def delete_favorite_team(self, request, team_id):
        team = TeamService.remove_user_favorite_team(request, team_id)
        serializer = TeamSerializerService.serialize_team_without_teamname(team)
        return Response(status=HTTP_200_OK, data=serializer.data)
    
    @action(
        detail=True,
        methods=['get'],
        url_path=r'posts',
    )
    def get_user_posts(self, request, pk=None):
        try:
            User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)

        posts = UserViewService.get_user_posts(request, pk)

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(posts, request)

        serializer = PostSerializerService.serialize_posts(request, paginated_data)
        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'me/posts',
    )
    def get_posts(self, request):
        posts = UserViewService.get_user_posts(request, request.user.id)

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(posts, request)

        serializer = PostSerializerService.serialize_posts(request, paginated_data)
        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'roles',
    )
    def get_roles(self, request):
        roles = Role.objects.all()
        serializer = RoleSerializer(roles, many=True)

        return Response(serializer.data)
    
    @action(
        detail=True,
        methods=['get'],
        url_path=r'comments',
    )
    def get_user_comments(self, request, pk=None):
        try:
            User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)

        comments = UserViewService.get_user_comments(request, pk)

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(comments, request)

        serializer = PostCommentSerializerService.serialize_comments(request, paginated_data)
        return pagination.get_paginated_response(serializer.data)

    @action(
        detail=False,
        methods=['get'],
        url_path=r'me/comments',
    )
    def get_comments(self, request):
        comments = UserViewService.get_user_comments(request, request.user.id)
        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(comments, request)
        serializer = PostCommentSerializerService.serialize_comments(request, paginated_data)

        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'me/chats',
    )
    def get_chats(self, request):
        chats = UserChatService.get_my_chats(request)
        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(chats, request)

        serializer = UserChatSerializerService.serialize_chats(request, paginated_data)

        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'me/chats/(?P<user_id>[0-9a-f-]+)',
    )
    def get_chat(self, request, user_id):
        user = request.user
        if user_id == user.id:
            return Response(status=HTTP_400_BAD_REQUEST, data={'error': 'You cannot chat with yourself'})

        chat = UserChatService.get_chat(request, user_id)
        if not chat:
            return Response(status=HTTP_404_NOT_FOUND)

        user_participant = chat.userchatparticipant_set.all().get(user=user)
        serializer = UserChatSerializerService.serialize_chat(chat, user_participant)

        return Response(serializer.data)

    @get_chat.mapping.delete
    def delete_chat(self, request, user_id):
        if user_id == request.user.id:
            return Response(status=HTTP_400_BAD_REQUEST, data={'error': 'You cannot chat with yourself'})

        UserChatService.delete_chat(request, user_id)
        return Response(status=HTTP_200_OK)
    
    @action(
        detail=False,
        methods=['post'],
        url_path=r'me/chats/(?P<user_id>[0-9a-f-]+)/messages',
    )
    def post_chat_message(self, request, user_id):
        if user_id == request.user.id:
            return Response(status=HTTP_400_BAD_REQUEST, data={'error': 'You cannot chat with yourself'})

        message, chat = UserChatService.create_chat_message(request, user_id)
        if not chat:
            return Response(status=HTTP_404_NOT_FOUND)

        message_serializer = UserChatSerializerService.serialize_message_for_chat(message)

        chat = UserChatService.get_chat_by_id(chat.id)
        chat_serializer = UserChatSerializerService.serialize_chat_for_update(chat)

        send_update_to_all_parties_regarding_chat(
            request,
            user_id,
            chat.id,
            chat_serializer,
            message_serializer
        )
        
        return Response(status=HTTP_201_CREATED, data={'id': str(message.id)})
    
    @action(
        detail=False,
        methods=['put'],
        url_path=r'me/chats/(?P<user_id>[0-9a-f-]+)/mark-as-read',
    )
    def mark_chat_messages_as_read(self, request, user_id):
        user = request.user
        if user_id == user.id:
            return Response(status=HTTP_400_BAD_REQUEST, data={'error': 'You cannot mark your own chat as read'})

        chat = UserChatService.mark_chat_as_read(request, user_id)
        if not chat:
            return Response(status=HTTP_404_NOT_FOUND)

        chat.refresh_from_db()
        chat_serializer = UserChatSerializerService.serialize_chat_for_update(chat)

        sender_chat_notification_channel_name = f'users/{user.id}/chats/updates'
        send_message_to_centrifuge(
            sender_chat_notification_channel_name,
            chat_serializer.data
        )

        return Response(status=HTTP_200_OK)
    
    @action(
        detail=False,
        methods=['post'],
        url_path=r'me/chats/(?P<user_id>[0-9a-f-])/block',
    )
    def block_chat(self, request, user_id):
        if user_id == request.user.id:
            return Response(status=HTTP_400_BAD_REQUEST, data={'error': 'You cannot block yourself'})

        UserChatService.block_chat(request, user_id)
        return Response(status=HTTP_200_OK)
    
    @action(
        detail=True,
        methods=['post'],
        url_path=r'chats',
    )
    def enable_chat(self, request, pk=None):
        if pk == request.user.id:
            return Response(status=HTTP_400_BAD_REQUEST, data={'error': 'You cannot chat with yourself'})

        try:
            target_user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)

        enabled, error, data = UserChatService.enable_chat(request, target_user) 
        if not enabled:
            return Response(status=HTTP_400_BAD_REQUEST, data=error)

        return Response(status=HTTP_201_CREATED, data=data)
    
    @action(
        detail=True,
        methods=['post'],
        url_path=r'likes',
    )
    def post_like(self, request, pk=None):
        user = request.user
        if user.id == pk:
            return Response(status=HTTP_400_BAD_REQUEST, data={'error': 'You cannot like yourself'})

        try:
            user_to_like = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)
        
        user = UserService.create_user_like(request, pk, user, user_to_like)

        serializer = UserSerializerService.serialize_user_with_id_only(user)
        return Response(status=HTTP_201_CREATED, data=serializer.data)
    
    @post_like.mapping.delete
    def delete_like(self, request, pk=None):
        user = request.user
        if user.id == pk:
            return Response(status=HTTP_400_BAD_REQUEST, data={'error': 'You cannot unlike yourself'})

        try:
            user_to_like = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)
        
        user = UserService.delete_user_like(request, pk, user, user_to_like)
        serializer = UserSerializerService.serialize_user_with_id_only(user)        
        return Response(status=HTTP_200_OK, data=serializer.data)
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'me/inquiries',
    )
    def get_inquiries(self, request):
        inquiries = InquiryService.get_my_inquiries(request)

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(inquiries, request)

        serializer = InquirySerializerService.serialize_inquiries(request, paginated_data)

        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'me/inquiries/(?P<inquiry_id>[0-9a-f-]+)',
    )
    def get_inquiry(self, request, inquiry_id):
        inquiry = InquiryService.get_inquiry(request, inquiry_id)
        if not inquiry:
            return Response(status=HTTP_404_NOT_FOUND)
        
        serializer = InquirySerializerService.serialize_inquiry(inquiry)
        return Response(serializer.data)
    
    @action(
        detail=False,
        methods=['put'],
        url_path=r'me/inquiries/(?P<inquiry_id>[0-9a-f-]+)/mark-as-read',
    )
    def mark_inquiry_messages_as_read(self, request, inquiry_id):
        user = request.user
        inquiry = Inquiry.objects.filter(
            id=inquiry_id, 
            user=user
        ).first()

        if not inquiry:
            return Response(status=HTTP_404_NOT_FOUND)

        updated = Inquiry.objects.filter(id=inquiry_id).update(last_read_at=datetime.now(timezone.utc))
        if not updated:
            return Response(status=HTTP_400_BAD_REQUEST)

        return Response(status=HTTP_200_OK)
    
    @action(
        detail=False,
        methods=['post'],
        url_path=r'me/inquiries/(?P<inquiry_id>[0-9a-f-]+)/messages',
    )
    def post_inquiry_message(self, request, inquiry_id):
        user = request.user
        inquiry_exists = Inquiry.objects.filter(
            id=inquiry_id, 
            user=user
        ).exists()

        if not inquiry_exists:
            return Response(status=HTTP_404_NOT_FOUND)

        serializer = InquiryMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save(
            inquiry=inquiry_id
        )
        message_serializer = InquiryMessageSerializer(
            message,
            fields_exclude=['inquiry_data'],
            context={
                'user': {
                    'fields': ['id', 'username']
                }
            }
        )

        inquiry = InquiryService.get_inquiry_by_id(inquiry_id)
        inquiry.updated_at = datetime.now(timezone.utc)
        inquiry.save()

        serializer = InquirySerializerService.serialize_inquiry_for_update(request, inquiry)

        send_update_to_all_parties_regarding_inquiry(
            inquiry,
            user,
            message_serializer,
            serializer
        )
        
        return Response(status=HTTP_201_CREATED, data={'id': str(message.id)})
    

class JWTViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CookieJWTRefreshAuthentication]

    @action(
        detail=False, 
        methods=['post'], 
        url_path='refresh'
    )
    def refresh(self, request, pk=None):
        logging.info('Refreshing token')
        refresh_token = request.auth

        refresh_token_cookie_key = settings.SIMPLE_JWT.get('AUTH_REFRESH_TOKEN_COOKIE', 'refresh')
        access_token_cookie_key = settings.SIMPLE_JWT.get('AUTH_ACCESS_TOKEN_COOKIE', 'access')
        secure = settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', True)
        httpOnly = settings.SIMPLE_JWT.get('AUTH_COOKIE_HTTP_ONLY', True)
        path = settings.SIMPLE_JWT.get('AUTH_COOKIE_PATH', '/')
        domain = settings.SIMPLE_JWT.get('AUTH_COOKIE_DOMAIN', None)
        samesite = settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax')

        response = Response(status=HTTP_201_CREATED, data={
            'username': request.user.username,
            'email': request.user.email,
            'id': request.user.id
        })
        response.delete_cookie(refresh_token_cookie_key)
        response.delete_cookie(access_token_cookie_key)

        response.set_cookie(
            refresh_token_cookie_key,
            str(refresh_token),
            secure=secure,
            httponly=httpOnly,
            path=path,
            domain=domain,
            samesite=samesite,
            expires=datetime.fromtimestamp(refresh_token.get('exp'), tz=timezone.utc)
        )
        response.set_cookie(
            access_token_cookie_key,
            str(refresh_token.access_token),
            secure=secure,
            httponly=True,
            path=path,
            domain=domain,
            samesite=samesite,
            max_age=settings.SIMPLE_JWT.get('ACCESS_TOKEN_LIFETIME')
        )

        return response
    
    @refresh.mapping.delete
    def delete_refresh(self, request):
        refresh_token_cookie_key = settings.SIMPLE_JWT.get('AUTH_REFRESH_TOKEN_COOKIE', 'refresh')
        access_token_cookie_key = settings.SIMPLE_JWT.get('AUTH_ACCESS_TOKEN_COOKIE', 'access')
        secure = settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', True)
        httpOnly = settings.SIMPLE_JWT.get('AUTH_COOKIE_HTTP_ONLY', True)
        path = settings.SIMPLE_JWT.get('AUTH_COOKIE_PATH', '/')
        domain = settings.SIMPLE_JWT.get('AUTH_COOKIE_DOMAIN', None)
        samesite = settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax')

        response = Response(status=HTTP_200_OK)
        response.set_cookie(
            refresh_token_cookie_key,
            '',
            secure=secure,
            httponly=httpOnly,
            path=path,
            domain=domain,
            samesite=samesite,
            expires=0
        )

        response.set_cookie(
            access_token_cookie_key,
            '',
            secure=secure,
            httponly=httpOnly,
            path=path,
            domain=domain,
            samesite=samesite,
            max_age=0
        )

        return response
    
    @action(
        detail=False, 
        methods=['get'], 
        url_path='websocket-access'
    )
    def access(self, request):
        token = generate_websocket_connection_token(request.user.id)
        return Response({'token': str(token)})

    @action(
        detail=False, 
        methods=['get'], 
        url_path=r'subscription/games/(?P<game_id>[0-9a-zA-Z-]+)/live-chat'
    )
    def subscribe_for_live_game_chat(self, request, game_id):
        try:
            Game.objects.get(game_id=game_id)
        except Game.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)

        channel_name = f'games/{game_id}/live-chat'
        token = generate_websocket_subscription_token(request.user.id, channel_name)
        return Response({'token': str(token)})
    
    @action(
        detail=False, 
        methods=['get'], 
        url_path=r'subscription/users/chats/(?P<chat_id>[0-9a-zA-Z-]+)'
    )
    def subscribe_for_user_chat(self, request, chat_id):
        try:
            UserChat.objects.get(
                id=chat_id, 
                userchatparticipant__user=request.user
            )
        except UserChat.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)
        
        channel_name = f'users/chats/{chat_id}'

        token = generate_websocket_subscription_token(request.user.id, channel_name)
        return Response({'token': str(token)})
    
    @action(
        detail=False, 
        methods=['get'], 
        url_path=r'subscription/users/chat-updates'
    )
    def subscribe_for_user_chat_updates(self, request):
        channel_name = f'users/{request.user.id}/chats/updates'
        token = generate_websocket_subscription_token(request.user.id, channel_name)
        return Response({'token': str(token)})
    
    @action(
        detail=False, 
        methods=['get'], 
        url_path=r'subscription/users/inquiries/(?P<inquiry_id>[0-9a-zA-Z-]+)'
    )
    def subscribe_for_user_inquiry(self, request, inquiry_id):
        try:
            Inquiry.objects.get(
                id=inquiry_id, 
                user=request.user
            )
        except Inquiry.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)
        
        channel_name = f'users/inquiries/{inquiry_id}'
        token = generate_websocket_subscription_token(request.user.id, channel_name)
        return Response({'token': str(token)})
    
    @action(
        detail=False, 
        methods=['get'], 
        url_path=r'subscription/users/inquiry-updates'
    )
    def subscribe_for_user_inquiry_updates(self, request):
        channel_name = f'users/{request.user.id}/inquiries/updates'
        token = generate_websocket_subscription_token(request.user.id, channel_name)
        return Response({'token': str(token)})