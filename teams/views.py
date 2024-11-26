from datetime import datetime, timedelta
from django.conf import settings
from django.db.models import Prefetch, Count
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Exists, OuterRef

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from rest_framework.permissions import IsAuthenticated

from api.paginators import CustomPageNumberPagination
from games.serializers import PlayerStatisticsSerializer, PlayerCareerStatisticsSerializer
from games.services import combine_games_and_linescores
from players.serializers import PlayerSerializer
from teams.forms import TeamPostCommentForm, TeamPostForm
from teams.models import (
    Post,
    PostComment,
    PostCommentLike,
    PostCommentReply,
    PostCommentStatus,
    PostCommentStatusDisplayName, 
    PostLike, 
    PostStatus, 
    PostStatusDisplayName, 
    Team,
    TeamLike, 
    TeamName
)
from teams.serializers import PostCommentStatusSerializer, PostStatusSerializer, TeamSerializer
from teams.services import (
    get_all_games_for_team_this_season,
    get_all_teams_season_stats, 
    get_last_n_games_log,
    get_player_last_n_games_log,
    get_monthly_games_for_team_this_season,
    get_player_career_stats,
    get_player_current_season_stats, 
    get_team_franchise_history,
    get_team_players, 
    get_team_season_stats
)
from teams.utils import convert_month_string_to_int

from users.authentication import CookieJWTAccessAuthentication

from nba_api.stats.endpoints.scoreboardv2 import ScoreboardV2

from users.serializers import PostCommentReplySerializer, PostCommentSerializer, PostSerializer, PostUpdateSerializer


