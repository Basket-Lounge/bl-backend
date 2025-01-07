from datetime import datetime
from typing import List, Union
from api.exceptions import AnonymousUserError, NotFoundError
from games.models import Game
from notification.models import Notification, NotificationActor, NotificationRecipient, NotificationTemplate, NotificationTemplateBody
from notification.serializers import NotificationSerializer
from players.models import Player
from teams.models import Post, PostComment, PostCommentReply, Team, TeamLike
from users.models import User, UserChat

from rest_framework.request import Request

from django.db.models import Prefetch
from django.db.models.manager import BaseManager


notification_queryset_allowed_order_by_fields = [
    'created_at',
    'notificationtemplate__notification_type__name',
    '-created_at',
    '-notificationtemplate__notification_type__name'
]

def create_notification_queryset_without_prefetch(
    request: Request,
    fields_only=[], 
    **kwargs
):
    """
    Create a queryset for the Notification model without prefetching related models.\n
    - request: request object.\n
    - fields_only: list of fields to return in the queryset.\n
    - **kwargs: keyword arguments to filter
    """

    roles_filter : str | None = request.query_params.get('roles', None)
    if roles_filter is not None:
        roles_filter = roles_filter.split(',')

    sort_by : str | None = request.query_params.get('sort', None)
    if sort_by is not None:
        sort_by : List[str] = sort_by.split(',')
        unique_sort_by = set(sort_by)

        for field in unique_sort_by:
            if field not in notification_queryset_allowed_order_by_fields:
                unique_sort_by.remove(field)

        sort_by = list(unique_sort_by)

    if kwargs is not None:
        queryset = Notification.objects.filter(**kwargs)
    else:
        queryset = Notification.objects.all()

    if roles_filter is not None:
        queryset = queryset.filter(role__id__in=roles_filter).distinct()

    if sort_by is not None:
        queryset = queryset.order_by(*sort_by)
    else:
        queryset = queryset.order_by('-created_at')

    if fields_only:
        return queryset.only(*fields_only)

    return queryset


