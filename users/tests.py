from rest_framework.test import APITestCase, APIRequestFactory, APIClient, force_authenticate

from teams.models import Language, Team, TeamLike, TeamName
from users.models import Role, User
from users.views import UserViewSet


# Create your tests here.
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