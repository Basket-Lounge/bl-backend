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