# Create your views here.
class TeamViewSet(viewsets.ViewSet):
    authentication_classes = [CookieJWTAccessAuthentication]

    def get_permissions(self):
        permission_classes = []

        if self.action == 'post_team_post':
            permission_classes = [IsAuthenticated]
        elif self.action == 'like_post':
            permission_classes = [IsAuthenticated]
        elif self.action == 'unlike_post':
            permission_classes = [IsAuthenticated]
        elif self.action == 'post_comment':
            permission_classes = [IsAuthenticated]
        elif self.action == 'update_comment':
            permission_classes = [IsAuthenticated]
        elif self.action == 'like_comment':
            permission_classes = [IsAuthenticated]
        elif self.action == 'unlike_comment':
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def retrieve(self, request, pk=None):
        try:
            fields_exclude = []
            team = Team.objects.prefetch_related(
                Prefetch(
                    'teamname_set',
                    queryset=TeamName.objects.select_related(
                        'language'
                    ).filter(
                        team__id=pk
                    ).only('name', 'language__name'),
                )
            ).only(
                'id', 'symbol'
            )

            if request.user.is_authenticated:
                team = team.annotate(
                    liked=Exists(TeamLike.objects.filter(user=request.user, team=OuterRef('pk')))
                ).get(id=pk)
            else:
                fields_exclude.append('liked')
                team = team.get(id=pk)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=HTTP_404_NOT_FOUND)

        serializer = TeamSerializer(
            team,
            fields_exclude=fields_exclude,
            context={
                'teamname': {
                    'fields': ['name', 'language'],
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        data = serializer.data
        data['stats'] = get_team_season_stats(settings.SEASON_YEAR, pk)

        return Response(data)

    @method_decorator(cache_page(60*60*24))
    def list(self, request):
        teams = Team.objects.prefetch_related(
            Prefetch(
                'teamname_set',
                queryset=TeamName.objects.select_related(
                    'language'
                ).all()
            )
        ).only(
            'id', 'symbol'
        ).order_by('symbol').all()

        serializer = TeamSerializer(
            teams,
            many=True,
            fields_exclude=['likes_count', 'liked'],
            context={
                'teamname': {
                    'fields': ['name', 'language'],
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        return Response(serializer.data)

    @method_decorator(cache_page(60*60*24)) 
    @action(detail=True, methods=['get'], url_path='franchise-history')
    def get_franchise_history(self, request, pk=None):
        team_franchise_history = get_team_franchise_history(pk)
        return Response(team_franchise_history)

    ## Cache the standings for 10 minutes
    @method_decorator(cache_page(60*10)) 
    @action(detail=False, methods=['get'], url_path='standings')
    def get_standings(self, request):
        relevant_keys = [
            'TeamID',
            'TeamCity',
            'TeamName',
            'TeamAbbreviation',
            'Conference',
            'ConferenceRecord',
            'WINS',
            'LOSSES',
            'WinPCT',
            'HOME',
            'ROAD',
            'L10',
            'ClinchedPostSeason',
            'PlayoffSeeding',
        ]
        standings = get_all_teams_season_stats(settings.SEASON_YEAR)

        ## Remove irrelevant keys
        for conference in standings:
            for team in standings[conference]:
                for key in list(team.keys()):
                    if key not in relevant_keys:
                        team.pop(key)

        return Response(standings)
    
    # @method_decorator(cache_page(60*10))
    @action(detail=True, methods=['get'], url_path='players')
    def get_players(self, request, pk=None):
        players = get_team_players(pk)
        serializer = PlayerSerializer(
            players,
            many=True,
            context={
                'team': {
                    'fields': ('id', 'symbol', 'teamname_set')
                },
                'teamname': {
                    'fields': ('name', 'language')
                },
                'language': {
                    'fields': ('name',)
                }
            }
        )

        return Response(serializer.data)

    # @method_decorator(cache_page(60*10))
    @action(detail=True, methods=['get'], url_path=r'players/(?P<player_id>[^/.]+)/career-stats') 
    def get_specific_player_career_stats(self, request, pk=None, player_id=None):
        players = get_team_players(pk)
        for player in players:
            if player.id == int(player_id):
                stats = get_player_career_stats(player_id)
                serializer = PlayerCareerStatisticsSerializer(
                    stats,
                    many=True,
                    fields_exclude=['player', 'team'],
                    context={
                        'team': {
                            'fields': ('id', 'symbol', 'teamname_set')
                        },
                        'teamname': {
                            'fields': ('name', 'language')
                        },
                        'language': {
                            'fields': ('name',)
                        }
                    }
                )

                return Response(serializer.data)

        return Response(status=HTTP_404_NOT_FOUND)
    
    # @method_decorator(cache_page(60*10))
    @action(detail=True, methods=['get'], url_path=r'players/(?P<player_id>[^/.]+)/season-stats')
    def get_specific_player_season_stats(self, request, pk=None, player_id=None):
        players = get_team_players(pk)
        for player in players:
            if player.id == int(player_id):
                return Response(get_player_current_season_stats(player_id, team_id=pk))

        return Response(status=HTTP_404_NOT_FOUND)

    # @method_decorator(cache_page(60*10)) 
    @action(detail=True, methods=['get'], url_path=r'players/(?P<player_id>[^/.]+)/last-5-games')
    def get_specific_player_last_5_games(self, request, pk=None, player_id=None):
        players = get_team_players(pk)
        for player in players:
            if player.id == int(player_id):
                stats = get_player_last_n_games_log(player_id, 5)
                serializer = PlayerStatisticsSerializer(
                    stats,
                    many=True,
                    context={
                        'player': {
                            'fields': ['id', 'first_name', 'last_name']
                        },
                        'team': {
                            'fields': ('id', 'symbol')
                        },
                        'game': {
                            'fields': ('visitor_team', 'home_team'),
                        },
                    }
                )
                return Response(serializer.data)

        return Response(status=HTTP_404_NOT_FOUND)

    ## Cache the last 4 games for 1 minute to avoid unnecessary API calls and maintain the freshness of the data
    @method_decorator(cache_page(60*1)) 
    @action(detail=True, methods=['get'], url_path='last-4-games')
    def get_last_4_games(self, request, pk=None):
        game_data, linescore_data = get_last_n_games_log(pk, 4)
        return Response(combine_games_and_linescores(game_data, linescore_data))

    # @method_decorator(cache_page(60*2))
    @action(detail=True, methods=['get'], url_path='games')
    def get_all_games(self, request, pk=None):
        filter_value = request.query_params.get('filter', None)
        month = convert_month_string_to_int(filter_value) if filter_value else None

        if month:
            games = get_monthly_games_for_team_this_season(pk, month)
        else:
            games = get_all_games_for_team_this_season(pk)

        return Response(games)

    @method_decorator(cache_page(60*60*24)) 
    @action(
        detail=False,
        methods=['get'],
        url_path=r'posts/statuses',
    )
    def get_post_statuses(self, request):
        statuses = PostStatus.objects.all()
        serializer = PostStatusSerializer(
            statuses, 
            many=True,
            context={
                'poststatusdisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        return Response(serializer.data)

    # @method_decorator(cache_page(60*60*24))
    @action(
        detail=False,
        methods=['get'],
        url_path=r'posts/statuses/for-creation',
    )
    def get_post_statuses_for_creation(self, request):
        statuses = PostStatus.objects.exclude(name='deleted').prefetch_related(
            Prefetch(
                'poststatusdisplayname_set',
                queryset=PostStatusDisplayName.objects.select_related(
                    'language'
                ).all()
            )
        )
        serializer = PostStatusSerializer(
            statuses, 
            many=True,
            context={
                'poststatusdisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        return Response(serializer.data)
    
    @method_decorator(cache_page(60*60*24))
    @action(
        detail=False,
        methods=['get'],
        url_path=r'posts/comments/statuses',
    )
    def get_post_comment_statuses(self, request):
        statuses = PostCommentStatus.objects.prefetch_related(
            Prefetch(
                'postcommentstatusdisplayname_set',
                queryset=PostCommentStatusDisplayName.objects.select_related(
                    'language'
                ).all()
            )
        )

        serializer = PostCommentStatusSerializer(
            statuses, 
            many=True,
            context={
                'postcommentstatusdisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        return Response(serializer.data)

    @action(
        detail=True, 
        methods=['post'], 
        url_path=r'posts',
    )
    def post_team_post(self, request, pk=None):
        form = TeamPostForm(request.data)
        if not form.is_valid():
            return Response(form.errors.as_data(), status=HTTP_400_BAD_REQUEST)
        
        user = request.user
        data = form.cleaned_data

        try:
            team = Team.objects.get(id=pk)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=HTTP_404_NOT_FOUND)
        
        Post.objects.create(
            user=user,
            team=team,
            status=data['status'],
            title=data['title'],
            content=data['content']
        )
        
        return Response(
            {'message': 'Post created successfully!'}, 
            status=HTTP_201_CREATED
        )
    
    @post_team_post.mapping.get
    def get_team_posts(self, request, pk=None):
        try:
            team = Team.objects.get(id=pk)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=HTTP_404_NOT_FOUND)
        
        fields_exclude = ['content']
        posts = Post.objects.filter(team=team).order_by('-created_at').select_related(
            'user',
            'team',
            'status'
        ).prefetch_related(
            Prefetch(
                'postlike_set',
                queryset=PostLike.objects.filter(post__team=team)
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
        url_path=r'posts/popular'
    )
    def get_popular_posts(self, request, pk=None):
        fields_exclude = ['content']
        posts = Post.objects.annotate(
            likes_count=Count('postlike'),
        ).order_by(
            '-likes_count'
        ).select_related(
            'user',
            'team',
            'status'
        ).prefetch_related(
            Prefetch(
                'postlike_set',
                queryset=PostLike.objects.all()
            ),
            'postcomment_set',
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
        )[:10]
        # ).filter(
        #     created_at__gte=datetime.now() - timedelta(hours=24)
        # )

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
        detail=True,
        methods=['get'],
        url_path=r'posts/(?P<post_id>[^/.]+)'
    )
    def get_team_post(self, request, pk=None, post_id=None):
        user = request.user
        try:
            team = Team.objects.get(id=pk)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=HTTP_404_NOT_FOUND)

        try:
            post = Post.objects.select_related(
                'user',
                'team',
                'status'
            ).prefetch_related(
                Prefetch(
                    'postlike_set',
                    queryset=PostLike.objects.filter(post__team=team).only('id')
                ),
                Prefetch(
                    'postcomment_set',
                    queryset=PostComment.objects.filter(post__team=team).only('id')
                ),
                Prefetch(
                    'status__poststatusdisplayname_set',
                    queryset=PostStatusDisplayName.objects.select_related(
                        'language'
                    ).all()
                )
            ).only(
                'id', 
                'title', 
                'content', 
                'created_at', 
                'updated_at', 
                'user__id', 
                'user__username', 
                'team__id', 
                'team__symbol', 
                'status__id',
                'status__name'
            )

            fields_exclude = []
            if user.is_authenticated:
                post = post.annotate(
                    liked=Exists(PostLike.objects.filter(user=user, post=OuterRef('pk')))
                ).get(
                    team=team,
                    id=post_id
                )
            else:
                fields_exclude.append('liked')
                post = post.get(
                    team=team,
                    id=post_id
                )
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=HTTP_404_NOT_FOUND)

        serializer = PostSerializer(
            post,
            fields_exclude=fields_exclude,
            context={
                'team': {
                    'fields': ['id', 'symbol']
                },
                'user': {
                    'fields': ('id', 'username')
                },
                'poststatusdisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        return Response(serializer.data)
    
    @get_team_post.mapping.patch
    def edit_team_post(self, request, pk=None, post_id=None):
        try:
            post = Post.objects.get(team__id=pk, id=post_id, user=request.user)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=HTTP_404_NOT_FOUND)

        serializer = PostUpdateSerializer(post, data=request.data, partial=True) 
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {'message': 'Post updated successfully!'}, 
            status=HTTP_200_OK
        )

    @action(
        detail=True,
        methods=['post'],
        url_path=r'posts/(?P<post_id>[^/.]+)/likes'
    )
    def like_post(self, request, pk=None, post_id=None):
        try:
            post = Post.objects.get(team__id=pk, id=post_id)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=HTTP_404_NOT_FOUND)
        
        user = request.user
        PostLike.objects.get_or_create(
            user=user,
            post=post
        )

        try:
            post = Post.objects.filter(
                team__id=pk,
                id=post_id
            ).annotate(
                liked=Exists(PostLike.objects.filter(user=user, post=OuterRef('pk')))
            ).only('id').get()
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=HTTP_404_NOT_FOUND)
        
        serializer = PostSerializer(
            post,
            fields=['id', 'likes_count', 'liked']
        )

        return Response(serializer.data)
    
    @like_post.mapping.delete
    def unlike_post(self, request, pk=None, post_id=None):
        user = request.user
        try:
            like = PostLike.objects.get(user=user, post__id=post_id)
            like.delete()
        except PostLike.DoesNotExist:
            pass

        try:
            post = Post.objects.filter(
                team__id=pk,
                id=post_id
            ).annotate(
                liked=Exists(PostLike.objects.filter(user=user, post=OuterRef('pk')))
            ).only('id').get()
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=HTTP_404_NOT_FOUND)
        
        serializer = PostSerializer(
            post,
            fields=['id', 'likes_count', 'liked']
        )

        return Response(serializer.data)
    
    @like_post.mapping.get
    def get_likes(self, request, pk=None, post_id=None):
        try:
            post = Post.objects.filter(
                team__id=pk,
                id=post_id
            )

            fields = ['id', 'likes_count']
            if request.user.is_authenticated:
                post = post.annotate(
                    liked=Exists(PostLike.objects.filter(user=request.user, post=OuterRef('pk')))
                ).only('id').get()

                fields.append('liked') 
            else:
                post = post.only('id').get()
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=HTTP_404_NOT_FOUND)

        serializer = PostSerializer(
            post,
            fields=fields
        )

        return Response(serializer.data)

    @action(
        detail=True,
        methods=['get'],
        url_path=r'posts/(?P<post_id>[^/.]+)/comments'
    )
    def get_comments(self, request, pk=None, post_id=None):
        try:
            team = Team.objects.get(id=pk)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=HTTP_404_NOT_FOUND)
        
        query = PostComment.objects.filter(
            post__team=team, 
            post__id=post_id
        ).prefetch_related(
            Prefetch(
                'postcommentlike_set',
                queryset=PostCommentLike.objects.filter(post_comment__post__id=post_id).only('id')
            ),
            Prefetch(
                'postcommentreply_set',
                queryset=PostCommentReply.objects.filter(post_comment__post__id=post_id).only('id')
            ),
        ).select_related(
            'user',
            'status'
        ).only(
            'id',
            'content',
            'created_at',
            'updated_at',
            'user__id',
            'user__username',
            'status__id',
            'status__name'
        ).order_by('-created_at')

        fields_exclude = ['post_data']

        if request.user.is_authenticated:
            query = query.annotate(
                liked=Exists(PostCommentLike.objects.filter(user=request.user, post_comment=OuterRef('pk')))
            )
        else:
            fields_exclude.append('liked')

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(query, request)

        serializer = PostCommentSerializer(
            paginated_data,
            many=True,
            fields_exclude=fields_exclude,
            context={
                'user': {
                    'fields': ('id', 'username')
                },
                'status': {
                    'fields': ('id', 'name')
                }
            }
        )

        return pagination.get_paginated_response(serializer.data)
    
    @get_comments.mapping.post
    def post_comment(self, request, pk=None, post_id=None):
        try:
            team = Team.objects.get(id=pk)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=HTTP_404_NOT_FOUND)
        
        try:
            post = Post.objects.get(team=team, id=post_id)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=HTTP_404_NOT_FOUND)

        form = TeamPostCommentForm(request.data)
        if not form.is_valid():
            return Response(form.errors, status=HTTP_400_BAD_REQUEST)
        
        user = request.user
        data = form.cleaned_data

        PostComment.objects.create(
            user=user,
            post=post,
            status=PostCommentStatus.get_created_role(),
            content=data['content']
        )

        return Response(
            {'message': 'Comment created successfully!'}, 
            status=HTTP_201_CREATED
        )
    
    @action(
        detail=True,
        methods=['get'],
        url_path=r'posts/(?P<post_id>[^/.]+)/comments/(?P<comment_id>[^/.]+)'
    )
    def get_comment(self, request, pk=None, post_id=None, comment_id=None):
        try:
            team = Team.objects.get(id=pk)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=HTTP_404_NOT_FOUND)
        
        try:
            fields_exclude = ['post_data']

            comment = PostComment.objects.select_related(
                'user',
                'status'
            ).prefetch_related(
                Prefetch(
                    'postcommentlike_set',
                    queryset=PostCommentLike.objects.filter(post_comment__post__id=post_id).only('id')
                ),
                Prefetch(
                    'postcommentreply_set',
                    queryset=PostCommentReply.objects.filter(post_comment__post__id=post_id).only('id')
                ),
            ).only(
                'id',
                'content',
                'created_at',
                'updated_at',
                'user__id',
                'user__username',
                'status__id',
                'status__name'
            )

            if request.user.is_authenticated:
                comment = comment.annotate(
                    liked=Exists(PostCommentLike.objects.filter(user=request.user, post_comment=OuterRef('pk')))
                ).get(
                    post__team=team,
                    post__id=post_id,
                    id=comment_id
                )
            else:
                fields_exclude.append('liked')
        except PostComment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)

        serializer = PostCommentSerializer(
            comment,
            fields_exclude=fields_exclude,
            context={
                'user': {
                    'fields': ('id', 'username')
                },
                'status': {
                    'fields': ('id', 'name')
                }
            }
        )

        return Response(serializer.data)
    
    @get_comment.mapping.put
    def update_comment(self, request, pk=None, post_id=None, comment_id=None):
        try:
            comment = PostComment.objects.get(
                post__team__id=pk,
                post__id=post_id,
                id=comment_id,
                user=request.user
            )
        except PostComment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)
        
        form = TeamPostCommentForm(request.data)
        if not form.is_valid():
            return Response(form.errors, status=HTTP_400_BAD_REQUEST)
        
        data = form.cleaned_data
        comment.content = data['content']
        comment.save()

        return Response(
            {'message': 'Comment updated successfully!'}, 
            status=HTTP_200_OK
        )
    
    @get_comment.mapping.delete
    def delete_comment(self, request, pk=None, post_id=None, comment_id=None):
        try:
            comment = PostComment.objects.get(
                post__team__id=pk,
                post__id=post_id,
                id=comment_id,
                user=request.user
            )
        except PostComment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)
        
        comment.status = PostCommentStatus.get_deleted_role()
        comment.save()

        return Response(
            {'message': 'Comment deleted successfully!'}, 
            status=HTTP_200_OK
        )

    @action(
        detail=True,
        methods=['post'],
        url_path=r'posts/(?P<post_id>[^/.]+)/comments/(?P<comment_id>[^/.]+)/likes'
    )
    def like_comment(self, request, pk=None, post_id=None, comment_id=None):
        try:
            comment = PostComment.objects.get(
                post__id=post_id, 
                id=comment_id, 
                post__team__id=pk
            )
        except PostComment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)
        
        user = request.user
        PostCommentLike.objects.get_or_create(
            user=user,
            post_comment=comment
        )

        try:
            comment = PostComment.objects.filter(
                post__team__id=pk,
                post__id=post_id,
                id=comment_id
            ).annotate(
                liked=Exists(PostCommentLike.objects.filter(user=user, post_comment=OuterRef('pk')))
            ).only('id').get()
        except PostComment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)
        
        serializer = PostCommentSerializer(
            comment,
            fields=['id', 'likes_count', 'liked']
        )

        return Response(serializer.data)
    
    @like_comment.mapping.delete
    def unlike_comment(self, request, pk=None, post_id=None, comment_id=None):
        user = request.user
        try:
            like = PostCommentLike.objects.get(user=user, post_comment__id=comment_id)
            like.delete()
        except PostCommentLike.DoesNotExist:
            pass

        try:
            comment = PostComment.objects.filter(
                post__team__id=pk,
                post__id=post_id,
                id=comment_id
            ).annotate(
                liked=Exists(PostCommentLike.objects.filter(user=user, post_comment=OuterRef('pk')))
            ).only('id').get()
        except PostComment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)
        
        serializer = PostCommentSerializer(
            comment,
            fields=['id', 'likes_count', 'liked']
        )

        return Response(serializer.data)
    
    @like_comment.mapping.get
    def get_likes(self, request, pk=None, post_id=None, comment_id=None):
        try:
            comment = PostComment.objects.filter(
                post__team__id=pk,
                post__id=post_id,
                id=comment_id
            )

            fields = ['id', 'likes_count']
            if request.user.is_authenticated:
                comment = comment.annotate(
                    liked=Exists(PostCommentLike.objects.filter(user=request.user, post_comment=OuterRef('pk')))
                ).only('id').get()

                fields.append('liked') 
            else:
                comment = comment.only('id').get()
        except PostComment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)

        serializer = PostCommentSerializer(
            comment,
            fields=fields
        )

        return Response(serializer.data)

    @action(
        detail=True,
        methods=['post'],
        url_path=r'posts/(?P<post_id>[^/.]+)/comments/(?P<comment_id>[^/.]+)/replies'
    )
    def reply_comment(self, request, pk=None, post_id=None, comment_id=None):
        try:
            comment = PostComment.objects.get(
                post__id=post_id, 
                id=comment_id, 
                post__team__id=pk
            )
        except PostComment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)
        
        form = TeamPostCommentForm(request.data)
        if not form.is_valid():
            return Response(form.errors, status=HTTP_400_BAD_REQUEST)
        
        user = request.user
        data = form.cleaned_data

        PostCommentReply.objects.create(
            user=user,
            post_comment=comment,
            content=data['content']
        )

        return Response(
            {'message': 'Reply created successfully!'}, 
            status=HTTP_201_CREATED
        )
    
    @reply_comment.mapping.get
    def get_replies(self, request, pk=None, post_id=None, comment_id=None):
        try:
            comment = PostComment.objects.get(
                post__id=post_id, 
                id=comment_id, 
                post__team__id=pk
            )
        except PostComment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)
        
        query = PostCommentReply.objects.filter(
            post_comment=comment
        ).select_related(
            'user',
            'status'
        ).only(
            'id',
            'content',
            'created_at',
            'updated_at',
            'user__id',
            'user__username',
            'status__id',
            'status__name'
        ).order_by('-created_at')

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(query, request)

        serializer = PostCommentReplySerializer(
            paginated_data,
            many=True,
            fields_exclude=['post_comment_data'],
            context={
                'user': {
                    'fields': ('id', 'username')
                },
                'status': {
                    'fields': ('id', 'name')
                }
            }
        )

        return pagination.get_paginated_response(serializer.data)


class TeamsPostViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'], url_path='top-5')
    def get_today_top_5_popular_posts(self, request):
        scoreboard = ScoreboardV2(
            game_date='2024-10-22',
            league_id='00',
            day_offset=0
        ).get_dict()

        return Response(scoreboard)
    