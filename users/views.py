from datetime import datetime, timezone

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST

from teams.models import Team, TeamLike
from teams.serializers import TeamSerializer
from users.authentication import CookieJWTRefreshAuthentication
from users.models import User
from users.serializers import CustomSocialLoginSerializer, UserSerializer

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

from dj_rest_auth.registration.views import SocialLoginView

from users.utils import calculate_level, generate_websocket_connection_token, generate_websocket_subscription_token


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
    def get_permissions(self):
        permission_classes = []
        if self.action == 'retrieve':
            permission_classes = [AllowAny]

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
                'experience', 
                'introduction', 
                'is_profile_visible'
            ),
        )

        return Response({
            'username': serializer.data['username'],
            'email': serializer.data['email'],
            'role': serializer.data['role'],
            'introduction': serializer.data['introduction'],
            'level': calculate_level(serializer.data['experience']),
            'is_profile_visible': serializer.data['is_profile_visible']
        })

    @method_decorator(cache_page(60*1))
    def retrieve(self, request, pk=None):
        user = User.objects.select_related('role').only(
            'username', 'email', 'role', 'experience'
        ).get(id=pk)

        serializer = UserSerializer(
            user,
            fields=('username', 'email', 'role', 'experience'),
        )

        return Response({
            'username': serializer.data['username'],
            'email': serializer.data['email'],
            'role': serializer.data['role'],
            'level': calculate_level(user.experience)
        })
    
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