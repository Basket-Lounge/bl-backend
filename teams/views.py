from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from api.exceptions import CustomError
from api.paginators import CustomPageNumberPagination
from notification.services.models_services import NotificationService
from teams.models import (
    Post,
    PostComment,
    PostCommentReply,
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
        elif self.action == 'get_team_posts':
            permission_classes = []
        elif self.action == 'edit_team_post':
            permission_classes = [IsAuthenticated]
        elif self.action == 'delete_team_post':
            permission_classes = [IsAuthenticated]
        elif self.action == 'hide_post':
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
        elif self.action == 'reply_comment':
            permission_classes = [IsAuthenticated]
        elif self.action == 'delete_comment':
            permission_classes = [IsAuthenticated]
        elif self.action == 'hide_or_unhide_comment':
            permission_classes = [IsAuthenticated]
        elif self.action == 'delete_reply':
            permission_classes = [IsAuthenticated]
        elif self.action == 'hide_or_unhide_reply':
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def retrieve(self, request, pk=None):
        team = TeamService.get_team(request, pk)
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
    
    @action(
        detail=True, 
        methods=['get'], 
        url_path=r'players/(?P<player_id>[^/.]+)/season-stats'
    )
    def get_specific_player_season_stats(self, request, pk=None, player_id=None):
        season_stats = TeamPlayerService.get_team_player_with_season_stats(player_id)
        if not season_stats:
            return Response({})

        serializer = TeamPlayerSerializerService.serialize_player_for_season_stats(season_stats)
        return Response(serializer.data)

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
        team_exists = TeamService.check_team_exists(pk)
        if not team_exists:
            return Response({'error': 'Team not found'}, status=HTTP_404_NOT_FOUND)

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
        _, error = PostService.create_post(request, pk)
        if error:
            return Response(error, status=HTTP_400_BAD_REQUEST)

        return Response(status=HTTP_201_CREATED)
    
    @post_team_post.mapping.get
    def get_team_posts(self, request, pk=None):
        try:
            Team.objects.get(id=pk)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=HTTP_404_NOT_FOUND)
        
        posts = PostService.get_team_posts_with_request(request, pk)

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
        
        posts = PostService.get_team_10_popular_posts(request, team.id)

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
        post = PostService.get_post(request, pk, post_id)
        if not post:
            return Response({'error': 'Post not found'}, status=HTTP_404_NOT_FOUND)
        
        if post.status.name == 'hidden' and post.user != request.user:
            return Response({'error': 'Post not found'}, status=HTTP_404_NOT_FOUND)

        serializer = PostSerializerService.serialize_post(request, post)
        return Response(serializer.data)
    
    @get_team_post.mapping.patch
    def edit_team_post(self, request, pk=None, post_id=None):
        try:
            post = Post.objects.exclude(
                status__name='deleted'
            ).get(
                team__id=pk, 
                id=post_id, 
                user=request.user,
            )
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=HTTP_404_NOT_FOUND)

        PostService.update_post(request, post)
        return Response(
            {'message': 'Post updated successfully!'}, 
            status=HTTP_200_OK
        )

    @get_team_post.mapping.delete
    def delete_team_post(self, request, pk=None, post_id=None):
        user_id = request.user.id
        PostService.delete_post(user_id, post_id)
        return Response(status=HTTP_200_OK)

    @action(
        detail=True,
        methods=['post'],
        url_path=r'posts/(?P<post_id>[^/.]+)/likes'
    )
    def like_post(self, request, pk=None, post_id=None):
        try:
            post = Post.objects.select_related('team').get(team__id=pk, id=post_id)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=HTTP_404_NOT_FOUND)
        
        user = request.user
        PostLike.objects.get_or_create(
            user=user,
            post=post
        )

        post = PostService.get_post_after_creating_like(request, pk, post_id)
        serializer = PostSerializerService.serialize_post_after_like(request, post)

        if serializer.data['likes_count'] % 10 == 0 and serializer.data['likes_count'] != 0:
            NotificationService.create_notification_for_post_like(
                post, 
                serializer.data['likes_count']
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

        post = PostService.get_post_after_creating_like(request, pk, post_id)
        serializer = PostSerializerService.serialize_post_after_like(request, post)
        return Response(serializer.data)
    
    @like_post.mapping.get
    def get_likes(self, request, pk=None, post_id=None):
        post = PostService.get_post_after_creating_like(request, pk, post_id)
        serializer = PostSerializerService.serialize_post_after_like(request, post)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['patch'],
        url_path=r'posts/(?P<post_id>[^/.]+)/hidden'
    )
    def hide_or_unhide_post(self, request, pk=None, post_id=None):
        try:
            Post.objects.get(team__id=pk, id=post_id)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=HTTP_404_NOT_FOUND)

        is_post_hidden = PostService.check_if_post_hidden(post_id, request.user)
        if is_post_hidden:
            PostService.unhide_post(post_id, request.user)
            message = 'Post unhidden successfully!'
        else:
            PostService.hide_post(post_id, request.user)
            message = 'Post hidden successfully!'

        return Response(
            {'message': message},
            status=HTTP_200_OK
        )

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
        
        comments = PostService.get_comments(request, pk, post_id)

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

        try:
            PostService.create_comment(request, post)
            return Response(
                {'message': 'Comment created successfully!'}, 
                status=HTTP_201_CREATED
            )
        except CustomError as e:
            return Response({'error': e.message}, status=e.code)
        except ValidationError as e:
            return Response({'error': e.detail}, status=e.status_code)
    
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
        
        comment = PostService.get_comment(request, team, post_id, comment_id)
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

        try: 
            PostService.like_comment(request, comment) 
        except CustomError as e:
            return Response({'error': e.message}, status=e.code)
        except Exception as e:
            return Response({'error': 'An error occurred'}, status=HTTP_500_INTERNAL_SERVER_ERROR)

        comment = PostService.get_comment_with_likes_only(request, pk, post_id, comment.id)
        serializer = PostSerializerService.serialize_comment_after_like(comment)
        return Response(serializer.data)
    
    @like_comment.mapping.delete
    def unlike_comment(self, request, pk=None, post_id=None, comment_id=None):
        try:
            comment = PostService.unlike_comment(request, pk, post_id, comment_id)
        except CustomError as e:
            return Response({'error': e.message}, status=e.code)

        serializer = PostSerializerService.serialize_comment_after_like(comment) 
        return Response(serializer.data)
    
    @action(
        detail=True,
        methods=['patch'],
        url_path=r'posts/(?P<post_id>[^/.]+)/comments/(?P<comment_id>[^/.]+)/hidden'
    )
    def hide_or_unhide_comment(self, request, pk=None, post_id=None, comment_id=None):
        try:
            comment = PostComment.objects.get(
                post__id=post_id, 
                id=comment_id, 
                post__team__id=pk,
                status__name='created'
            )
        except PostComment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)
        
        if comment.user == request.user:
            return Response(
                {'error': 'You cannot hide your own comment'}, 
                status=HTTP_400_BAD_REQUEST
            )

        try: 
            is_comment_hidden = PostService.check_if_comment_hidden(comment_id, request.user)
            if is_comment_hidden:
                PostService.unhide_comment(comment_id, request.user)
                message = 'Comment unhidden successfully!'
            else:
                PostService.hide_comment(comment_id, request.user)
                message = 'Comment hidden successfully!'

            return Response(
                {'message': message},
                status=HTTP_200_OK
            )
        except CustomError as e:
            return Response({'error': e.message}, status=e.code)
    
    @like_comment.mapping.get
    def get_likes(self, request, pk=None, post_id=None, comment_id=None):
        comment = PostService.get_comment_with_likes_only(request, pk, post_id, comment_id)
        if not comment:
            return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)

        serializer = PostSerializerService.serialize_comment_with_likes_only(request, comment) 
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

        try:
            PostService.create_comment_reply(request, comment)        
            return Response(status=HTTP_201_CREATED)
        except CustomError as e:
            return Response({'error': e.message}, status=e.code)
        except ValidationError as e:
            return Response({'error': e.detail}, status=e.status_code)
    
    @reply_comment.mapping.get
    def get_replies(self, request, pk=None, post_id=None, comment_id=None):
        try:
            PostComment.objects.get(
                post__id=post_id, 
                id=comment_id, 
                post__team__id=pk
            )
        except PostComment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)
        
        replies = PostService.get_comment_replies(comment_id, request.user)

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(replies, request)

        serializer = PostSerializerService.serialize_comment_replies(paginated_data)
        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=True,
        methods=['delete'],
        url_path=r'posts/(?P<post_id>[^/.]+)/comments/(?P<comment_id>[^/.]+)/replies/(?P<reply_id>[^/.]+)'
    )
    def delete_reply(self, request, pk=None, post_id=None, comment_id=None, reply_id=None):
        try:
            PostCommentReply.objects.get(
                post_comment__post__id=post_id,
                post_comment__id=comment_id,
                id=reply_id,
                user=request.user
            )
        except PostCommentReply.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)

        try: 
            PostService.delete_reply(request.user, reply_id)
            return Response(
                {'message': 'Reply deleted successfully!'}, 
                status=HTTP_200_OK
            )
        except CustomError as e:
            return Response({'error': e.message}, status=e.code)
        except Exception as e:
            return Response({'error': 'An error occurred'}, status=HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(
        detail=True,
        methods=['patch'],
        url_path=r'posts/(?P<post_id>[^/.]+)/comments/(?P<comment_id>[^/.]+)/replies/(?P<reply_id>[^/.]+)/hidden'
    )
    def hide_or_unhide_reply(
        self, 
        request, 
        pk=None, 
        post_id=None, 
        comment_id=None, 
        reply_id=None
    ):
        try:
            reply = PostCommentReply.objects.get(
                post_comment__post__id=post_id,
                post_comment__id=comment_id,
                id=reply_id,
                status__name='created'
            )
        except PostCommentReply.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)
        
        if reply.user == request.user:
            return Response(
                {'error': 'You cannot hide your own reply'}, 
                status=HTTP_400_BAD_REQUEST
            )
        
        try:
            is_reply_hidden = PostService.check_if_reply_hidden(reply_id, request.user)
            if is_reply_hidden:
                PostService.unhide_reply(reply_id, request.user)
                message = 'Reply unhidden successfully!'
            else:
                PostService.hide_reply(reply_id, request.user)
                message = 'Reply hidden successfully!'

            return Response(
                {'message': message},
                status=HTTP_200_OK
            )
        except CustomError as e:
            return Response({'error': e.message}, status=e.code)
        except Exception as e:
            return Response({'error': 'An error occurred'}, status=HTTP_500_INTERNAL_SERVER_ERROR)
    
class TeamsPostViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'], url_path='top-5')
    def get_today_top_5_popular_posts(self, request):
        scoreboard = ScoreboardV2(
            game_date='2024-10-22',
            league_id='00',
            day_offset=0
        ).get_dict()

        return Response(scoreboard)
    