from rest_framework.test import APITestCase, APIRequestFactory, APIClient, force_authenticate

from api.utils import MockResponse
from teams.models import Language, Post, PostComment, PostCommentStatus, PostStatus, Team, TeamLike, TeamName
from users.models import Role, User, UserChat, UserChatParticipant, UserChatParticipantMessage
from users.views import UserViewSet

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