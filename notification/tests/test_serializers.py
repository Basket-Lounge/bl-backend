from rest_framework.test import APITestCase

from notification.models import Notification, NotificationActor, NotificationRecipient, NotificationTemplate, NotificationTemplateBody
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

        team = Team.objects.all().first()

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
        post_comment = PostComment.objects.create(
            post=post,
            user=user,
            content='Test comment',
            status=PostCommentStatus.objects.get(name='created')
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

        actor = NotificationActor.objects.create(
            notification=notification,
            user=user,
            team=team,
            post=post,
            comment=post_comment
        )

        notification_user2 = Notification.objects.create(
            template=template,
        )

        actor_user2 = NotificationActor.objects.create(
            notification=notification_user2,
            user=user2,
            team=team,
            post=post,
            comment=post_comment_user2
        )

        recipient = NotificationRecipient.objects.create(
            notification=notification,
            recipient=user
        )

        recipient_user2 = NotificationRecipient.objects.create(
            notification=notification_user2,
            recipient=user2
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
                    'fields': ['id', 'recipient']
                },
                'user': {
                    'fields': ['id', 'username', 'favorite_team']
                },
                'post': {
                    'fields': ['id', 'title']
                },
                'postcomment': {
                    'fields': ['id']
                },
                'team': {
                    'fields': ['id', 'symbol']
                },
                'game': {
                    'fields': ['game_id', 'name']
                },
                'player': {
                    'fields': ['id', 'name']
                },
                'postcommentreply': {
                    'fields': ['id']
                },
                'userchat': {
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

        self.assertEqual(notification_item['template_data']['id'], str(notification.template.id))
        self.assertEqual(len(notification_item['actors']), 1)
        self.assertEqual(notification_item['picture_url'], None)
        FRONTEND_URL = settings.FRONTEND_URL
        redirect_url = f'{FRONTEND_URL}/teams/{notification_item["actors"][0]["team_data"]["id"]}/posts/{notification_item["actors"][0]["post_data"]["id"]}/'
        if FRONTEND_URL is None:
            self.fail('FRONTEND_URL is not set in settings')

        self.assertEqual(notification_item['redirect_url'], redirect_url)

        # user2 should have 1 notification
        user2 = User.objects.get(username='testuser2')
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
            notificationrecipient__recipient__username='testuser2'
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
                    'fields': ['id', 'recipient']
                },
                'user': {
                    'fields': ['id', 'username', 'favorite_team']
                },
                'post': {
                    'fields': ['id', 'title']
                },
                'postcomment': {
                    'fields': ['id']
                },
                'team': {
                    'fields': ['id', 'symbol']
                },
                'game': {
                    'fields': ['game_id', 'name']
                },
                'player': {
                    'fields': ['id', 'name']
                },
                'postcommentreply': {
                    'fields': ['id']
                },
                'userchat': {
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

        self.assertEqual(notification_item['template_data']['id'], str(notification.template.id))
        self.assertEqual(len(notification_item['actors']), 1)
        picture_url = f'/logos/{notification_item["actors"][0]["user_data"]["favorite_team"]["symbol"]}.svg'
        self.assertEqual(notification_item['picture_url'], picture_url)
        redirect_url = f'{FRONTEND_URL}/teams/{notification_item["actors"][0]["team_data"]["id"]}/posts/{notification_item["actors"][0]["post_data"]["id"]}/'
        self.assertEqual(notification_item['redirect_url'], redirect_url)

        self.assertTrue('English' in notification_item['contents'])
        self.assertTrue('Korean' in notification_item['contents'])

        self.assertEqual(notification_item['contents']['English'], f'{user2.username} commented on your post')
        self.assertEqual(notification_item['contents']['Korean'], f'{user2.username}님이 당신의 게시물에 댓글을 달았습니다')