class NotificationService:
    @staticmethod
    def create_notification(template: NotificationTemplate, data: dict | None = None):
        notification = Notification.objects.create(
            template=template,
            data=data
        )
        return notification

    @staticmethod
    def create_notification_actor(
        notification: Notification, 
        actors: List[Union[User, Post, PostComment, PostCommentReply, Game, Player, Team, UserChat]]
    ):
        filtered_actors = {}
        actor_model = {
            User: 'user',
            Post: 'post',
            PostComment: 'comment',
            PostCommentReply: 'reply',
            Game: 'game',
            Player: 'player',
            Team: 'team',
            UserChat: 'chat'
        }
        try:
            for actor in actors:
                actor_type = actor_model[type(actor)]
                filtered_actors[actor_type] = actor
        except KeyError:
            raise ValueError('Invalid actor type')

        actor = NotificationActor.objects.create(
            notification=notification,
            **filtered_actors
        )
        return actor
    
    @staticmethod
    def create_notification_recipient(notification: Notification, recipient: User):
        recipient = NotificationRecipient.objects.create(
            notification=notification,
            recipient=recipient
        )
        return recipient
    
    @staticmethod
    def get_user_notifications(request: Request, user: User):
        notifications = create_notification_queryset_without_prefetch(
            request,
            notificationrecipient__recipient=user,
            notificationrecipient__deleted=False
        ).select_related(
            'template',
            'template__type'
        ).prefetch_related(
            Prefetch(
                'notificationactor_set',
                queryset=NotificationActor.objects.select_related(
                    'user',
                    'post',
                    'comment',
                    'reply',
                    'game',
                    'player',
                    'team',
                    'chat'
                ).prefetch_related(
                    Prefetch(
                        'user__teamlike_set',
                        queryset=TeamLike.objects.select_related(
                            'team'
                        )
                    ),
                )
            ),
            Prefetch(
                'notificationrecipient_set',
                queryset=NotificationRecipient.objects.select_related(
                    'recipient'
                )
            ),
            Prefetch(
                'template__notificationtemplatebody_set',
                queryset=NotificationTemplateBody.objects.select_related(
                    'language'
                )
            )
        )

        return notifications
    
    @staticmethod
    def get_user_unread_notifications(request: Request):
        if not request.user.is_authenticated:
            raise ValueError('User is not authenticated')
        
        notifications = create_notification_queryset_without_prefetch(
            request,
            notificationrecipient__recipient=request.user,
            notificationrecipient__read=False,
            notificationrecipient__deleted=False
        ).select_related(
            'template',
            'template__type'
        ).prefetch_related(
            Prefetch(
                'notificationactor_set',
                queryset=NotificationActor.objects.select_related(
                    'user',
                    'post',
                    'comment',
                    'reply',
                    'game',
                    'player',
                    'team',
                    'chat'
                ).prefetch_related(
                    Prefetch(
                        'user__teamlike_set',
                        queryset=TeamLike.objects.select_related(
                            'team'
                        )
                    )
                )
            ),
            Prefetch(
                'notificationrecipient_set',
                queryset=NotificationRecipient.objects.select_related(
                    'recipient'
                )
            ),
            Prefetch(
                'template__notificationtemplatebody_set',
                queryset=NotificationTemplateBody.objects.select_related(
                    'language'
                )
            )
        )

        return notifications
    
    @staticmethod
    def get_user_unread_notifications_count(request: Request):
        user = request.user
        if not request.user.is_authenticated:
            raise ValueError('User is not authenticated')
        
        notification_count = create_notification_queryset_without_prefetch(
            request,
            notificationrecipient__recipient=user,
            notificationrecipient__read=False
        ).count()

        return notification_count
    
    @staticmethod
    def delete_user_notifications(request: Request):
        if not request.user.is_authenticated:
            raise AnonymousUserError()

        NotificationRecipient.objects.filter(
            recipient=request.user
        ).update(
            deleted=True,
            deleted_at=datetime.now()
        ) 

    @staticmethod
    def mark_user_notifications_as_read(request: Request):
        if not request.user.is_authenticated:
            raise AnonymousUserError()

        NotificationRecipient.objects.filter(
            recipient=request.user,
            read=False
        ).update(
            read=True,
            read_at=datetime.now()
        )

    @staticmethod
    def get_user_notification_by_id(
        request: Request,
        notification_id: str
    ):
        if not request.user.is_authenticated:
            raise ValueError('User is not authenticated')

        notification = create_notification_queryset_without_prefetch(
            request,
            id=notification_id,
            notificationrecipient__recipient=request.user
        ).select_related(
            'template',
            'template__type'
        ).prefetch_related(
            Prefetch(
                'notificationactor_set',
                queryset=NotificationActor.objects.select_related(
                    'user',
                    'post',
                    'comment',
                    'reply',
                    'game',
                    'player',
                    'team',
                    'chat'
                ).prefetch_related(
                    Prefetch(
                        'user__teamlike_set',
                        queryset=TeamLike.objects.select_related(
                            'team'
                        )
                    ),
                )
            ),
            Prefetch(
                'notificationrecipient_set',
                queryset=NotificationRecipient.objects.select_related(
                    'recipient'
                )
            ),
            Prefetch(
                'template__notificationtemplatebody_set',
                queryset=NotificationTemplateBody.objects.select_related(
                    'language'
                )
            )
        ).first()

        return notification
    
    @staticmethod
    def check_if_notification_exists_by_various_criteria(**kwargs):
        return Notification.objects.filter(**kwargs).exists()
    
    @staticmethod
    def check_if_notification_exists_by_template_subject_and_data(
        template_subject: str,
        data: dict,
        recipient: User
    ):
        return Notification.objects.filter(
            data=data,
            template__subject=template_subject,
            notificationrecipient__recipient=recipient
        ).select_related(
            'template',
            'template__type'
        ).prefetch_related(
            Prefetch(
                'notificationactor_set',
                queryset=NotificationActor.objects.select_related(
                    'user',
                    'post',
                    'comment',
                    'reply',
                    'game',
                    'player',
                    'team',
                    'chat'
                ).prefetch_related(
                    Prefetch(
                        'user__teamlike_set',
                        queryset=TeamLike.objects.select_related(
                            'team'
                        )
                    ),
                )
            ),
            Prefetch(
                'notificationrecipient_set',
                queryset=NotificationRecipient.objects.select_related(
                    'recipient'
                )
            ),
            Prefetch(
                'template__notificationtemplatebody_set',
                queryset=NotificationTemplateBody.objects.select_related(
                    'language'
                )
            )
        ).exists()
    
    @staticmethod
    def create_notification_for_post_like(post: Post, number_of_likes: int):
        existence = NotificationService.check_if_notification_exists_by_various_criteria(
            template__subject='post-likes',
            notificationactor__post=post,
            data={ 'number': number_of_likes },
            notificationrecipient__recipient=post.user
        )

        if existence:
            return

        template = NotificationTemplate.objects.get(subject='post-likes')
        notification = NotificationService.create_notification(
            template,
            data={
                'number': number_of_likes,
            }
        )

        NotificationService.create_notification_actor(
            notification,
            [post, post.team]
        )

        NotificationService.create_notification_recipient(
            notification,
            post.user
        )

    @staticmethod
    def create_notification_for_post_comment(post: Post, user: User):
        if post.user == user:
            return

        existence = NotificationService.check_if_notification_exists_by_various_criteria(
            template__subject='post-comment',
            notificationactor__post=post,
            notificationactor__user=user
        )

        if existence:
            return

        template = NotificationTemplate.objects.get(subject='post-comment')
        notification = NotificationService.create_notification(
            template
        )

        NotificationService.create_notification_actor(
            notification,
            [post, post.team, user]
        )

        NotificationService.create_notification_recipient(
            notification,
            post.user
        )

    @staticmethod
    def create_notification_for_post_comment_reply(reply: PostCommentReply, replies_count: int, user: User):
        """
        Create a notification for how many replies a comment has.
        """

        if reply.post_comment.user == user:
            return

        existence = NotificationService.check_if_notification_exists_by_various_criteria(
            template__subject='comment-replies',
            data={ 'number': replies_count },
            notificationactor__comment=reply.post_comment,
            notificationactor__user=user
        )

        if existence:
            return

        template = NotificationTemplate.objects.get(subject='comment-replies')
        notification = NotificationService.create_notification(
            template,
            data={
                'number': replies_count
            }
        )

        NotificationService.create_notification_actor(
            notification,
            [reply.post_comment, reply.post_comment.post, reply.post_comment.post.team, reply, user]
        )

        NotificationService.create_notification_recipient(
            notification,
            reply.post_comment.user
        )

    def create_notification_for_post_comment_likes(post_comment: PostComment, number_of_likes: int):
        existence = NotificationService.check_if_notification_exists_by_various_criteria(
            template__subject='comment-likes',
            notificationactor__comment=post_comment,
            data={ 'number': number_of_likes },
            notificationrecipient__recipient=post_comment.user
        )

        if existence:
            return

        template = NotificationTemplate.objects.get(subject='comment-likes')
        notification = NotificationService.create_notification(
            template,
            data={
                'number': number_of_likes
            }
        )

        NotificationService.create_notification_actor(
            notification,
            [post_comment, post_comment.post, post_comment.post.team]
        )

        NotificationService.create_notification_recipient(
            notification,
            post_comment.user
        )

    @staticmethod
    def mark_user_notification_as_read(
        request: Request,
        notification_id: str
    ):
        if not request.user.is_authenticated:
            raise AnonymousUserError()

        queryset = NotificationRecipient.objects.filter(
            recipient=request.user,
            notification__id=notification_id
        )

        if not queryset.exists():
            raise NotFoundError()

        queryset.update(
            read=True,
            read_at=datetime.now()
        )
    
    @staticmethod
    def delete_user_notification(
        request: Request,
        notification_id: str
    ):
        if not request.user.is_authenticated:
            raise AnonymousUserError()
        
        queryset = NotificationRecipient.objects.filter(
            recipient=request.user,
            notification__id=notification_id
        )

        if not queryset.exists():
            raise NotFoundError()
        
        queryset.update(
            deleted=True,
            deleted_at=datetime.now()
        )

