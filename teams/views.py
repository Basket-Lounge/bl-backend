from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from rest_framework.permissions import IsAuthenticated

from api.paginators import CustomPageNumberPagination
from teams.models import (
    Post,
    PostComment,
    PostCommentStatus,
    PostLike, 
    Team,
)
from teams.services import (
    PostSerializerService,
    PostService,
    TeamPlayerSerializerService,
    TeamPlayerService,
    TeamSerializerService,
    TeamService,
    TeamViewService,
    get_all_teams_season_stats, 
    get_team_franchise_history,
    get_team_season_stats
)

from users.authentication import CookieJWTAccessAuthentication

from nba_api.stats.endpoints.scoreboardv2 import ScoreboardV2


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
        team = TeamViewService.get_team(request, pk)
        if not team:
            return Response({'error': 'Team not found'}, status=HTTP_404_NOT_FOUND)

        serializer = TeamSerializerService.serialize_team(request, team)

        data = serializer.data
        data['stats'] = get_team_season_stats(settings.SEASON_YEAR, pk)

        return Response(data)

    @method_decorator(cache_page(60*60*24))
    def list(self, request):
        teams = TeamService.get_all_teams()
        serializer = TeamSerializerService.serialize_team_without_likes_count_and_liked(teams)
        return Response(serializer.data)

    @method_decorator(cache_page(60*60*24)) 
    @action(detail=True, methods=['get'], url_path='franchise-history')
    def get_franchise_history(self, request, pk=None):
        team_franchise_history = get_team_franchise_history(pk)
        return Response(team_franchise_history)

    @method_decorator(cache_page(60*60*24)) 
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
    
    @method_decorator(cache_page(60*10))
    @action(detail=True, methods=['get'], url_path='players')
    def get_players(self, request, pk=None):
        players = TeamPlayerService.get_team_players(pk)
        serializer = TeamPlayerSerializerService.serialize_players(players)
        return Response(serializer.data)

    @method_decorator(cache_page(60*60*24))
    @action(
        detail=True, 
        methods=['get'], 
        url_path=r'players/(?P<player_id>[^/.]+)/career-stats'
    ) 
    def get_specific_player_career_stats(self, request, pk=None, player_id=None):
        stats = TeamPlayerService.get_team_player_career_stats(pk, player_id)
        serializer = TeamPlayerSerializerService.serialize_player_career_stats(stats)
        return Response(serializer.data)
    
    @method_decorator(cache_page(60*60*24))
    @action(
        detail=True, 
        methods=['get'], 
        url_path=r'players/(?P<player_id>[^/.]+)/season-stats'
    )
    def get_specific_player_season_stats(self, request, pk=None, player_id=None):
        player = TeamPlayerService.get_team_player_with_season_stats(player_id)
        serializer = TeamPlayerSerializerService.serialize_player_for_season_stats(player)
        return Response(serializer.data['season_stats'])

    @method_decorator(cache_page(60*10)) 
    @action(
        detail=True, 
        methods=['get'], 
        url_path=r'players/(?P<player_id>[^/.]+)/last-5-games'
    )
    def get_specific_player_last_5_games(self, request, pk=None, player_id=None):
        stats = TeamPlayerService.get_team_player_last_n_games_log(player_id, 5)
        serializer = TeamPlayerSerializerService.serialize_player_games_stats(stats)
        return Response(serializer.data)

    @method_decorator(cache_page(60*1)) 
    @action(detail=True, methods=['get'], url_path='last-4-games')
    def get_last_4_games(self, request, pk=None):
        data = TeamService.get_and_serialize_team_last_n_games(pk, 4)
        return Response(data)

    @method_decorator(cache_page(60*60))
    @action(detail=True, methods=['get'], url_path='games')
    def get_all_games(self, request, pk=None):
        games = TeamService.get_all_games(pk)
        serializer = TeamSerializerService.serialize_all_games(games)
        return Response(serializer.data)

    @method_decorator(cache_page(60*60*24)) 
    @action(
        detail=False,
        methods=['get'],
        url_path=r'posts/statuses',
    )
    def get_post_statuses(self, request):
        statuses = PostService.get_all_statuses()
        serializer = PostSerializerService.serialize_post_statuses(statuses)
        return Response(serializer.data)

    @method_decorator(cache_page(60*60*24))
    @action(
        detail=False,
        methods=['get'],
        url_path=r'posts/statuses/for-creation',
    )
    def get_post_statuses_for_creation(self, request):
        statuses = PostService.get_statuses_for_post_creation()
        serializer = PostSerializerService.serialize_post_statuses(statuses)
        return Response(serializer.data)
    
    @method_decorator(cache_page(60*60*24))
    @action(
        detail=False,
        methods=['get'],
        url_path=r'posts/comments/statuses',
    )
    def get_post_comment_statuses(self, request):
        statuses = PostService.get_comment_statuses()
        serializer = PostSerializerService.serialize_post_comment_statuses(statuses)
        return Response(serializer.data)

    @action(
        detail=True, 
        methods=['post'], 
        url_path=r'posts',
    )
    def post_team_post(self, request, pk=None):
        created, error = PostService.create_post(request, pk)
        if error:
            return Response(error, status=HTTP_400_BAD_REQUEST)

        return Response(status=HTTP_201_CREATED)
    
    @post_team_post.mapping.get
    def get_team_posts(self, request, pk=None):
        try:
            Team.objects.get(id=pk)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=HTTP_404_NOT_FOUND)
        
        posts = PostService.get_team_posts(request, pk)

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(posts, request)

        serializer = PostSerializerService.serialize_posts(request, paginated_data)
        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'posts/popular'
    )
    def get_popular_posts(self, request, pk=None):
        posts = PostService.get_10_popular_posts(request)

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(posts, request)

        serializer = PostSerializerService.serialize_posts(request, paginated_data)
        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=True,
        methods=['get'],
        url_path=r'posts/popular'
    )
    def get_team_popular_posts(self, request, pk=None):
        try:
            team = Team.objects.get(id=pk)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=HTTP_404_NOT_FOUND)
        
        posts = PostService.get_team_10_popular_posts(request, team)

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(posts, request)

        serializer = PostSerializerService.serialize_posts(request, paginated_data)
        return pagination.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=['get'],
        url_path=r'posts/(?P<post_id>[^/.]+)'
    )
    def get_team_post(self, request, pk=None, post_id=None):
        try:
            Team.objects.get(id=pk)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=HTTP_404_NOT_FOUND)

        post = PostService.get_post(request, pk, post_id)
        if not post:
            return Response({'error': 'Post not found'}, status=HTTP_404_NOT_FOUND)

        serializer = PostSerializerService.serialize_post(request, post)
        return Response(serializer.data)
    
    @get_team_post.mapping.patch
    def edit_team_post(self, request, pk=None, post_id=None):
        try:
            post = Post.objects.get(team__id=pk, id=post_id, user=request.user)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=HTTP_404_NOT_FOUND)

        PostService.update_post(request, post)
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

        post = PostService.get_post_after_creating_like(request, pk, post_id)
        serializer = PostSerializerService.serialize_post_after_like(post)
        return Response(serializer.data)
    
    @like_post.mapping.delete
    def unlike_post(self, request, pk=None, post_id=None):
        user = request.user
        try:
            like = PostLike.objects.get(user=user, post__id=post_id)
            like.delete()
        except PostLike.DoesNotExist:
            pass

        post = PostService.get_post_after_creating_like(request, pk, post_id)
        serializer = PostSerializerService.serialize_post_after_like(post)
        return Response(serializer.data)
    
    @like_post.mapping.get
    def get_likes(self, request, pk=None, post_id=None):
        post = PostService.get_post_after_creating_like(request, pk, post_id)
        serializer = PostSerializerService.serialize_post_after_like(post)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['get'],
        url_path=r'posts/(?P<post_id>[^/.]+)/comments'
    )
    def get_comments(self, request, pk=None, post_id=None):
        try:
            Team.objects.get(id=pk)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=HTTP_404_NOT_FOUND)
        
        comments = TeamViewService.get_comments(request, pk, post_id)

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(comments, request)

        serializer = PostSerializerService.serialize_comments_for_post(request, paginated_data)
        return pagination.get_paginated_response(serializer.data)
    
    @get_comments.mapping.post
    def post_comment(self, request, pk=None, post_id=None):
        try:
            post = Post.objects.get(team__id=pk, id=post_id)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=HTTP_404_NOT_FOUND)

        created, error = PostService.create_comment(request, post)
        if error:
            return Response(error, status=HTTP_400_BAD_REQUEST)

        return Response(
            {'message': 'Comment created successfully!'}, 
            status=HTTP_201_CREATED
        )
    
    @action(
        detail=True,
        methods=['get'],
        url_path=r'posts/(?P<post_id>[^/.]+)/comments/(?P<comment_id>[^/.]+)'
    )
    def get_comment(
        self, 
        request, 
        pk=None, 
        post_id=None, 
        comment_id=None
    ):
        try:
            team = Team.objects.get(id=pk)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=HTTP_404_NOT_FOUND)
        
        comment = TeamViewService.get_comment(request, team, post_id, comment_id)
        if not comment:
            return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)

        serializer = PostSerializerService.serialize_comment(request, comment)
        return Response(serializer.data)
    
    @get_comment.mapping.put
    def update_comment(
        self, 
        request, 
        pk=None, 
        post_id=None, 
        comment_id=None
    ):
        try:
            comment = PostComment.objects.get(
                post__team__id=pk,
                post__id=post_id,
                id=comment_id,
                user=request.user
            )
        except PostComment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)

        PostService.update_comment(request, comment)        

        return Response(
            {'message': 'Comment updated successfully!'}, 
            status=HTTP_200_OK
        )
    
    @get_comment.mapping.delete
    def delete_comment(
        self, 
        request, 
        pk=None, 
        post_id=None, 
        comment_id=None
    ):
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
        
        comment = PostService.like_comment(request, pk, post_id, comment) 
        serializer = PostSerializerService.serialize_comment_after_like(comment)
        return Response(serializer.data)
    
    @like_comment.mapping.delete
    def unlike_comment(self, request, pk=None, post_id=None, comment_id=None):
        comment = PostService.unlike_comment(request, pk, post_id, comment_id)
        serializer = PostSerializerService.serialize_comment_after_like(comment) 
        return Response(serializer.data)
    
    @like_comment.mapping.get
    def get_likes(self, request, pk=None, post_id=None, comment_id=None):
        comment = PostService.get_comment_with_likes_only(request, pk, post_id, comment_id)
        if not comment:
            return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)

        serializer = PostSerializerService.serialize_comment_with_likes_only(comment) 
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

        created, error = PostService.create_comment_reply(request, comment)        
        if error:
            return Response(error, status=HTTP_400_BAD_REQUEST)

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
        
        replies = PostService.get_comment_replies(comment_id)

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(replies, request)

        serializer = PostSerializerService.serialize_comment_replies(paginated_data)
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
    