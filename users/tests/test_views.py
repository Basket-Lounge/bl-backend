from datetime import datetime, timezone
from http import cookies
import uuid

from django.conf import settings
from rest_framework.test import APITestCase, APIRequestFactory, APIClient, force_authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from api.utils import MockResponse
from management.models import Inquiry, InquiryMessage, InquiryModerator, InquiryModeratorMessage, InquiryType
from teams.models import Language, Post, PostComment, PostCommentStatus, PostStatus, Team, TeamLike, TeamName
from users.authentication import CookieJWTRefreshAuthentication
from users.models import Role, User, UserChat, UserChatParticipant, UserChatParticipantMessage, UserLike
from users.services import UserChatService
from users.views import JWTViewSet, UserViewSet

from unittest.mock import patch

class UserTestCase(APITestCase):
    def setUp(self):
        regular_user = User.objects.create(
            username='testuser', 
            email="asdf@asdf.com"
        )
        regular_user.set_password('testpassword')
        regular_user.save()

        admin_user = User.objects.create(
            username='testadmin', 
            email="admin@admin.com", 
            role=Role.get_admin_role()
        )
        admin_user.set_password('testadmin')
        admin_user.save()

    def test_regular_user(self):
        user = User.objects.get(username='testuser')
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, "asdf@asdf.com")
        self.assertTrue(user.check_password('testpassword'))

        role = Role.get_regular_user_role()
        self.assertEqual(user.role, role)

    def test_admin_user(self):
        user = User.objects.get(username='testadmin')
        self.assertEqual(user.username, 'testadmin')
        self.assertEqual(user.email, "admin@admin.com")
        self.assertTrue(user.check_password('testadmin'))

        role = Role.get_admin_role()
        self.assertEqual(user.role, role)

    def test_modify_user_attributes(self):
        user = User.objects.get(username='testuser')
        user.username = 'newusername'
        user.save()

        user.refresh_from_db()
        self.assertEqual(user.username, 'newusername')

    def test_modify_user_password(self):
        user = User.objects.get(username='testuser')
        user.set_password('newpassword')
        user.save()

        user.refresh_from_db()
        self.assertTrue(user.check_password('newpassword'))

    def test_modify_user_role(self):
        user = User.objects.get(username='testuser')
        user.role = Role.get_admin_role()
        user.save()

        user.refresh_from_db()
        self.assertEqual(user.role, Role.get_admin_role())

