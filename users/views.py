from datetime import datetime, timezone

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Exists, OuterRef, Prefetch, Q

from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK, 
    HTTP_201_CREATED, 
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND
)

from api.paginators import CustomPageNumberPagination
from teams.models import (
    Post, 
    PostComment, 
    PostCommentLike, 
    PostCommentReply, 
    PostLike, 
    PostStatusDisplayName, 
    Team, 
    TeamLike
)
from teams.serializers import TeamSerializer
from users.authentication import CookieJWTAccessAuthentication, CookieJWTRefreshAuthentication
from users.models import User, UserChat, UserChatParticipant, UserChatParticipantMessage, UserLike
from users.serializers import (
    CustomSocialLoginSerializer, 
    PostCommentSerializer, 
    PostSerializer,
    UserChatParticipantMessageCreateSerializer,
    UserChatSerializer, 
    UserSerializer
)

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

from dj_rest_auth.registration.views import SocialLoginView

from users.utils import (
    calculate_level, 
    generate_websocket_connection_token, 
    generate_websocket_subscription_token
)


class CustomGoogleOAuth2Adapter(GoogleOAuth2Adapter):
    def complete_login(self, request, app, token, response, **kwargs):
        data = None
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

        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        user = request.user
        serializer = UserSerializer(
            user,
            fields=(
                'username', 
                'email', 
                'role',
                'level',
                'introduction', 
                'is_profile_visible',
                'likes_count'
            ),
        )

        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        fields = [
            'username',
            'role',
            'level',
            'introduction',
            'is_profile_visible',
            'likes_count'
        ]

        try:
            user = User.objects.select_related('role').only(
                'username', 'email', 'role', 'experience'
            )

            if request.user.is_authenticated:
                user = user.annotate(
                    liked=Exists(UserLike.objects.filter(user=request.user, liked_user=OuterRef('pk')))
                ).get(id=pk)

                fields.append('liked')
            else:
                user = user.get(id=pk)

        except User.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)

        serializer = UserSerializer(
            user,
            fields=fields,
        )

        return Response(serializer.data)
    
    @action(
        detail=True,
        methods=['get'],
        url_path='favorite-teams',
        permission_classes=[AllowAny]
    )
    def get_user_favorite_teams(self, request, pk=None):
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)

        query = Team.objects.prefetch_related(
            'teamname_set'
        ).filter(
            teamlike__user=user
        ).order_by('symbol').only('id', 'symbol')

        if not query.exists():
            return Response([])

        serializer = TeamSerializer(
            query,
            many=True,
            fields=['id', 'symbol', 'teamname_set'],
            context={
                'teamname': {
                    'fields': ['name', 'language']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        return Response(serializer.data)
    
    @action(
        detail=False, 
        methods=['get'], 
        url_path=r'me/favorite-teams', 
        permission_classes=[IsAuthenticated]
    )
    def get_favorite_teams(self, request, pk=None):
        user = request.user

        query = Team.objects.prefetch_related(
            'teamname_set'
        ).filter(
            teamlike__user=user
        ).order_by('symbol').only('id', 'symbol')

        if not query.exists():
            return Response([])

        serializer = TeamSerializer(
            query,
            many=True,
            fields=['id', 'symbol', 'teamname_set'],
            context={
                'teamname': {
                    'fields': ['name', 'language']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        return Response(serializer.data)

    @get_favorite_teams.mapping.put
    def put_favorite_teams(self, request):
        user = request.user
        data = request.data

        team_ids = [team['id'] for team in data]
        teams = Team.objects.filter(id__in=team_ids)

        TeamLike.objects.filter(user=user).delete()
        TeamLike.objects.bulk_create([
            TeamLike(user=user, team=team) for team in teams
        ])

        return Response(status=HTTP_201_CREATED)
    
    @action(
        detail=False,
        methods=['post'],
        url_path=r'me/favorite-teams/(?P<team_id>[0-9a-f-]+)',
        permission_classes=[IsAuthenticated]
    )
    def post_favorite_team(self, request, team_id):
        user = request.user
        TeamLike.objects.get_or_create(user=user, team=Team.objects.get(id=team_id))
        
        try:
            team = Team.objects.filter(id=team_id).only('id', 'symbol').annotate(
                liked=Exists(TeamLike.objects.filter(user=user, team=OuterRef('pk')))
            ).get()
        except Team.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND, data={'error': 'Not exists'}) 
        
        serializer = TeamSerializer(
            team,
            fields_exclude=['teamname_set'],
        )

        return Response(status=HTTP_201_CREATED, data=serializer.data)
    
    @post_favorite_team.mapping.delete
    def delete_favorite_team(self, request, team_id):
        user = request.user

        try:
            TeamLike.objects.get(user=user, team__id=team_id).delete()
        except TeamLike.DoesNotExist:
            return Response(status=HTTP_400_BAD_REQUEST, data={'error': 'Not exists'})
        
        try:
            team = Team.objects.filter(id=team_id).only('id', 'symbol').annotate(
                liked=Exists(TeamLike.objects.filter(user=user, team=OuterRef('pk')))
            ).get()
        except Team.DoesNotExist:
            return Response(status=HTTP_400_BAD_REQUEST, data={'error': 'Not exists'})
        
        serializer = TeamSerializer(
            team,
            fields_exclude=['teamname_set'],
        )

        return Response(status=HTTP_200_OK, data=serializer.data)
    
    @action(
        detail=False,
        methods=['put'],
        url_path=r'me/profile-visibility',
        permission_classes=[IsAuthenticated]
    )
    def update_profile_visibility(self, request):
        user = request.user
        if 'is_profile_visible' not in request.data:
            return Response(status=HTTP_400_BAD_REQUEST)
        if not isinstance(request.data['is_profile_visible'], bool):
            return Response(status=HTTP_400_BAD_REQUEST)
        
        user.is_profile_visible = request.data['is_profile_visible']
        user.save()

        return Response(status=HTTP_201_CREATED)
    
    @action(
        detail=False,
        methods=['put'],
        url_path=r'me/introduction',
        permission_classes=[IsAuthenticated]
    )
    def update_introduction(self, request):
        user = request.user
        if 'introduction' not in request.data:
            return Response(status=HTTP_400_BAD_REQUEST)
        if not isinstance(request.data['introduction'], str):
            return Response(status=HTTP_400_BAD_REQUEST)
        
        user.introduction = request.data['introduction']
        user.save()

        return Response(status=HTTP_201_CREATED)
    
    @action(
        detail=True,
        methods=['get'],
        url_path=r'posts',
        permission_classes=[AllowAny]
    )
    def get_user_posts(self, request, pk=None):
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)

        fields_exclude = ['content']
        posts = Post.objects.filter(user=user).order_by('-created_at').select_related(
            'user',
            'team',
            'status'
        ).prefetch_related(
            Prefetch(
                'postlike_set',
                queryset=PostLike.objects.filter(post__user=user)
            ),
            Prefetch(
                'postcomment_set',
                queryset=PostComment.objects.filter(post__user=user)
            ),
            Prefetch(
                'status__poststatusdisplayname_set',
                queryset=PostStatusDisplayName.objects.select_related(
                    'language'
                ).all()
            ),
        ).only(
            'id', 
            'title', 
            'created_at', 
            'updated_at', 
            'user__id', 
            'user__username', 
            'team__id', 
            'team__symbol', 
            'status__id', 
            'status__name'
        )

        if request.user.is_authenticated:
            posts = posts.annotate(
                liked=Exists(PostLike.objects.filter(user=request.user, post=OuterRef('pk')))
            )
        else:
            fields_exclude.append('liked')

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(posts, request)

        serializer = PostSerializer(
            paginated_data,
            many=True,
            fields_exclude=fields_exclude,
            context={
                'user': {
                    'fields': ('id', 'username')
                },
                'team': {
                    'fields': ('id', 'symbol')
                },
                'poststatusdisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'me/posts',
        permission_classes=[IsAuthenticated]
    )
    def get_posts(self, request):
        user = request.user

        fields_exclude = ['content']
        posts = Post.objects.filter(user=user).order_by('-created_at').select_related(
            'user',
            'team',
            'status'
        ).prefetch_related(
            Prefetch(
                'postlike_set',
                queryset=PostLike.objects.filter(post__user=user)
            ),
            Prefetch(
                'postcomment_set',
                queryset=PostComment.objects.filter(post__user=user)
            ),
            Prefetch(
                'status__poststatusdisplayname_set',
                queryset=PostStatusDisplayName.objects.select_related(
                    'language'
                ).all()
            ),
        ).only(
            'id', 
            'title', 
            'created_at', 
            'updated_at', 
            'user__id', 
            'user__username', 
            'team__id', 
            'team__symbol', 
            'status__id', 
            'status__name'
        ).annotate(
            liked=Exists(PostLike.objects.filter(user=request.user, post=OuterRef('pk')))
        )

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(posts, request)

        serializer = PostSerializer(
            paginated_data,
            many=True,
            fields_exclude=fields_exclude,
            context={
                'user': {
                    'fields': ('id', 'username')
                },
                'team': {
                    'fields': ('id', 'symbol')
                },
                'poststatusdisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=True,
        methods=['get'],
        url_path=r'comments',
        permission_classes=[AllowAny]
    )
    def get_user_comments(self, request, pk=None):
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)

        query = PostComment.objects.filter(
            user=user,
        ).exclude(
            Q(status__name='deleted') | Q(post__status__name='deleted')
        ).prefetch_related(
            Prefetch(
                'postcommentlike_set',
                queryset=PostCommentLike.objects.filter(post_comment__user=user)
            ),
            Prefetch(
                'postcommentreply_set',
                queryset=PostCommentReply.objects.filter(post_comment__user=user)
            ),
        ).select_related(
            'user',
            'status',
            'post__team',
            'post__user'
        ).only(
            'id',
            'content',
            'created_at',
            'updated_at',
            'user__id',
            'user__username',
            'status__id',
            'status__name',
            'post__id',
            'post__title',
            'post__team__id',
            'post__team__symbol',
            'post__user__id',
            'post__user__username'
        ).order_by(
            '-created_at'
        )

        if request.user.is_authenticated:
            query = query.annotate(
                liked=Exists(PostCommentLike.objects.filter(user=request.user, post_comment=OuterRef('pk')))
            )

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(query, request)

        serializer = PostCommentSerializer(
            paginated_data,
            fields_exclude=['liked'] if not request.user.is_authenticated else [],
            many=True,
            context={
                'user': {
                    'fields': ('id', 'username')
                },
                'status': {
                    'fields': ('id', 'name')
                },
                'post': {
                    'fields': ('id', 'title', 'team_data', 'user_data')
                },
                'team': {
                    'fields': ('id', 'symbol')
                }
            }
        )

        return pagination.get_paginated_response(serializer.data)

    @action(
        detail=False,
        methods=['get'],
        url_path=r'me/comments',
        permission_classes=[IsAuthenticated]
    )
    def get_comments(self, request):
        user = request.user

        query = PostComment.objects.filter(
            user=user,
        ).exclude(
            Q(status__name='deleted') | Q(post__status__name='deleted')
        ).prefetch_related(
            Prefetch(
                'postcommentlike_set',
                queryset=PostCommentLike.objects.filter(post_comment__user=user)
            ),
            Prefetch(
                'postcommentreply_set',
                queryset=PostCommentReply.objects.filter(post_comment__user=user)
            ),
        ).select_related(
            'user',
            'status',
            'post__team',
            'post__user'
        ).only(
            'id',
            'content',
            'created_at',
            'updated_at',
            'user__id',
            'user__username',
            'status__id',
            'status__name',
            'post__id',
            'post__title',
            'post__team__id',
            'post__team__symbol',
            'post__user__id',
            'post__user__username'
        ).order_by(
            '-created_at'
        ).annotate(
            liked=Exists(PostCommentLike.objects.filter(user=user, post_comment=OuterRef('pk')))
        )

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(query, request)

        serializer = PostCommentSerializer(
            paginated_data,
            many=True,
            context={
                'user': {
                    'fields': ('id', 'username')
                },
                'status': {
                    'fields': ('id', 'name')
                },
                'post': {
                    'fields': ('id', 'title', 'team_data', 'user_data')
                },
                'team': {
                    'fields': ('id', 'symbol')
                }
            }
        )

        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'me/chats',
        permission_classes=[IsAuthenticated]
    )
    def get_chats(self, request):
        user = request.user

        user_chat_query = UserChat.objects.filter(
            userchatparticipant__user=user
        )
        
        chat_query = UserChat.objects.filter(
            userchatparticipant__user=user
        ).prefetch_related(
            Prefetch(
                'userchatparticipant_set',
                UserChatParticipant.objects.filter(
                    chat__in=user_chat_query
                ).prefetch_related(
                    Prefetch(
                        'userchatparticipantmessage_set',
                        queryset=UserChatParticipantMessage.objects.filter(
                            sender__chat__in=user_chat_query
                        ).order_by('created_at')
                    ),
                ).select_related(
                    'user',
                )
            )
        ).order_by('-updated_at')

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(chat_query, request)

        serializer = UserChatSerializer(
            paginated_data,
            many=True,
            fields=['id', 'participants'],
            context={
                'userchatparticipant': {
                    'fields': ['user_data', 'last_message']
                },
                'userchatparticipantmessage': {
                    'fields_exclude': ['sender_data']
                },
                'user': {
                    'fields': ['id', 'username']
                }
            }
        )

        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'me/chats/(?P<user_id>[0-9a-f-]+)',
        permission_classes=[IsAuthenticated]
    )
    def get_chat(self, request, user_id):
        user = request.user

        chat = UserChat.objects.filter(
            userchatparticipant__user=user
        ).filter(
            userchatparticipant__user__id=user_id
        ).first()

        if not chat:
            return Response(status=HTTP_404_NOT_FOUND)

        chat_query = UserChat.objects.filter(
            id=chat.id
        ).prefetch_related(
            Prefetch(
                'userchatparticipant_set',
                UserChatParticipant.objects.filter(
                    chat=chat
                ).prefetch_related(
                    Prefetch(
                        'userchatparticipantmessage_set',
                        queryset=UserChatParticipantMessage.objects.filter(
                            sender__chat=chat
                        ).order_by('created_at')
                    ),
                ).select_related(
                    'user',
                )
            )
        ).get()

        serializer = UserChatSerializer(
            chat_query,
            fields=['id', 'participants', 'created_at', 'updated_at'],
            context={
                'userchatparticipant': {
                    'fields': ['user_data', 'messages']
                },
                'userchatparticipantmessage': {
                    'fields_exclude': ['sender_data']
                },
                'user': {
                    'fields': ['id', 'username']
                }
            }
        )

        return Response(serializer.data)
    
    @action(
        detail=False,
        methods=['post'],
        url_path=r'me/chats/(?P<user_id>[0-9a-f-]+)/messages',
        permission_classes=[IsAuthenticated]
    )
    def post_chat_message(self, request, user_id):
        user = request.user
        chat = UserChat.objects.filter(
            userchatparticipant__user=user
        ).filter(
            userchatparticipant__user__id=user_id
        ).first()

        if not chat:
            return Response(status=HTTP_404_NOT_FOUND)

        serializer = UserChatParticipantMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save(
            sender=UserChatParticipant.objects.get(user=user, chat=chat)
        )

        return Response(status=HTTP_201_CREATED, data={'id': str(message.id)})
    
    @action(
        detail=True,
        methods=['post'],
        url_path=r'chats',
        permission_classes=[IsAuthenticated]
    )
    def post_chat(self, request, pk=None):
        try:
            another_participant = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)
        
        user = request.user

        chat = UserChat.objects.create()
        UserChatParticipant.objects.bulk_create([
            UserChatParticipant(user=user, chat=chat),
            UserChatParticipant(user=another_participant, chat=chat)
        ])

        return Response(status=HTTP_201_CREATED, data={'id': str(chat.id)})
    
    @action(
        detail=True,
        methods=['post'],
        url_path=r'likes',
        permission_classes=[IsAuthenticated]
    )
    def post_like(self, request, pk=None):
        user = request.user
        try:
            user_to_like = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)

        UserLike.objects.get_or_create(user=user, liked_user=user_to_like)

        try:
            user = User.objects.filter(id=pk).annotate(
                liked=Exists(UserLike.objects.filter(user=request.user, liked_user=OuterRef('pk')))
            ).get()
        except User.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)
        
        serializer = UserSerializer(
            user,
            fields=['id', 'likes_count', 'liked']
        )

        return Response(status=HTTP_201_CREATED, data=serializer.data)
    
    @post_like.mapping.delete
    def delete_like(self, request, pk=None):
        user = request.user
        try:
            user_to_like = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)

        try:
            UserLike.objects.get(user=user, liked_user=user_to_like).delete()
        except UserLike.DoesNotExist:
            return Response(status=HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.filter(id=pk).annotate(
                liked=Exists(UserLike.objects.filter(user=request.user, liked_user=OuterRef('pk')))
            ).get()
        except User.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)
        
        serializer = UserSerializer(
            user,
            fields=['id', 'likes_count', 'liked']
        )

        return Response(status=HTTP_200_OK, data=serializer.data)


class JWTViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CookieJWTRefreshAuthentication]

    @action(detail=False, methods=['post'], url_path='refresh')
    def refresh(self, request, pk=None):
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
    
    @action(detail=False, methods=['get'], url_path='websocket-access')
    def access(self, request):
        token = generate_websocket_connection_token(request.user.id)
        return Response({'token': str(token)})

    @action(detail=False, methods=['get'], url_path='subscription')
    def subscription(self, request):
        channel_name = request.query_params.get('channel')
        token = generate_websocket_subscription_token(request.user.id, channel_name)
        return Response({'token': str(token)})