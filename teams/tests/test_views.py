from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate

from teams.models import Post, PostLike, PostStatus, Team
from teams.views import TeamViewSet
from users.models import  User


class TeamsAPIEndpointTestCase(APITestCase):
    def setUp(self):
        regular_user = User.objects.create(
            username='testuser', 
            email="test@test.com",
        )
        regular_user.set_password('testpassword')
        regular_user.save()

        regular_user2 = User.objects.create(
            username='testuser2', 
            email="asdfasdf@asdfasdf.com",
        )
        regular_user2.set_password('testpassword')
        regular_user2.save()

    def test_get_popular_posts(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        user2 = User.objects.filter(username='testuser2').first()
        if not user2:
            self.fail("User not found")

        factory = APIRequestFactory()
        request = factory.get(f'/api/teams/posts/popular/')

        view = TeamViewSet.as_view({'get': 'get_popular_posts'})
        response = view(request)

        data = response.data
        self.assertEqual(response.status_code, 200)
        self.assertTrue('results' in data)
        self.assertTrue('count' in data)
        self.assertTrue('next' in data)
        self.assertTrue('previous' in data)

        self.assertEqual(data['count'], 0)
        self.assertEqual(data['results'], [])
        self.assertIsNone(data['next'])
        self.assertIsNone(data['previous'])

        # Insert some posts
        status = PostStatus.objects.filter(name='created').first()
        deleted_status = PostStatus.objects.filter(name='deleted').first()
        hidden_status = PostStatus.objects.filter(name='hidden').first()

        team = Team.objects.all().first()

        for i in range(10):
            Post.objects.create(
                title='Fake Post',
                content='Fake Content',
                user=user,
                team=team,
                status=status,
            )

        post = Post.objects.create(
            title='Most Popular Post',
            content='Most Popular Content',
            user=user,
            team=team,
            status=status,
        )

        PostLike.objects.create(
            post=post,
            user=user,
        )

        PostLike.objects.create(
            post=post,
            user=user2,
        )

        Post.objects.create(
            title='Deleted Post',
            content='Deleted Content',
            user=user,
            team=team,
            status=deleted_status,
        )

        Post.objects.create(
            title='Hidden Post',
            content='Hidden Content',
            user=user,
            team=team,
            status=hidden_status,
        )

        request = factory.get(f'/api/teams/posts/popular/')
        response = view(request)

        data = response.data
        self.assertEqual(response.status_code, 200)
        self.assertTrue('results' in data)
        self.assertTrue('count' in data)
        self.assertTrue('next' in data)
        self.assertTrue('previous' in data)

        self.assertEqual(data['count'], 10)
        self.assertEqual(len(data['results']), 10)
        self.assertTrue(data['next'] is None)
        self.assertTrue(data['previous'] is None)
        
        first_post = data['results'][0]
        self.assertTrue('id' in first_post)
        self.assertTrue('title' in first_post)
        self.assertFalse('content' in first_post)
        self.assertFalse('liked' in first_post)
        self.assertTrue('likes_count' in first_post)
        self.assertTrue('comments_count' in first_post)
        self.assertTrue('team_data' in first_post)
        self.assertTrue('user_data' in first_post)
        self.assertTrue('status_data' in first_post)
        self.assertTrue('created_at' in first_post)
        self.assertTrue('updated_at' in first_post)

        self.assertEqual(first_post['id'], str(post.id))
        self.assertEqual(first_post['title'], post.title)
        self.assertEqual(first_post['likes_count'], 2)
        self.assertEqual(first_post['comments_count'], 0)
        self.assertEqual(first_post['team_data']['id'], team.id)
        self.assertEqual(first_post['user_data']['id'], user.id)
        self.assertEqual(first_post['status_data']['id'], status.id)
        self.assertEqual(first_post['created_at'], post.created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
        self.assertEqual(first_post['updated_at'], post.updated_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))

        force_authenticate(request, user=user)
        response = view(request)
        data = response.data

        self.assertEqual(data['count'], 10)
        self.assertEqual(len(data['results']), 10)
        self.assertTrue(data['next'] is None)
        self.assertTrue(data['previous'] is None)

        first_post = data['results'][0]
        self.assertTrue('id' in first_post)
        self.assertTrue('title' in first_post)
        self.assertFalse('content' in first_post)
        self.assertTrue('liked' in first_post)
        self.assertTrue('likes_count' in first_post)
        self.assertTrue('comments_count' in first_post)
        self.assertTrue('team_data' in first_post)
        self.assertTrue('user_data' in first_post)
        self.assertTrue('status_data' in first_post)
        self.assertTrue('created_at' in first_post)
        self.assertTrue('updated_at' in first_post)

        self.assertEqual(first_post['id'], str(post.id))
        self.assertEqual(first_post['title'], post.title)
        self.assertEqual(first_post['likes_count'], 2)
        self.assertEqual(first_post['comments_count'], 0)
        self.assertEqual(first_post['team_data']['id'], team.id)
        self.assertEqual(first_post['user_data']['id'], user.id)
        self.assertEqual(first_post['status_data']['id'], status.id)
        self.assertEqual(first_post['created_at'], post.created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
        self.assertEqual(first_post['updated_at'], post.updated_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
        self.assertTrue(first_post['liked'])


    def test_get_team_popular_posts(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        user2 = User.objects.filter(username='testuser2').first()
        if not user2:
            self.fail("User not found")

        team = Team.objects.all().first()

        factory = APIRequestFactory()
        request = factory.get(f'/api/teams/{team.id}/posts/popular/')

        view = TeamViewSet.as_view({'get': 'get_team_popular_posts'})
        response = view(request, pk=team.id)

        data = response.data
        self.assertEqual(response.status_code, 200)
        self.assertTrue('results' in data)
        self.assertTrue('count' in data)
        self.assertTrue('next' in data)
        self.assertTrue('previous' in data)

        self.assertEqual(data['count'], 0)
        self.assertEqual(data['results'], [])
        self.assertIsNone(data['next'])
        self.assertIsNone(data['previous'])

        # Insert some posts
        status = PostStatus.objects.filter(name='created').first()
        deleted_status = PostStatus.objects.filter(name='deleted').first()
        hidden_status = PostStatus.objects.filter(name='hidden').first()

        for i in range(10):
            Post.objects.create(
                title='Fake Post',
                content='Fake Content',
                user=user,
                team=team,
                status=status,
            )

        post = Post.objects.create(
            title='Most Popular Post',
            content='Most Popular Content',
            user=user,
            team=team,
            status=status,
        )

        PostLike.objects.create(
            post=post,
            user=user,
        )

        PostLike.objects.create(
            post=post,
            user=user2,
        )

        Post.objects.create(
            title='Deleted Post',
            content='Deleted Content',
            user=user,
            team=team,
            status=deleted_status,
        )

        hidden_post = Post.objects.create(
            title='Hidden Post',
            content='Hidden Content',
            user=user,
            team=team,
            status=hidden_status,
        )

        PostLike.objects.create(
            post=hidden_post,
            user=user,
        )

        PostLike.objects.create(
            post=hidden_post,
            user=user2,
        )

        request = factory.get(f'/api/teams/{team.id}/posts/popular/')
        response = view(request, pk=team.id)

        data = response.data
        self.assertEqual(response.status_code, 200)
        self.assertTrue('results' in data)
        self.assertTrue('count' in data)
        self.assertTrue('next' in data)
        self.assertTrue('previous' in data)

        self.assertEqual(data['count'], 10)
        self.assertEqual(len(data['results']), 10)
        self.assertTrue(data['next'] is None)
        self.assertTrue(data['previous'] is None)

        for post in data['results']:
            self.assertTrue('id' in post)
            self.assertTrue('title' in post)
            self.assertFalse('content' in post)
            self.assertFalse('liked' in post)
            self.assertTrue('likes_count' in post)
            self.assertTrue('comments_count' in post)
            self.assertTrue('team_data' in post)
            self.assertTrue('user_data' in post)
            self.assertTrue('status_data' in post)
            self.assertTrue('created_at' in post)
            self.assertTrue('updated_at' in post)
            
            self.assertEqual(post['status_data']['name'], 'created')

    def test_get_team_posts(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        user2 = User.objects.filter(username='testuser2').first()
        if not user2:
            self.fail("User not found")

        team = Team.objects.all().first()

        factory = APIRequestFactory()
        request = factory.get(f'/api/teams/{team.id}/posts/')
        view = TeamViewSet.as_view({'get': 'get_team_posts'})

        response = view(request, pk=team.id)
        data = response.data

        self.assertEqual(response.status_code, 200)
        self.assertTrue('results' in data)
        self.assertTrue('count' in data)
        self.assertTrue('next' in data)
        self.assertTrue('previous' in data)

        self.assertEqual(data['count'], 0)
        self.assertEqual(data['results'], [])
        self.assertIsNone(data['next'])
        self.assertIsNone(data['previous'])

        # Insert some posts
        status = PostStatus.objects.filter(name='created').first()
        deleted_status = PostStatus.objects.filter(name='deleted').first()
        hidden_status = PostStatus.objects.filter(name='hidden').first()

        for i in range(10):
            Post.objects.create(
                title='Fake Post',
                content='Fake Content',
                user=user,
                team=team,
                status=status,
            )

        Post.objects.create(
            title='Hidden Post',
            content='Hidden Content',
            user=user,
            team=team,
            status=hidden_status,
        )

        Post.objects.create(
            title='Deleted Post',
            content='Deleted Content',
            user=user,
            team=team,
            status=deleted_status,
        )

        # unauthenticated user
        request = factory.get(f'/api/teams/{team.id}/posts/')
        response = view(request, pk=team.id)

        data = response.data
        self.assertEqual(response.status_code, 200)
        self.assertTrue('results' in data)
        self.assertTrue('count' in data)
        self.assertTrue('next' in data)
        self.assertTrue('previous' in data)

        self.assertEqual(data['count'], 10)
        self.assertEqual(len(data['results']), 10)
        self.assertTrue(data['next'] is None)
        self.assertTrue(data['previous'] is None)

        for post in data['results']:
            self.assertTrue('id' in post)
            self.assertTrue('title' in post)
            self.assertFalse('content' in post)
            self.assertFalse('liked' in post)
            self.assertTrue('likes_count' in post)
            self.assertTrue('comments_count' in post)
            self.assertTrue('team_data' in post)
            self.assertTrue('user_data' in post)
            self.assertTrue('status_data' in post)
            self.assertTrue('created_at' in post)
            self.assertTrue('updated_at' in post)
            self.assertEqual(post['status_data']['name'], 'created')

        # authenticated user
        force_authenticate(request, user=user)
        response = view(request, pk=team.id)

        data = response.data
        self.assertEqual(response.status_code, 200)
        self.assertTrue('results' in data)
        self.assertTrue('count' in data)
        self.assertTrue('next' in data)
        self.assertTrue('previous' in data)

        self.assertEqual(data['count'], 10)
        self.assertEqual(len(data['results']), 10)
        self.assertTrue(data['next'] is None)
        self.assertTrue(data['previous'] is None)

        for post in data['results']:
            self.assertTrue('id' in post)
            self.assertTrue('title' in post)
            self.assertFalse('content' in post)
            self.assertTrue('liked' in post)
            self.assertTrue('likes_count' in post)
            self.assertTrue('comments_count' in post)
            self.assertTrue('team_data' in post)
            self.assertTrue('user_data' in post)
            self.assertTrue('status_data' in post)
            self.assertTrue('created_at' in post)
            self.assertTrue('updated_at' in post)
            self.assertEqual(post['status_data']['name'], 'created')         

    def test_get_team_post(self):
        user = User.objects.filter(username='testuser').first()
        if not user:
            self.fail("User not found")

        user2 = User.objects.filter(username='testuser2').first()
        if not user2:
            self.fail("User not found")

        team = Team.objects.all().first()

        factory = APIRequestFactory()
        fake_post_id = '00000000-0000-0000-0000-000000000000'
        request = factory.get(f'/api/teams/{team.id}/posts/{fake_post_id}/')

        view = TeamViewSet.as_view({'get': 'get_team_post'})
        response = view(request, pk=team.id, post_id=fake_post_id)

        data = response.data
        self.assertEqual(response.status_code, 404)

        # Insert some posts
        status = PostStatus.objects.filter(name='created').first()
        deleted_status = PostStatus.objects.filter(name='deleted').first()
        hidden_status = PostStatus.objects.filter(name='hidden').first()

        post = Post.objects.create(
            title='Fake Post',
            content='Fake Content',
            user=user,
            team=team,
            status=status,
        )

        request = factory.get(f'/api/teams/{team.id}/posts/{str(post.id)}/')
        response = view(request, pk=team.id, post_id=str(post.id))

        data = response.data
        self.assertEqual(response.status_code, 200)
        self.assertTrue('id' in data)
        self.assertTrue('title' in data)
        self.assertTrue('content' in data)
        self.assertFalse('liked' in data)
        self.assertTrue('likes_count' in data)
        self.assertTrue('comments_count' in data)
        self.assertTrue('team_data' in data)
        self.assertTrue('user_data' in data)
        self.assertTrue('status_data' in data)
        self.assertTrue('created_at' in data)
        self.assertTrue('updated_at' in data)

        self.assertEqual(data['id'], str(post.id))
        self.assertEqual(data['title'], post.title)
        self.assertEqual(data['content'], post.content)
        self.assertEqual(data['likes_count'], 0)
        self.assertEqual(data['comments_count'], 0)
        self.assertEqual(data['team_data']['id'], team.id)
        self.assertEqual(data['user_data']['id'], user.id)
        self.assertEqual(data['status_data']['id'], status.id)
        self.assertEqual(data['created_at'], post.created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
        self.assertEqual(data['updated_at'], post.updated_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))

        force_authenticate(request, user=user)
        response = view(request, pk=team.id, post_id=str(post.id))

        data = response.data
        self.assertEqual(response.status_code, 200)
        self.assertTrue('id' in data)
        self.assertTrue('title' in data)
        self.assertTrue('content' in data)
        self.assertTrue('liked' in data)
        self.assertTrue('likes_count' in data)
        self.assertTrue('comments_count' in data)
        self.assertTrue('team_data' in data)
        self.assertTrue('user_data' in data)
        self.assertTrue('status_data' in data)
        self.assertTrue('created_at' in data)
        self.assertTrue('updated_at' in data)

        self.assertEqual(data['id'], str(post.id))
        self.assertEqual(data['title'], post.title)
        self.assertEqual(data['content'], post.content)
        self.assertEqual(data['likes_count'], 0)
        self.assertEqual(data['comments_count'], 0)
        self.assertEqual(data['team_data']['id'], team.id)
        self.assertEqual(data['user_data']['id'], user.id)
        self.assertEqual(data['status_data']['id'], status.id)
        self.assertEqual(data['created_at'], post.created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
        self.assertEqual(data['updated_at'], post.updated_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
        self.assertFalse(data['liked'])

        PostLike.objects.create(
            post=post,
            user=user,
        )

        request = factory.get(f'/api/teams/{team.id}/posts/{str(post.id)}/')
        force_authenticate(request, user=user)

        response = view(request, pk=team.id, post_id=str(post.id))
        data = response.data

        self.assertEqual(data['likes_count'], 1)
        self.assertTrue(data['liked'])

        # Test hidden post
        hidden_post = Post.objects.create(
            title='Hidden Post',
            content='Hidden Content',
            user=user,
            team=team,
            status=hidden_status,
        )

        request = factory.get(f'/api/teams/{team.id}/posts/{str(hidden_post.id)}/')
        response = view(request, pk=team.id, post_id=str(hidden_post.id))

        self.assertEqual(response.status_code, 404)

        force_authenticate(request, user=user)
        response = view(request, pk=team.id, post_id=str(hidden_post.id))
        data = response.data

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['id'], str(hidden_post.id))
        self.assertEqual(data['title'], hidden_post.title)
        self.assertEqual(data['content'], hidden_post.content)
        self.assertEqual(data['likes_count'], 0)
        self.assertEqual(data['comments_count'], 0)
        self.assertEqual(data['team_data']['id'], team.id)
        self.assertEqual(data['user_data']['id'], user.id)
        self.assertEqual(data['status_data']['id'], hidden_status.id)
        self.assertEqual(data['created_at'], hidden_post.created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
        self.assertEqual(data['updated_at'], hidden_post.updated_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))

        request = factory.get(f'/api/teams/{team.id}/posts/{str(hidden_post.id)}/')
        force_authenticate(request, user=user2)
        response = view(request, pk=team.id, post_id=str(hidden_post.id))

        self.assertEqual(response.status_code, 404)
        
        # Test deleted post
        deleted_post = Post.objects.create(
            title='Deleted Post',
            content='Deleted Content',
            user=user,
            team=team,
            status=deleted_status,
        )

        request = factory.get(f'/api/teams/{team.id}/posts/{str(deleted_post.id)}/')
        response = view(request, pk=team.id, post_id=str(deleted_post.id))

        self.assertEqual(response.status_code, 404)