class UserAPIEndpointTestCase(APITestCase):
    def setUp(self):
        regular_user = User.objects.create(
            username='testuser', 
            email="test@test.com",
        )
        regular_user.set_password('testpassword')
        regular_user.save()

        admin_user = User.objects.create(
            username='testadmin', 
            email="admin@test.com",
            role=Role.get_admin_role()
        )
        admin_user.set_password('testadmin')
        admin_user.save()

        korean = Language.objects.create(name='korean')
        english = Language.objects.create(name='english')

        sample_team = Team.objects.create(
            id=1,
            symbol='TST',
        )
        TeamName.objects.create(
            team=sample_team,
            language=korean,
            name='테스트'
        )
        TeamName.objects.create(
            team=sample_team,
            language=english,
            name='test'
        )
        TeamLike.objects.create(
            team=sample_team,
            user=regular_user
        )

    def test_get_user_info_of_oneself(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        factory = APIRequestFactory()
        request = factory.get(f'/api/users/me/')
        force_authenticate(request, user=user)
        view = UserViewSet.as_view({'get': 'me'})

        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email'], 'test@test.com')

        # test an anonymous user
        client = APIClient()
        response = client.get(f'/api/users/me/')

        self.assertEqual(response.status_code, 401)

    def test_get_user_info_of_another_user(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        factory = APIRequestFactory()

        # this is an anonymous request
        request = factory.get(f'/api/users/{user.id}/')
        view = UserViewSet.as_view({'get': 'retrieve'})

        response = view(request, pk=user.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertFalse('email' in response.data)
        self.assertFalse('liked' in response.data)

        # this is an authenticated request
        request = factory.get(f'/api/users/{user.id}/')
        authenticated_user = User.objects.filter(username='testadmin').first()
        force_authenticate(request, user=authenticated_user)
        view = UserViewSet.as_view({'get': 'retrieve'})

        response = view(request, pk=user.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertFalse('email' in response.data)
        self.assertTrue('liked' in response.data)
        self.assertEqual(response.data['liked'], False)

    def test_get_favorite_teams_of_oneself(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        factory = APIRequestFactory()
        request = factory.get(f'/api/users/me/favorite-teams/')
        force_authenticate(request, user=user)
        view = UserViewSet.as_view({'get': 'get_favorite_teams'})

        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['symbol'], 'TST')

        # test an anonymous user
        client = APIClient()
        response = client.get(f'/api/users/me/favorite-teams/')

        self.assertEqual(response.status_code, 401)

    def test_get_favorite_teams_of_another_user(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        factory = APIRequestFactory()

        # this is an anonymous request
        request = factory.get(f'/api/users/{user.id}/favorite-teams/')
        view = UserViewSet.as_view({'get': 'get_user_favorite_teams'})

        response = view(request, pk=user.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['symbol'], 'TST')

    def test_put_favorite_teams_of_oneself(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        # test an anonymous user
        client = APIClient()
        response = client.put(f'/api/users/me/favorite-teams/')

        self.assertEqual(response.status_code, 401)

        # User can't have more than 1 favorite team
        factory = APIRequestFactory()
        request = factory.put(
            f'/api/users/me/favorite-teams/',
            data=[
                {'id': 1, 'favorite': True},
                {'id': 2, 'favorite': True}
            ],
            format='json'
        )
        force_authenticate(request, user=user)
        view = UserViewSet.as_view({'put': 'put_favorite_teams'})

        response = view(request)
        self.assertEqual(response.status_code, 400)

        # User can't favorite a team that doesn't exist
        request = factory.put(
            f'/api/users/me/favorite-teams/',
            data=[
                {'id': 2, 'favorite': True}
            ],
            format='json'
        )

        force_authenticate(request, user=user)
        response = view(request)

        user_favorite_teams_count = TeamLike.objects.filter(
            user__username='testuser'
        ).count()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(user_favorite_teams_count, 0)

        # User can favorite a team that exists
        team = Team.objects.all().first()

        request = factory.put(
            f'/api/users/me/favorite-teams/',
            data=[
                {'id': team.id, 'favorite': True}
            ],
            format='json'
        )
        force_authenticate(request, user=user)
        response = view(request)

        user_favorite_teams_count = TeamLike.objects.filter(
            user__username='testuser'
        ).count()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(user_favorite_teams_count, 1)

        # User can unfavorite a team
        request = factory.put(
            f'/api/users/me/favorite-teams/',
            data=[
                {'id': team.id, 'favorite': False}
            ],
            format='json'
        )
        force_authenticate(request, user=user)
        response = view(request)

        user_favorite_teams_count = TeamLike.objects.filter(
            user__username='testuser',
            favorite=False
        ).count()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(user_favorite_teams_count, 1)

    def test_post_favorite_team(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        factory = APIRequestFactory()
        view = UserViewSet.as_view({'post': 'post_favorite_team'})
        team = Team.objects.all().first()

        # test an anonymous user
        request = factory.post(
            f'/api/users/me/favorite-teams/{team.id}/',
        )
        response = view(request, team_id=team.id)
        self.assertEqual(response.status_code, 401)

        # test a regular user
        request = factory.post(
            f'/api/users/me/favorite-teams/{team.id}/',
        )
        force_authenticate(request, user=user)
        response = view(request, team_id=team.id)
        self.assertEqual(response.status_code, 201)

        user_favorite_teams_count = TeamLike.objects.filter(
            user__username='testuser'
        ).count()

        self.assertEqual(user_favorite_teams_count, 1)
    
    def test_delete_favorite_team(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        factory = APIRequestFactory()
        view = UserViewSet.as_view({'delete': 'delete_favorite_team'})
        team = Team.objects.all().first()

        # test an anonymous user
        request = factory.delete(
            f'/api/users/me/favorite-teams/{team.id}/',
        )
        response = view(request, team_id=team.id)
        self.assertEqual(response.status_code, 401)

        # test a regular user
        request = factory.post(
            f'/api/users/me/favorite-teams/{team.id}/',
        )
        force_authenticate(request, user=user)
        view = UserViewSet.as_view({'post': 'post_favorite_team'})
        response = view(request, team_id=team.id)

        user_favorite_teams_count = TeamLike.objects.filter(
            user__username='testuser'
        ).count()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(user_favorite_teams_count, 1)

        request = factory.delete(
            f'/api/users/me/favorite-teams/{team.id}/',
        )
        force_authenticate(request, user=user)
        view = UserViewSet.as_view({'delete': 'delete_favorite_team'})
        response = view(request, team_id=team.id)
        self.assertEqual(response.status_code, 200)

        user_favorite_teams_count = TeamLike.objects.filter(
            user__username='testuser'
        ).count()

        self.assertEqual(user_favorite_teams_count, 0)

    def test_get_user_posts(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        factory = APIRequestFactory()
        view = UserViewSet.as_view({'get': 'get_user_posts'})

        # test an anonymous user
        request = factory.get(
            f'/api/users/{user.id}/posts/'
        )
        response = view(request, pk=user.id)
        data = response.data
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['results'], [])
        self.assertFalse(data['next'])
        self.assertFalse(data['previous'])

        # test a regular user
        force_authenticate(request, user=user)
        response = view(request, pk=user.id)
        data = response.data
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['results'], [])
        self.assertFalse(data['next'])
        self.assertFalse(data['previous'])

        team = Team.objects.all().first()
        # insert a post
        Post.objects.create(
            title='test title',
            content='test content',
            status=PostStatus.objects.get(name='created'),
            team=team,
            user=user
        )
        request = factory.get(
            f'/api/users/{user.id}/posts/'
        )
        response = view(request, pk=user.id)
        data = response.data

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 1)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['title'], 'test title')
        # Shouldn't return the content
        self.assertFalse('content' in data['results'][0])

        # Create 10 more posts
        for i in range(10):
            Post.objects.create(
                title=f'test title',
                content=f'test content',
                status=PostStatus.objects.get(name='created'),
                team=team,
                user=user
            )

        request = factory.get(
            f'/api/users/{user.id}/posts/'
        )
        response = view(request, pk=user.id)

        data = response.data
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 11)
        self.assertEqual(len(data['results']), 10)
        self.assertTrue(data['next'])
        self.assertFalse(data['previous'])

    def test_get_posts(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        factory = APIRequestFactory()
        view = UserViewSet.as_view({'get': 'get_posts'})

        # test an anonymous user
        request = factory.get(
            f'/api/users/me/posts/'
        )
        response = view(request)
        data = response.data
        self.assertEqual(response.status_code, 401)

        # test a regular user
        force_authenticate(request, user=user)
        response = view(request)
        data = response.data
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['results'], [])
        self.assertFalse(data['next'])
        self.assertFalse(data['previous'])

        team = Team.objects.all().first()

        # insert a post
        Post.objects.create(
            title='test title',
            content='test content',
            status=PostStatus.objects.get(name='created'),
            team=team,
            user=user
        )
        response = view(request)
        data = response.data

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 1)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['title'], 'test title')
        # Shouldn't return the content
        self.assertFalse('content' in data['results'][0])

        # Create 10 more posts
        for i in range(10):
            Post.objects.create(
                title=f'test title',
                content=f'test content',
                status=PostStatus.objects.get(name='created'),
                team=team,
                user=user
            )

        response = view(request)

        data = response.data
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 11)
        self.assertEqual(len(data['results']), 10)
        self.assertTrue(data['next'])
        self.assertFalse(data['previous'])

    def test_get_roles(self):
        factory = APIRequestFactory()
        view = UserViewSet.as_view({'get': 'get_roles'})

        request = factory.get(
            f'/api/users/roles/'
        )
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 6)

    def test_get_user_comments(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        factory = APIRequestFactory()
        view = UserViewSet.as_view({'get': 'get_user_comments'})

        # test an anonymous user
        request = factory.get(
            f'/api/users/{user.id}/comments/'
        )
        response = view(request, pk=user.id)
        data = response.data
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['results'], [])
        self.assertFalse(data['next'])
        self.assertFalse(data['previous'])

        # test a regular user
        force_authenticate(request, user=user)
        response = view(request, pk=user.id)
        data = response.data
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['results'], [])
        self.assertFalse(data['next'])
        self.assertFalse(data['previous'])

        team = Team.objects.all().first()

        # insert a post and a comment
        post = Post.objects.create(
            title='test title',
            content='test content',
            status=PostStatus.objects.get(name='created'),
            team=team,
            user=user
        )
        
        PostComment.objects.create(
            post=post,
            user=user,
            content='test comment',
            status=PostCommentStatus.get_created_role()
        )

        # test an anonymous user
        request = factory.get(
            f'/api/users/{user.id}/comments/'
        )
        response = view(request, pk=user.id)
        data = response.data

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 1)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['content'], 'test comment')
        self.assertFalse('liked' in data['results'][0])

        # test a regular user
        force_authenticate(request, user=user)
        response = view(request, pk=user.id)
        data = response.data

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 1)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['content'], 'test comment')
        self.assertTrue('liked' in data['results'][0])
        self.assertEqual(data['results'][0]['liked'], False)

        # Create 10 more comments
        for i in range(10):
            PostComment.objects.create(
                post=post,
                user=user,
                content='test comment',
                status=PostCommentStatus.get_created_role()
            )

        request = factory.get(
            f'/api/users/{user.id}/comments/'
        )
        response = view(request, pk=user.id)
        data = response.data

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 11)
        self.assertEqual(len(data['results']), 10)
        self.assertTrue(data['next'])
        self.assertFalse(data['previous'])
        self.assertEqual(data['results'][0]['content'], 'test comment')
        self.assertFalse('liked' in data['results'][0])

    def test_get_comments(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        factory = APIRequestFactory()
        view = UserViewSet.as_view({'get': 'get_comments'})

        # test an anonymous user
        request = factory.get(
            f'/api/users/me/comments/'
        )
        response = view(request)
        data = response.data
        self.assertEqual(response.status_code, 401)

        # test a regular user
        force_authenticate(request, user=user)
        response = view(request)
        data = response.data
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['results'], [])
        self.assertFalse(data['next'])
        self.assertFalse(data['previous'])

        team = Team.objects.all().first()

        # insert a post and a comment
        post = Post.objects.create(
            title='test title',
            content='test content',
            status=PostStatus.objects.get(name='created'),
            team=team,
            user=user
        )
        
        PostComment.objects.create(
            post=post,
            user=user,
            content='test comment',
            status=PostCommentStatus.get_created_role()
        )

        # test a regular user
        force_authenticate(request, user=user)
        response = view(request)
        data = response.data

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 1)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['content'], 'test comment')
        self.assertFalse(data['previous'])
        self.assertFalse(data['next'])
        self.assertTrue('liked' in data['results'][0])
        self.assertEqual(data['results'][0]['liked'], False)

        # Create 10 more comments
        for i in range(10):
            PostComment.objects.create(
                post=post,
                user=user,
                content='test comment',
                status=PostCommentStatus.get_created_role()
            )

        response = view(request)
        data = response.data

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 11)
        self.assertEqual(len(data['results']), 10)
        self.assertTrue(data['next'])
        self.assertFalse(data['previous'])
        self.assertEqual(data['results'][0]['content'], 'test comment')
        self.assertTrue('liked' in data['results'][0])
        self.assertEqual(data['results'][0]['liked'], False)

    def test_get_chats(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        factory = APIRequestFactory()
        view = UserViewSet.as_view({'get': 'get_chats'})

        # test an anonymous user
        request = factory.get(
            f'/api/users/me/chats/'
        )
        response = view(request)
        self.assertEqual(response.status_code, 401)

        # test a regular user
        force_authenticate(request, user=user)
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['results'], [])
        self.assertFalse(response.data['next'])
        self.assertFalse(response.data['previous'])

        # Create a chat
        chat = UserChat.objects.create()
        UserChatParticipant.objects.create( 
            chat=chat,
            user=user
        )
        UserChatParticipant.objects.create(
            chat=chat,
            user=User.objects.filter(username='testadmin').first()
        )

        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(len(response.data['results'][0]['participants']), 2)
        self.assertFalse(response.data['results'][0]['participants'][0]['last_message'])
        self.assertFalse(response.data['results'][0]['participants'][1]['last_message'])
        self.assertEqual(response.data['results'][0]['participants'][0]['unread_messages_count'], 0)
        self.assertEqual(response.data['results'][0]['participants'][1]['unread_messages_count'], 0)
        self.assertTrue('user_data' in response.data['results'][0]['participants'][0])
        self.assertTrue('user_data' in response.data['results'][0]['participants'][1])


    def test_get_chat(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        user2 = User.objects.filter(username='testadmin').first()
        if not user2:
            self.fail("User not found")

        factory = APIRequestFactory()
        view = UserViewSet.as_view({'get': 'get_chat'})

        # Create a chat
        chat = UserChat.objects.create()
        part1 = UserChatParticipant.objects.create( 
            chat=chat,
            user=user
        )
        part2 = UserChatParticipant.objects.create(
            chat=chat,
            user=user2
        )

        # test an anonymous user
        request = factory.get(
            f'/api/users/me/chats/{user2.id}/'
        )
        response = view(request, pk=user2.id)
        self.assertEqual(response.status_code, 401)

        # test a regular user
        force_authenticate(request, user=user)
        response = view(request, user_id=user2.id)
        data = response.data

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['id'], str(chat.id))
        self.assertEqual(len(data['participants']), 2)
        self.assertFalse('last_message' in data['participants'][0])
        self.assertFalse('last_message' in data['participants'][1])
        self.assertFalse('unread_messages_count' in data['participants'][0])
        self.assertFalse('unread_messages_count' in data['participants'][1])
        self.assertTrue('user_data' in data['participants'][0])
        self.assertTrue('user_data' in data['participants'][1])
        self.assertTrue('messages' in data['participants'][0])
        self.assertTrue('messages' in data['participants'][1])
        self.assertEqual(len(data['participants'][0]['messages']), 0)
        self.assertEqual(len(data['participants'][1]['messages']), 0)

        # Create a message
        UserChatParticipantMessage.objects.create(
            sender=part1,
            message="test message"
        )
        UserChatParticipantMessage.objects.create(
            sender=part2,
            message="test message"
        )

        response = view(request, user_id=user2.id)
        data = response.data

        self.assertEqual(response.status_code, 200)
        self.assertTrue('messages' in data['participants'][0])
        self.assertTrue('messages' in data['participants'][1])
        self.assertEqual(len(data['participants'][0]['messages']), 1)
        self.assertEqual(len(data['participants'][1]['messages']), 1)
        self.assertEqual(data['participants'][0]['messages'][0]['message'], 'test message')
        self.assertEqual(data['participants'][1]['messages'][0]['message'], 'test message')

        # attempt to chat with oneself
        request = factory.get(
            f'/api/users/me/chats/{user.id}/'
        )
        force_authenticate(request, user=user)
        response = view(request, user_id=user.id)

        self.assertEqual(response.status_code, 400)
    
    def test_delete_chat(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        user2 = User.objects.filter(username='testadmin').first()
        if not user2:
            self.fail("User not found")

        factory = APIRequestFactory()
        view = UserViewSet.as_view({'delete': 'delete_chat'})

        # Create a chat
        chat = UserChat.objects.create()
        user_participant = UserChatParticipant.objects.create( 
            chat=chat,
            user=user
        )
        UserChatParticipant.objects.create(
            chat=chat,
            user=user2
        )

        # test an anonymous user
        request = factory.delete(
            f'/api/users/me/chats/{user2.id}/'
        )
        response = view(request, pk=user2.id)
        self.assertEqual(response.status_code, 401)

        # test a regular user
        force_authenticate(request, user=user)
        response = view(request, user_id=user2.id)
        self.assertEqual(response.status_code, 200)

        user_participant.refresh_from_db()
        self.assertTrue(user_participant.chat_deleted)
        self.assertIsNotNone(user_participant.last_deleted_at)

    @patch('requests.post', return_value=MockResponse(200, {'result': 'ok'}))
    def test_post_chat_message(self, mocked):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        user2 = User.objects.filter(username='testadmin').first()
        if not user2:
            self.fail("User not found")

        factory = APIRequestFactory()
        view = UserViewSet.as_view({'post': 'post_chat_message'})

        # Create a chat
        chat = UserChat.objects.create()
        part1 = UserChatParticipant.objects.create( 
            chat=chat,
            user=user
        )
        part2 = UserChatParticipant.objects.create(
            chat=chat,
            user=user2
        )

        # test an anonymous user
        request = factory.post(
            f'/api/users/me/chats/{user2.id}/messages/',
            data={'message': 'test message'},
            format='json'
        )
        response = view(request, user_id=user2.id)
        self.assertEqual(response.status_code, 401)

        # test a regular user
        force_authenticate(request, user=user)
        response = view(request, user_id=user2.id)
        self.assertEqual(response.status_code, 201)

        message = UserChatParticipantMessage.objects.filter(sender=part1).first()
        self.assertEqual(message.message, 'test message')


    @patch('requests.post', return_value=MockResponse(200, {'result': 'ok'}))
    def test_mark_chat_messages_as_read(self, mocked):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        user2 = User.objects.filter(username='testadmin').first()
        if not user2:
            self.fail("User not found")

        factory = APIRequestFactory()
        view = UserViewSet.as_view({'put': 'mark_chat_messages_as_read'})

        # Create a chat
        chat = UserChat.objects.create()
        part1 = UserChatParticipant.objects.create( 
            chat=chat,
            user=user
        )
        part1_last_read_at = part1.last_read_at
        part2 = UserChatParticipant.objects.create(
            chat=chat,
            user=user2
        )
        part2_last_read_at = part2.last_read_at

        # Create a message
        UserChatParticipantMessage.objects.create(
            sender=part1,
            message="test message"
        )
        UserChatParticipantMessage.objects.create(
            sender=part2,
            message="test message"
        )

        # test an anonymous user
        request = factory.put(
            f'/api/users/me/chats/{user2.id}/mark-as-read/',
        )
        response = view(request, user_id=user2.id)
        self.assertEqual(response.status_code, 401)

        # test a regular user
        force_authenticate(request, user=user)
        view(request, user_id=user2.id)

        part1.refresh_from_db()
        part2.refresh_from_db()

        self.assertEqual(part1_last_read_at, part1.last_read_at)
        self.assertNotEqual(part2.last_read_at, part2_last_read_at)

    
    def test_block_chat(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        user2 = User.objects.filter(username='testadmin').first()
        if not user2:
            self.fail("User not found")

        factory = APIRequestFactory()
        view = UserViewSet.as_view({'post': 'block_chat'})

        # Create a chat
        chat = UserChat.objects.create()
        part1 = UserChatParticipant.objects.create( 
            chat=chat,
            user=user
        )
        part1_last_blocked_at = part1.last_blocked_at
        part2 = UserChatParticipant.objects.create(
            chat=chat,
            user=user2
        )

        # test an anonymous user
        request = factory.post(
            f'/api/users/me/chats/{user2.id}/block/',
        )
        response = view(request, user_id=user2.id)
        self.assertEqual(response.status_code, 401)

        # test a regular user
        force_authenticate(request, user=user)
        response = view(request, user_id=user2.id)
        self.assertEqual(response.status_code, 200)

        part1.refresh_from_db()
        part2.refresh_from_db()

        self.assertTrue(part1.chat_blocked)
        self.assertNotEqual(part1_last_blocked_at, part1.last_blocked_at)
        self.assertFalse(part2.chat_blocked)

    def test_enable_chat(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        user2 = User.objects.filter(username='testadmin').first()
        if not user2:
            self.fail("User not found")

        factory = APIRequestFactory()
        view = UserViewSet.as_view({'post': 'enable_chat'})

        # test an anonymous user
        request = factory.post(
            f'/api/users/{user2.id}/chats/',
        )
        response = view(request, pk=user2.id)
        self.assertEqual(response.status_code, 401)

        # test a non-existing chat
        force_authenticate(request, user=user)
        response = view(request, pk=1234)
        self.assertEqual(response.status_code, 404)

        # test a regular user
        response = view(request, pk=user2.id)
        self.assertEqual(response.status_code, 201)

        chat = UserChat.objects.filter(
            userchatparticipant__user=user
        ).filter(
            userchatparticipant__user=user2
        )
        part1 = UserChatParticipant.objects.filter(
            chat=chat.first(),
            user=user
        ).first()
        if not part1:
            self.fail("UserChatParticipant not found")
        part2 = UserChatParticipant.objects.filter(
            chat=chat.first(),
            user=user2
        ).first()
        if not part2:
            self.fail("UserChatParticipant not found")

        self.assertTrue(chat.exists())
        
        # block and re-enable the chat
        UserChatService.block_chat(request, user2.id)
        part1.refresh_from_db()
        part2.refresh_from_db()

        self.assertTrue(part1.chat_blocked)
        self.assertFalse(part2.chat_blocked)
        part1_last_blocked_at = part1.last_blocked_at
        part2_last_read_at = part2.last_read_at

        response = view(request, pk=user2.id)
        part1.refresh_from_db()
        part2.refresh_from_db()

        self.assertFalse(part1.chat_blocked)
        self.assertFalse(part1.chat_deleted)
        self.assertFalse(part2.chat_blocked)
        self.assertFalse(part2.chat_deleted)
        self.assertNotEqual(part1_last_blocked_at, part1.last_blocked_at) 
        self.assertNotEqual(part2_last_read_at, part2.last_read_at)
        
        part2_last_read_at = part2.last_read_at
        part1_last_deleted_at = part1.last_deleted_at

        # delete and re-enable the chat
        UserChatService.delete_chat(request, user2.id)
        part1.refresh_from_db()
        part2.refresh_from_db()

        self.assertTrue(part1.chat_deleted)
        self.assertNotEqual(part1_last_deleted_at, part1.last_deleted_at)
        self.assertFalse(part2.chat_deleted)
        self.assertNotEqual(part2_last_read_at, part2.last_read_at)

        part2_last_read_at = part2.last_read_at
        part1_last_deleted_at = part1.last_deleted_at

        response = view(request, pk=user2.id)
        part1.refresh_from_db()
        part2.refresh_from_db()

        self.assertFalse(part1.chat_deleted)
        self.assertFalse(part1.chat_blocked)
        self.assertFalse(part2.chat_deleted)
        self.assertFalse(part2.chat_blocked)
        self.assertNotEqual(part1_last_deleted_at, part1.last_deleted_at)
        self.assertNotEqual(part2_last_read_at, part2.last_read_at)


    def test_post_like(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        user2 = User.objects.filter(username='testadmin').first()
        if not user2:
            self.fail("User not found")

        factory = APIRequestFactory()
        view = UserViewSet.as_view({'post': 'post_like'})

        # test an anonymous user
        request = factory.post(
            f'/api/users/{user.id}/likes/',
        )
        response = view(request, pk=user.id)
        self.assertEqual(response.status_code, 401)

        # test liking oneself
        force_authenticate(request, user=user)
        response = view(request, pk=user.id)
        self.assertEqual(response.status_code, 400)

        # test a regular user
        request = factory.post(
            f'/api/users/{user2.id}/likes/',
        )
        force_authenticate(request, user=user)
        response = view(request, pk=user2.id)

        self.assertEqual(response.status_code, 201)
        self.assertTrue(UserLike.objects.filter(
            user=user,
            liked_user=user2
        ).exists())

    def test_delete_like(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        user2 = User.objects.filter(username='testadmin').first()
        if not user2:
            self.fail("User not found")

        factory = APIRequestFactory()
        view = UserViewSet.as_view({'delete': 'delete_like'})

        # test an anonymous user
        request = factory.delete(
            f'/api/users/{user.id}/likes/',
        )
        response = view(request, pk=user.id)
        self.assertEqual(response.status_code, 401)

        # test unliking oneself
        force_authenticate(request, user=user)
        response = view(request, pk=user.id)
        self.assertEqual(response.status_code, 400)

        # test a regular user
        UserLike.objects.create(
            user=user,
            liked_user=user2
        )

        request = factory.delete(
            f'/api/users/{user2.id}/likes/',
        )
        force_authenticate(request, user=user)
        response = view(request, pk=user2.id)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserLike.objects.filter(
            user=user,
            liked_user=user2
        ).exists())

    def test_get_inquiries(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        factory = APIRequestFactory()
        view = UserViewSet.as_view({'get': 'get_inquiries'})

        # test an anonymous user
        request = factory.get(
            f'/api/users/me/inquiries/'
        )
        response = view(request)
        self.assertEqual(response.status_code, 401)

        # test a regular user
        force_authenticate(request, user=user)
        response = view(request)
        data = response.data

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['results'], [])
        self.assertFalse(data['next'])
        self.assertFalse(data['previous'])

        # Create an inquiry
        inquiry_type = InquiryType.objects.all().first()
        inquiry = Inquiry.objects.create(
            user=user,
            inquiry_type=inquiry_type,
            title='test title',
        )

        InquiryMessage.objects.create(
            inquiry=inquiry,
            message='test message',
        )

        response = view(request)
        data = response.data

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 1)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['title'], 'test title')
        self.assertFalse('messages' in data['results'][0])
        self.assertFalse('unread_messages_count' in data['results'][0])
        self.assertFalse('user_data' in data['results'][0])
        self.assertTrue('last_message' in data['results'][0])
        self.assertTrue('inquiry_type_data' in data['results'][0])
        self.assertTrue('moderators' in data['results'][0])
        self.assertEqual(data['results'][0]['last_message']['message'], 'test message')
        self.assertEqual(data['results'][0]['inquiry_type_data']['name'], inquiry_type.name)
        self.assertEqual(data['results'][0]['moderators'], [])

        # Create 10 more inquiries
        admin = User.objects.filter(username='testadmin').first()
        if not admin:
            self.fail("User not found")

        for i in range(10):
            inquiry = Inquiry.objects.create(
                user=user,
                inquiry_type=inquiry_type,
                title='test title',
            )
            InquiryMessage.objects.create(
                inquiry=inquiry,
                message='test message',
            )

            moderator = InquiryModerator.objects.create(
                inquiry=inquiry,
                moderator=admin
            )
            InquiryModeratorMessage.objects.create(
                inquiry_moderator=moderator,
                message='test message'
            )

        response = view(request)
        data = response.data

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 11)
        self.assertEqual(len(data['results']), 10)
        self.assertTrue(data['next'])
        self.assertFalse(data['previous'])

        for inquiry in data['results']:
            self.assertEqual(inquiry['title'], 'test title')
            self.assertFalse('messages' in inquiry)
            self.assertFalse('unread_messages_count' in inquiry)
            self.assertFalse('user_data' in inquiry)
            self.assertTrue('last_message' in inquiry)
            self.assertTrue('inquiry_type_data' in inquiry)
            self.assertTrue('moderators' in inquiry)
            self.assertTrue('moderator_data' in inquiry['moderators'][0])
            self.assertTrue('last_message' in inquiry['moderators'][0])
            self.assertTrue('unread_messages_count' in inquiry['moderators'][0])
            self.assertEqual(inquiry['last_message']['message'], 'test message')
            self.assertEqual(inquiry['inquiry_type_data']['name'], inquiry_type.name) 
            self.assertEqual(len(inquiry['moderators']), 1)
            self.assertEqual(inquiry['moderators'][0]['moderator_data']['username'], admin.username)
            self.assertEqual(inquiry['moderators'][0]['last_message']['message'], 'test message')
            self.assertEqual(inquiry['moderators'][0]['unread_messages_count'], 1)
    
    def test_get_inquiry(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        admin = User.objects.filter(username='testadmin').first()
        if not admin:
            self.fail("User not found")

        factory = APIRequestFactory()
        view = UserViewSet.as_view({'get': 'get_inquiry'})

        # Create an inquiry
        inquiry_type = InquiryType.objects.all().first()
        inquiry = Inquiry.objects.create(
            user=user,
            inquiry_type=inquiry_type,
            title='test title',
        )
        InquiryMessage.objects.create(
            inquiry=inquiry,
            message='test message',
        )

        moderator = InquiryModerator.objects.create(
            inquiry=inquiry,
            moderator=admin
        )
        InquiryModeratorMessage.objects.create(
            inquiry_moderator=moderator,
            message='test message'
        )

        # test an anonymous user
        request = factory.get(
            f'/api/users/me/inquiries/{inquiry.id}/'
        )
        response = view(request, inquiry_id=inquiry.id)
        self.assertEqual(response.status_code, 401)

        # test a regular user
        force_authenticate(request, user=user)
        response = view(request, inquiry_id=inquiry.id)
        data = response.data

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['id'], str(inquiry.id))
        self.assertEqual(data['title'], 'test title')
        self.assertFalse('user_data' in data)
        self.assertFalse('last_message' in data)
        self.assertFalse('unread_messages_count' in data)
        self.assertTrue('messages' in data)
        self.assertTrue('inquiry_type_data' in data)
        self.assertTrue('moderators' in data)
        self.assertEqual(data['inquiry_type_data']['name'], inquiry_type.name)
        self.assertEqual(len(data['moderators']), 1)
        self.assertEqual(len(data['messages']), 1)
        self.assertEqual(data['messages'][0]['message'], 'test message')
        self.assertFalse('last_message' in data['moderators'][0])
        self.assertFalse('unread_messages_count' in data['moderators'][0])
        self.assertFalse('inquiry_data' in data['moderators'][0])
        self.assertTrue('messages' in data['moderators'][0])
        self.assertTrue('moderator_data' in data['moderators'][0])
        self.assertEqual(data['moderators'][0]['moderator_data']['username'], admin.username)
        self.assertEqual(len(data['moderators'][0]['messages']), 1)
        self.assertEqual(data['moderators'][0]['messages'][0]['message'], 'test message')

    def test_mark_inquiry_messages_as_read(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        admin = User.objects.filter(username='testadmin').first()
        if not admin:
            self.fail("User not found")

        factory = APIRequestFactory()
        view = UserViewSet.as_view({'put': 'mark_inquiry_messages_as_read'})

        # Create an inquiry
        inquiry_type = InquiryType.objects.all().first()
        inquiry = Inquiry.objects.create(
            user=user,
            inquiry_type=inquiry_type,
            title='test title',
        )
        InquiryMessage.objects.create(
            inquiry=inquiry,
            message='test message',
        )

        moderator = InquiryModerator.objects.create(
            inquiry=inquiry,
            moderator=admin
        )
        InquiryModeratorMessage.objects.create(
            inquiry_moderator=moderator,
            message='test message'
        )

        # test an anonymous user
        request = factory.put(
            f'/api/users/me/inquiries/{inquiry.id}/mark-as-read/',
        )
        response = view(request, inquiry_id=inquiry.id)
        self.assertEqual(response.status_code, 401)

        # test a regular user
        last_read_at = inquiry.last_read_at
        force_authenticate(request, user=user)
        response = view(request, inquiry_id=inquiry.id)
        self.assertEqual(response.status_code, 200)

        inquiry.refresh_from_db()
        self.assertNotEqual(last_read_at, inquiry.last_read_at)

        # test a non-existing inquiry
        random_uuid = str(uuid.uuid4())
        request = factory.put(
            f'/api/users/me/inquiries/{random_uuid}/mark-as-read/',
        )
        force_authenticate(request, user=user)
        response = view(request, inquiry_id=random_uuid)
        self.assertEqual(response.status_code, 404)
    
    @patch('requests.post', return_value=MockResponse(200, {'result': 'ok'}))
    def test_post_inquiry_message(self, mocked):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        admin = User.objects.filter(username='testadmin').first()
        if not admin:
            self.fail("User not found")

        factory = APIRequestFactory()
        view = UserViewSet.as_view({'post': 'post_inquiry_message'})

        # Create an inquiry
        inquiry_type = InquiryType.objects.all().first()
        inquiry = Inquiry.objects.create(
            user=user,
            inquiry_type=inquiry_type,
            title='test title',
        )
        InquiryModerator.objects.create(
            inquiry=inquiry,
            moderator=admin
        )

        # test an anonymous user
        request = factory.post(
            f'/api/users/me/inquiries/{inquiry.id}/messages/',
            data={'message': 'test message'},
            format='json'
        )
        response = view(request, inquiry_id=inquiry.id)
        self.assertEqual(response.status_code, 401)

        # test a regular user
        force_authenticate(request, user=user)
        response = view(request, inquiry_id=inquiry.id)
        self.assertEqual(response.status_code, 201)

        message = InquiryMessage.objects.filter(inquiry=inquiry).first()
        if not message:
            self.fail("InquiryMessage not found")

        self.assertEqual(message.message, 'test message')

        # test an empty message
        request = factory.post(
            f'/api/users/me/inquiries/{inquiry.id}/messages/',
            data={'message': ''},
            format='json'
        )
        force_authenticate(request, user=user)
        response = view(request, inquiry_id=inquiry.id)
        self.assertEqual(response.status_code, 400)


class JWTViewSetTestCase(APITestCase):
    def setUp(self):
        regular_user = User.objects.create(
            username='testuser', 
            email="asdf@asdf.com"
        )
        regular_user.set_password('testpassword')
        regular_user.save()

    def test_refresh(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        factory = APIRequestFactory()
        view = JWTViewSet.as_view({'post': 'refresh'})

        # test an anonymous user
        request = factory.post(
            f'/api/token/refresh/',
        )
        request.auth = None
        response = view(request)
        self.assertEqual(response.status_code, 401)

        # test a regular user
        user = User.objects.filter(username='testuser').first()
        token = RefreshToken.for_user(user)
        force_authenticate(request, user=user, token=token)
        response = view(request)
        data = response.data

        self.assertEqual(response.status_code, 201)
        self.assertTrue('username' in data)
        self.assertTrue('email' in data)
        self.assertTrue('id' in data)
        self.assertEqual(data['username'], user.username)
        self.assertEqual(data['email'], user.email)
        self.assertEqual(data['id'], user.id)

        response_cookies : cookies.SimpleCookie = response.cookies
        refresh_token_cookie_key = settings.SIMPLE_JWT.get('AUTH_REFRESH_TOKEN_COOKIE', 'refresh')
        access_token_cookie_key = settings.SIMPLE_JWT.get('AUTH_ACCESS_TOKEN_COOKIE', 'access')
        secure = settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', True)
        httpOnly = settings.SIMPLE_JWT.get('AUTH_COOKIE_HTTP_ONLY', True)
        path = settings.SIMPLE_JWT.get('AUTH_COOKIE_PATH', '/')
        domain = settings.SIMPLE_JWT.get('AUTH_COOKIE_DOMAIN', None) if settings.SIMPLE_JWT.get('AUTH_COOKIE_DOMAIN', None) else ''
        samesite = settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax')

        self.assertTrue(refresh_token_cookie_key in response_cookies)
        self.assertTrue(access_token_cookie_key in response_cookies)
        self.assertEqual(response_cookies[refresh_token_cookie_key]['path'], path)
        self.assertEqual(response_cookies[access_token_cookie_key]['path'], path)
        self.assertEqual(response_cookies[refresh_token_cookie_key]['secure'], secure)
        self.assertEqual(response_cookies[access_token_cookie_key]['secure'], secure)
        self.assertEqual(response_cookies[refresh_token_cookie_key]['httponly'], httpOnly)
        self.assertEqual(response_cookies[access_token_cookie_key]['httponly'], httpOnly)
        self.assertEqual(response_cookies[refresh_token_cookie_key]['samesite'], samesite)
        self.assertEqual(response_cookies[access_token_cookie_key]['samesite'], samesite)
        self.assertEqual(response_cookies[refresh_token_cookie_key]['domain'], domain)
        self.assertEqual(response_cookies[access_token_cookie_key]['domain'], domain)

        date_string = response_cookies[refresh_token_cookie_key]['expires']
        date_format = '%a, %d %b %Y %H:%M:%S %Z'
        converted_date = datetime.strptime(date_string, date_format)
        converted_date = converted_date.replace(tzinfo=timezone.utc)
        self.assertEqual(converted_date, datetime.fromtimestamp(token.get('exp'), tz=timezone.utc))