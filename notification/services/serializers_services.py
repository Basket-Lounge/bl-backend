from notification.models import (
    Notification, 
)

from notification.serializers import NotificationSerializer

from django.db.models.manager import BaseManager


class NotificationSerializerService:
    @staticmethod
    def serialize_notifications(notifications: BaseManager[Notification]) -> NotificationSerializer:
        """
        Serialize a queryset of notifications.

        Args:
        notifications (BaseManager[Notification]): The queryset of notifications.
        """

        return NotificationSerializer(
            notifications, 
            fields_exclude=[
                'actors',
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
                'notificationtemplate': {
                    'fields': ['id', 'type_data']
                },
                'notificationtemplatetype': {
                    'fields': ['display_names', 'color_code']
                },
                'notificationtemplatetypedisplayname': {
                    'fields': ['id', 'name', 'language_data']
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
    def serialize_notification(notification: Notification) -> NotificationSerializer:
        """
        Serialize a single notification.

        Args:
        notification (Notification): The notification to serialize.
        """

        return NotificationSerializer(
            notification,
            fields_exclude=[
                'actors',
                'data'
            ],
            context={
                'language': {
                    'fields': ['id', 'name']
                },
                'notificationtemplate': {
                    'fields': ['id', 'type_data']
                },
                'notificationtemplatetype': {
                    'fields': ['display_names', 'color_code']
                },
                'notificationtemplatetypedisplayname': {
                    'fields': ['id', 'name', 'language_data']
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