class NotificationSerializerService:
    @staticmethod
    def serialize_notifications(notifications: BaseManager[Notification]):
        return NotificationSerializer(
            notifications, 
            fields_exclude=[
                'actors',
                'template_data',
                'data'
            ],
            many=True,
            context={
                'language': {
                    'fields': ['id', 'name']
                },
                'notificationtemplatebody': {
                    'fields': ['id', 'subject', 'body', 'language_data']
                },
                'notificationactor': {
                    'fields': [
                        'id',
                        'user_data',
                        'post_data',
                        'comment_data',
                        'reply_data',
                        'game_data',
                        'player_data',
                        'team_data',
                        'chat_data'
                    ]
                },
                'notificationrecipient': {
                    'fields': ['read', 'read_at', 'recipient_data']
                },
                'user': {
                    'fields': ['id', 'username']
                },
                'team': {
                    'fields': ['id', 'symbol']
                },
                'actor_user': {
                    'fields': ['id', 'username', 'favorite_team']
                },
                'actor_post': {
                    'fields': ['id', 'title']
                },
                'actor_postcomment': {
                    'fields': ['id']
                },
                'actor_team': {
                    'fields': ['id', 'symbol']
                },
                'actor_game': {
                    'fields': ['game_id', 'name']
                },
                'actor_player': {
                    'fields': ['id', 'name']
                },
                'actor_postcommentreply': {
                    'fields': ['id']
                },
                'actor_userchat': {
                    'fields': ['id']
                }
            }
        )
    
    @staticmethod
    def serialize_notification(notification: Notification):
        return NotificationSerializer(
            notification,
            fields_exclude=[
                'actors',
                'template_data',
                'data'
            ],
            context={
                'language': {
                    'fields': ['id', 'name']
                },
                'notificationtemplatebody': {
                    'fields': ['id', 'subject', 'body', 'language_data']
                },
                'notificationactor': {
                    'fields': [
                        'id',
                        'user_data',
                        'post_data',
                        'comment_data',
                        'reply_data',
                        'game_data',
                        'player_data',
                        'team_data',
                        'chat_data'
                    ]
                },
                'notificationrecipient': {
                    'fields': ['read', 'read_at', 'recipient_data']
                },
                'user': {
                    'fields': ['id', 'username']
                },
                'team': {
                    'fields': ['id', 'symbol']
                },
                'actor_user': {
                    'fields': ['id', 'username', 'favorite_team']
                },
                'actor_post': {
                    'fields': ['id', 'title']
                },
                'actor_postcomment': {
                    'fields': ['id']
                },
                'actor_team': {
                    'fields': ['id', 'symbol']
                },
                'actor_game': {
                    'fields': ['game_id', 'name']
                },
                'actor_player': {
                    'fields': ['id', 'name']
                },
                'actor_postcommentreply': {
                    'fields': ['id']
                },
                'actor_userchat': {
                    'fields': ['id']
                }
            }
        )