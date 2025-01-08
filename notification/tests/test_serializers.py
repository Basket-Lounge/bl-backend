from rest_framework.test import APITestCase

from notification.models import (
    Notification, 
    NotificationActor, 
    NotificationRecipient, 
    NotificationTemplate, 
    NotificationTemplateBody
)
from notification.serializers import NotificationSerializer
from teams.models import Post, PostComment, PostCommentStatus, PostStatus, Team, TeamLike
from users.models import User

from django.db.models import Prefetch

from django.conf import settings


class NotificationSerializerTestCase(APITestCase):
    def setUp(self):
        user = User.objects.create_user(
            username='testuser',
            email='asdf@asdf.com'
        )
        user.set_password('testpassword')
        user.save()

        user2 = User.objects.create_user(
            username='testuser2',
            email="asdf@vcxzvzxcv.com"
        )
        user2.set_password('testpassword')
        user2.save()

        team = Team.objects.filter(symbol='ATL').first()

        TeamLike.objects.create(
            team=team,
            user=user2,
            favorite=True
        )

        post = Post.objects.create(
            status=PostStatus.objects.get(name='created'),
            team=team,
            user=user,
            title='Test post',
            content='Test content'
        )

        post_comment_user2 = PostComment.objects.create(
            post=post,
            user=user2,
            content='Test comment 2',
            status=PostCommentStatus.objects.get(name='created')
        )

        # get a post-comment notification template
        template = NotificationTemplate.objects.get(
            subject='post-comment'
        )

        notification = Notification.objects.create(
            template=template,
        )

        NotificationActor.objects.create(
            notification=notification,
            user=user2, 
            team=team,
            post=post,
            comment=post_comment_user2
        )

        NotificationRecipient.objects.create(
            notification=notification,
            recipient=user
        )

    def test_notification_serializer(self):
        # user1 should have 1 notification
        notifications = Notification.objects.select_related(
            'template',
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
        ).filter(
            notificationrecipient__recipient__username='testuser'
        )

        serializer = NotificationSerializer(
            notifications, 
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

        data = serializer.data
        
        self.assertEqual(len(data), 1)

        notification = notifications[0]
        notification_item = data[0]

        self.assertTrue('id' in notification_item)
        self.assertTrue('data' in notification_item)
        self.assertTrue('template_data' in notification_item)
        self.assertTrue('actors' in notification_item)
        self.assertTrue('picture_url' in notification_item)
        self.assertTrue('redirect_url' in notification_item)
        self.assertTrue('contents' in notification_item)
        self.assertTrue('recipients' in notification_item)

        self.assertEqual(notification_item['template_data']['id'], str(notification.template.id))
        self.assertEqual(len(notification_item['actors']), 1)
        self.assertEqual(notification_item['actors'][0]['user_data']['username'], 'testuser2')
        self.assertEqual(len(notification_item['recipients']), 1)
        self.assertEqual(notification_item['recipients'][0]['read'], False)
        self.assertEqual(notification_item['recipients'][0]['read_at'], None)
        self.assertEqual(notification_item['recipients'][0]['recipient_data']['username'], 'testuser')

        team = Team.objects.filter(symbol='ATL').first()
        self.assertEqual(notification_item['picture_url'], f'/logos/{team.symbol}.svg')
        FRONTEND_URL = settings.FRONTEND_URL
        redirect_url = f'{FRONTEND_URL}/teams/{notification_item["actors"][0]["team_data"]["id"]}/posts/{notification_item["actors"][0]["post_data"]["id"]}/'
        if FRONTEND_URL is None:
            self.fail('FRONTEND_URL is not set in settings')

        self.assertEqual(notification_item['redirect_url'], redirect_url)