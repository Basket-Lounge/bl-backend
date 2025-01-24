from datetime import datetime
from typing import List, Union
from api.exceptions import AnonymousUserError, NotFoundError, BadRequestError
from api.utils import is_valid_uuid
from games.models import Game
from notification.models import (
    Notification, 
    NotificationActor, 
    NotificationRecipient, 
    NotificationTemplate, 
    NotificationTemplateBody,
    NotificationTemplateType,
    NotificationTemplateTypeDisplayName,
)
from players.models import Player
from teams.models import Post, PostComment, PostCommentReply, Team, TeamLike
from users.models import User, UserChat

from rest_framework.request import Request
from django.contrib.auth.models import AnonymousUser

from django.db.models import Prefetch
from django.db.models.manager import BaseManager


notification_queryset_allowed_order_by_fields = [
    'created_at',
    'template__type__name',
    '-created_at',
    '-template__type__name'
]

def create_notification_queryset_without_prefetch(
    request: Request,
    fields_only=[], 
    **kwargs
) -> BaseManager[Notification]:
    """
    Create a queryset for the Notification model without prefetching related models.\n

    Args:
        request (Request): The request object.
        fields_only (list): The fields to include in the queryset.
        **kwargs: The filters to apply to the queryset.

    Returns:
        QuerySet: The queryset of notifications.
    """

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

    types_filter : str | None = request.query_params.get('types', None)
    if types_filter is not None:
        unfiltered_types = types_filter.split(',')
        types_filter = []

        for type in unfiltered_types:
            try:
                types_filter.append(int(type))
            except ValueError:
                pass
        
        if types_filter:
            queryset = queryset.filter(template__type__id__in=types_filter)

    if sort_by is not None:
        queryset = queryset.order_by(*sort_by)
    else:
        queryset = queryset.order_by('-created_at')

    if fields_only:
        return queryset.only(*fields_only)

    return queryset


class NotificationService:
    @staticmethod
    def create_notification(template: NotificationTemplate, data: dict | None = None) -> Notification:
        """
        Create a notification.

        Args:
            template (NotificationTemplate): The template for the notification.
            data (dict): The data to include in the notification.

        Returns:
            Notification: The notification that was created.
        """

        notification = Notification.objects.create(
            template=template,
            data=data
        )
        return notification

    @staticmethod
    def create_notification_actor(
        notification: Notification, 
        actors: List[Union[User, Post, PostComment, PostCommentReply, Game, Player, Team, UserChat]]
    ) -> NotificationActor:
        """
        Create a notification actor.

        Args:
            notification (Notification): The notification to send.
            actors (List[Union[User, Post, PostComment, PostCommentReply, Game, Player, Team, UserChat]]): The actors in the notification.

        Returns:
            NotificationActor: The notification actor that was created.
        """

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
    def create_notification_recipient(notification: Notification, recipient: User) -> NotificationRecipient:
        """
        Create a notification recipient.

        Args:
            notification (Notification): The notification to send.
            recipient (User): The user to send the notification to.

        Returns:
            NotificationRecipient: The notification recipient that was created.
        """

        recipient = NotificationRecipient.objects.create(
            notification=notification,
            recipient=recipient
        )

        return recipient
    
    @staticmethod
    def get_notification_template_types() -> BaseManager[NotificationTemplateType]:
        """
        Get all notification template types.

        Returns:
            BaseManager[NotificationTemplateTypeDisplayName]: The QuerySet of notification template types.
        """

        return NotificationTemplateType.objects.prefetch_related(
            Prefetch(
                'notificationtemplatetypedisplayname_set',
                queryset=NotificationTemplateTypeDisplayName.objects.select_related(
                    'language'
                )
            )
        )
    
    @staticmethod
    def get_user_notifications_with_request(request: Request) -> BaseManager[Notification]:
        '''
        Get the notifications for a user.

        Args:
            request (Request): The request object.

        Returns:
            BaseManager[Notification]: The QuerySet of notifications.
        '''

        notifications = create_notification_queryset_without_prefetch(
            request,
            notificationrecipient__recipient=request.user,
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
            ),
            Prefetch(
                'template__type__notificationtemplatetypedisplayname_set',
                queryset=NotificationTemplateTypeDisplayName.objects.select_related(
                    'language'
                )
            )
        )

        return notifications
    
    @staticmethod
    def get_user_unread_notifications_with_request(request: Request) -> BaseManager[Notification]:
        '''
        Get the unread notifications for a user. 
        Requires the request object for dynamically filtering the queryset.

        Args:
            request (Request): The request object.

        Returns:
            BaseManager[Notification]: The QuerySet of unread notifications.
        '''

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
            ),
            Prefetch(
                'template__type__notificationtemplatetypedisplayname_set',
                queryset=NotificationTemplateTypeDisplayName.objects.select_related(
                    'language'
                )
            )
        )

        return notifications
    
    @staticmethod
    def get_user_unread_notifications_count(user: User) -> int:
        '''
        Get the number of unread notifications for a user.

        Args:
            user (User): The user to get the notifications for.

        Returns:
            int: The number of unread notifications.
        '''

        if user == AnonymousUser:
            raise AnonymousUserError()

        return Notification.objects.filter(
            notificationrecipient__recipient=user,
            notificationrecipient__read=False
        ).count()
    
    @staticmethod
    def delete_user_notifications(user: User, data: List[str] | None | dict = None) -> None:
        """
        Delete a user's notifications.

        Args:
            user (User): The user who received the notifications.
            data (List[str]): The IDs of the notifications to delete.
        """

        queryset = NotificationRecipient.objects.filter(
            recipient=user,
        )

        if bool(data) == True: 
            if not isinstance(data, list):
                raise BadRequestError('Data must be a list of UUID strings')
            
            for item in data:
                is_valid = is_valid_uuid(item)
                if not is_valid:
                    raise BadRequestError('Data must be a list of UUID strings')

            queryset = queryset.filter(
                notification__id__in=data
            )
        
        queryset.update(
            deleted=True,
            deleted_at=datetime.now()
        ) 

    @staticmethod
    def mark_user_notifications_as_read(user: User, data: List[str] | None = None) -> None:
        """
        Mark a user's notifications as read.

        Args:
            user (User): The user who received the notifications.
        """

        queryset = NotificationRecipient.objects.filter(
            recipient=user,
        )

        if bool(data) == True:
            if not isinstance(data, list):
                raise BadRequestError('Data must be a list of UUID strings')
            
            for item in data:
                is_valid = is_valid_uuid(item)
                if not is_valid:
                    raise BadRequestError('Data must be a list of UUID strings')

            queryset = queryset.filter(
                notification__id__in=data
            )
        
        queryset.update(
            read=True,
            read_at=datetime.now()
        )

    @staticmethod
    def get_user_notification_by_id(
        notification_id: str,
        user: User
    ) -> Notification | None:
        """
        Get a user's notification by ID.

        Args:
            notification_id (str): The ID of the notification.
            user (User): The user who received the notification.

        Returns:
            Notification | None: The notification if it exists, None otherwise.
        """

        notification = Notification.objects.filter(
            id=notification_id,
            notificationrecipient__recipient=user
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
            ),
            Prefetch(
                'template__type__notificationtemplatetypedisplayname_set',
                queryset=NotificationTemplateTypeDisplayName.objects.select_related(
                    'language'
                )
            )
        ).first()

        return notification
    
    @staticmethod
    def check_if_notification_exists_by_various_criteria(**kwargs) -> bool:
        """
        Check if a notification exists by various criteria.

        Args:
            **kwargs: The criteria to check.

        Returns:
            bool: True if the notification exists, False otherwise.
        """

        return Notification.objects.filter(**kwargs).exists()
    
    @staticmethod
    def create_notification_for_post_like(post: Post, number_of_likes: int) -> None:
        """
        Create a notification for how many likes a post has.

        Args:
            post (Post): The post that was liked.
            number_of_likes (int): The number of likes the post has.
        """

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
    def create_notification_for_post_comment(post: Post, user: User) -> Notification:
        """
        Create a notification for a comment on a post.

        Args:
            post (Post): The post that was commented on.
            user (User): The user who commented.

        Returns:
            Notification: The notification that was created.
        """

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

        return notification

    @staticmethod
    def create_notification_for_post_comment_reply(
        reply: PostCommentReply, 
        replies_count: int, 
        user: User
    ) -> Notification:
        """
        Create a notification for how many replies a comment has.

        Args:
            reply (PostCommentReply): The reply that was made.
            replies_count (int): The number of replies the comment has.
            user (User): The user who made the reply.

        Returns:
            Notification: The notification that was created.
        """

        if reply.post_comment.user == user:
            return

        existence = NotificationService.check_if_notification_exists_by_various_criteria(
            template__subject='comment-replies',
            data={ 'number': replies_count },
            notificationactor__comment=reply.post_comment,
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

        return notification

    def create_notification_for_post_comment_likes(
        post_comment: PostComment, 
        number_of_likes: int, 
        user: User
    ) -> Notification:
        """
        Create a notification for how many likes a comment has.

        Args:
            post_comment (PostComment): The comment that was liked.
            number_of_likes (int): The number of likes the comment has.
            user (User): The user who liked the comment.

        Returns:
            Notification: The notification that was created.
        """

        existence = NotificationService.check_if_notification_exists_by_various_criteria(
            template__subject='comment-likes',
            notificationactor__comment=post_comment,
            data={ 'number': number_of_likes },
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
            [post_comment, post_comment.post, post_comment.post.team, user]
        )

        NotificationService.create_notification_recipient(
            notification,
            post_comment.user
        )

        return notification

    @staticmethod
    def create_notification_for_user_likes(
        user: User, 
        liked_user: User, 
        number_of_likes: int
    ) -> Notification:
        """
        Create a notification for how many likes a user has.

        Args:
            user (User): The user who liked the other user.
            liked_user (User): The user who was liked.
            number_of_likes (int): The number of likes the user has.

        Returns:
            Notification: The notification that was created.
        """

        existence = NotificationService.check_if_notification_exists_by_various_criteria(
            template__subject='user-likes',
            data={ 'number': number_of_likes },
            notificationrecipient__recipient=liked_user
        )

        if existence:
            return

        template = NotificationTemplate.objects.get(subject='user-likes')
        notification = NotificationService.create_notification(
            template,
            data={
                'number': number_of_likes
            }
        )

        NotificationService.create_notification_actor(
            notification,
            [user]
        )

        NotificationService.create_notification_recipient(
            notification,
            liked_user
        )

        return notification
    
    def create_notification_for_login(
        user: User
    ) -> Notification:
        """
        Create a notification for when a user logs in.

        Args:
            user (User): The user who logged in.

        Returns:
            Notification: The notification that was created.
        """

        template = NotificationTemplate.objects.get(subject='user-login')
        notification = NotificationService.create_notification(
            template
        )

        NotificationService.create_notification_actor(
            notification,
            [user]
        )

        NotificationService.create_notification_recipient(
            notification,
            user
        )

        return notification

    @staticmethod
    def mark_user_notification_as_read(
        notification_id: str,
        user: User
    ) -> None:
        """
        Mark a user's notification as read.

        Args:
            notification_id (str): The ID of the notification.
            user (User): The user who received the notification.
        """

        queryset = NotificationRecipient.objects.filter(
            recipient=user,
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
        notification_id: str,
        user: User
    ) -> None:
        """
        Delete a user's notification.

        Args:
            notification_id (str): The ID of the notification.
            user (User): The user who received the notification.
        """

        queryset = NotificationRecipient.objects.filter(
            recipient=user,
            notification__id=notification_id
        )

        if not queryset.exists():
            raise NotFoundError()
        
        queryset.update(
            deleted=True,
            deleted_at=datetime.now()
        )