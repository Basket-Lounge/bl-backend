from unittest.mock import patch
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate

from management.models import Inquiry, InquiryMessage, InquiryModerator, InquiryModeratorMessage, InquiryType
from management.views import InquiryModeratorViewSet
from users.models import Role, User


class InquiryModeratorViewSetTestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create(
            username='test_user',
            email='testuser1@email.com'
        )
        self.user1.set_password('testpassword')
        self.user1.save()

        self.admin1 = User.objects.create(
            username='testadmin', 
            email="admin@admin.com", 
            role=Role.get_admin_role()
        )
        self.admin1.set_password('admin')
        self.admin1.save()

        self.admin2 = User.objects.create(
            username='testadmin2', 
            email="admin1@admin.com",
            role=Role.get_admin_role()
        )
        self.admin2.set_password('admin')
        self.admin2.save()


    def test_retrieve(self):
        # Create an inquiry
        inquiry_type = InquiryType.objects.all().first()
        inquiry = Inquiry.objects.create(
            user=self.user1,
            inquiry_type=inquiry_type,
            title='test title',
        )

        factory = APIRequestFactory()
        request = factory.get(f'/api/admin/inquiries/{str(inquiry.id)}')
        force_authenticate(request, user=self.admin1)
        view = InquiryModeratorViewSet.as_view({'get': 'retrieve'})
        response = view(request, pk=inquiry.id)
        self.assertEqual(response.status_code, 200)

        data = response.data
        self.assertEqual(data['id'], str(inquiry.id))
        self.assertTrue('user_data' in data)
        self.assertTrue('inquiry_type_data' in data)
        self.assertTrue('moderators' in data)
        self.assertTrue('solved' in data)
        self.assertTrue('last_read_at' in data)
        self.assertTrue('title' in data)
        self.assertTrue('created_at' in data)
        self.assertTrue('updated_at' in data)
        self.assertEqual(data['user_data']['id'], self.user1.id)
        self.assertEqual(data['user_data']['username'], self.user1.username)
        self.assertEqual(data['inquiry_type_data']['id'], inquiry_type.id)
        self.assertEqual(data['inquiry_type_data']['name'], inquiry_type.name)
        self.assertEqual(data['inquiry_type_data']['description'], inquiry_type.description)
        self.assertTrue('display_names' in data['inquiry_type_data'])
        self.assertEqual(data['moderators'], [])
        self.assertEqual(data['solved'], False)
        self.assertEqual(data['title'], inquiry.title)
        self.assertEqual(data['last_read_at'], inquiry.last_read_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
        self.assertEqual(data['created_at'], inquiry.created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
        self.assertEqual(data['updated_at'], inquiry.updated_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))

        # Assign a moderator to the inquiry
        inquiry_moderator = InquiryModerator.objects.create(
            inquiry=inquiry,
            moderator=self.admin1,
        )

        request = factory.get(f'/api/admin/inquiries/{str(inquiry.id)}')
        force_authenticate(request, user=self.admin1)
        view = InquiryModeratorViewSet.as_view({'get': 'retrieve'})
        response = view(request, pk=inquiry.id)

        data = response.data
        self.assertEqual(len(data['moderators']), 1)
        self.assertEqual(data['moderators'][0]['moderator_data']['id'], self.admin1.id)
        self.assertEqual(data['moderators'][0]['moderator_data']['username'], self.admin1.username)
        self.assertEqual(data['moderators'][0]['last_read_at'], inquiry_moderator.last_read_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
        self.assertEqual(data['moderators'][0]['in_charge'], inquiry_moderator.in_charge)

    def test_get_inquiry_messages(self):
        # Create an inquiry
        inquiry_type = InquiryType.objects.all().first()
        inquiry = Inquiry.objects.create(
            user=self.user1,    
            inquiry_type=inquiry_type,
            title='test title',
        )
        inquiry_moderator = InquiryModerator.objects.create(
            inquiry=inquiry,
            moderator=self.admin1,
        )

        # Create 5 messages
        for i in range(5):
            InquiryMessage.objects.create(
                inquiry=inquiry,
                message=f'test message {i}',
            )

        # Create 5 messages for the moderator
        for i in range(5):
            InquiryModeratorMessage.objects.create(
                inquiry_moderator=inquiry_moderator,
                message=f'test message {i}',
            )

        factory = APIRequestFactory()
        request = factory.get(f'/api/admin/inquiries/{str(inquiry.id)}/messages/')
        view = InquiryModeratorViewSet.as_view({'get': 'get_inquiry_messages'})
        response = view(request, pk=inquiry.id)
        self.assertEqual(response.status_code, 401)

        force_authenticate(request, user=self.admin1)
        response = view(request, pk=inquiry.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('next' in response.data)
        self.assertTrue('results' in response.data)
        self.assertEqual(response.data['next'], None)
        self.assertEqual(len(response.data['results']), 10)

        data = response.data['results']
        for i in range(5):
            self.assertEqual(data[i]['message'], f'test message {i}')
            self.assertEqual(data[i]['user_type'], 'User')

        for i in range(5):
            self.assertEqual(data[i + 5]['message'], f'test message {i}')
            self.assertEqual(data[i + 5]['user_type'], 'Moderator')

        # Create 30 more messages
        for i in range(30):
            InquiryMessage.objects.create(
                inquiry=inquiry,
                message=f'new test message {i}',
            )

        request = factory.get(f'/api/admin/inquiries/{str(inquiry.id)}/messages/')
        force_authenticate(request, user=self.admin1)
        response = view(request, pk=inquiry.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('next' in response.data)
        self.assertTrue('results' in response.data)

        data = response.data['results']
        self.assertIsNotNone(response.data['next'])
        self.assertEqual(len(data), 25)

        for i in range(5, 30):
            self.assertEqual(data[i - 5]['message'], f'new test message {i}')
            self.assertEqual(data[i - 5]['user_type'], 'User')
        
        next_url = response.data['next']
        request = factory.get(next_url)
        force_authenticate(request, user=self.admin1)
        response = view(request, pk=inquiry.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('next' in response.data)
        self.assertTrue('results' in response.data)

        data = response.data['results']
        self.assertIsNone(response.data['next'])
        self.assertEqual(len(data), 15)

        for i in range(5):
            self.assertEqual(data[i]['message'], f'test message {i}')
            self.assertEqual(data[i]['user_type'], 'User')

        for i in range(5):
            self.assertEqual(data[i + 5]['message'], f'test message {i}')
            self.assertEqual(data[i + 5]['user_type'], 'Moderator')

        for i in range(5):
            self.assertEqual(data[i + 10]['message'], f'new test message {i}')
            self.assertEqual(data[i + 10]['user_type'], 'User')


    def test_list(self):
        # Create 5 inquiries
        inquiry_type = InquiryType.objects.all().first()
        for i in range(5):
            Inquiry.objects.create(
                user=self.user1,
                inquiry_type=inquiry_type,
                title=f'test title {i}',
            )

        factory = APIRequestFactory()
        request = factory.get('/api/admin/inquiries/')
        view = InquiryModeratorViewSet.as_view({'get': 'list'})
        response = view(request)
        self.assertEqual(response.status_code, 401)

        force_authenticate(request, user=self.admin1)
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('count' in response.data)
        self.assertTrue('next' in response.data)
        self.assertTrue('previous' in response.data)
        self.assertTrue('current_page' in response.data)
        self.assertTrue('first_page' in response.data)
        self.assertTrue('last_page' in response.data)
        self.assertTrue('results' in response.data)
        self.assertEqual(response.data['count'], 5)
        self.assertEqual(response.data['current_page'], 1)
        self.assertEqual(response.data['first_page'], 1)
        self.assertEqual(response.data['last_page'], 1)
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])

        data = response.data['results']
        self.assertEqual(len(data), 5)
        index_set = set()
        real_index = 0
        for i in range(4, -1, -1):
            self.assertTrue('user_data' in data[real_index])
            self.assertTrue('inquiry_type_data' in data[real_index])
            self.assertTrue('moderators' in data[real_index])
            self.assertTrue('last_message' in data[real_index])
            self.assertTrue('solved' in data[real_index])
            self.assertTrue('last_read_at' in data[real_index])
            self.assertTrue('title' in data[real_index])
            self.assertTrue('created_at' in data[real_index])
            self.assertTrue('updated_at' in data[real_index])

            self.assertEqual(data[real_index]['title'], f'test title {i}')
            index_set.add(data[real_index]['title'])
            self.assertEqual(data[real_index]['user_data']['id'], self.user1.id)
            self.assertEqual(data[real_index]['user_data']['username'], self.user1.username)
            self.assertEqual(data[real_index]['inquiry_type_data']['id'], inquiry_type.id)
            self.assertEqual(data[real_index]['inquiry_type_data']['name'], inquiry_type.name)
            self.assertEqual(data[real_index]['inquiry_type_data']['description'], inquiry_type.description)
            self.assertTrue('display_names' in data[real_index]['inquiry_type_data'])
            self.assertEqual(data[real_index]['moderators'], [])

            real_index += 1

        self.assertEqual(len(index_set), 5)

    
    @patch('management.tasks.broadcast_inquiry_updates_to_all_parties.delay')
    def test_partial_update(self, mocked):
        # Create an inquiry
        inquiry_type = InquiryType.objects.all().first()
        inquiry = Inquiry.objects.create(
            user=self.user1,
            inquiry_type=inquiry_type,
            title='test title',
        )

        factory = APIRequestFactory()
        request = factory.patch(
            f'/api/admin/inquiries/{str(inquiry.id)}',
            data={'solved': True},
            format='json'
        )
        view = InquiryModeratorViewSet.as_view({'patch': 'partial_update'})
        response = view(request, pk=inquiry.id)
        self.assertEqual(response.status_code, 401)

        # Try to mark the inquiry as solved as a moderator that is not assigned to the inquiry
        request = factory.patch(f'/api/admin/inquiries/{str(inquiry.id)}', {'solved': False})
        force_authenticate(request, user=self.admin1)
        view = InquiryModeratorViewSet.as_view({'patch': 'partial_update'})
        response = view(request, pk=inquiry.id)
        self.assertEqual(response.status_code, 404)

        # Assign a moderator to the inquiry
        InquiryModerator.objects.create(
            inquiry=inquiry,
            moderator=self.admin1,
        )

        # Mark the inquiry as solved
        request = factory.patch(f'/api/admin/inquiries/{str(inquiry.id)}', {'solved': True})
        force_authenticate(request, user=self.admin1)
        view = InquiryModeratorViewSet.as_view({'patch': 'partial_update'})
        response = view(request, pk=inquiry.id)
        self.assertEqual(response.status_code, 200)

        inquiry.refresh_from_db()
        self.assertTrue(inquiry.solved)

        # Mark the inquiry as unsolved
        request = factory.patch(f'/api/admin/inquiries/{str(inquiry.id)}', {'solved': False})
        force_authenticate(request, user=self.admin1)
        response = view(request, pk=inquiry.id)
        self.assertEqual(response.status_code, 200)

        inquiry.refresh_from_db()
        self.assertFalse(inquiry.solved)

        # Change the type of the inquiry
        inquiry_type2 = InquiryType.objects.all().last()
        request = factory.patch(f'/api/admin/inquiries/{str(inquiry.id)}', {'inquiry_type': inquiry_type2.id})
        force_authenticate(request, user=self.admin1)
        response = view(request, pk=inquiry.id)
        self.assertEqual(response.status_code, 200)

        inquiry.refresh_from_db()
        self.assertEqual(inquiry.inquiry_type, inquiry_type2)

        # Change the title of the inquiry
        request = factory.patch(f'/api/admin/inquiries/{str(inquiry.id)}', {'title': 'brand new title'})
        force_authenticate(request, user=self.admin1)
        response = view(request, pk=inquiry.id)
        self.assertEqual(response.status_code, 200)

        inquiry.refresh_from_db()
        self.assertEqual(inquiry.title, 'brand new title')

    @patch('management.tasks.broadcast_inquiry_updates_for_new_message_to_all_parties.delay')
    def test_send_message(self, mocked):
        # Create an inquiry
        inquiry_type = InquiryType.objects.all().first()
        inquiry = Inquiry.objects.create(
            user=self.user1,
            inquiry_type=inquiry_type,
            title='test title',
        )

        factory = APIRequestFactory()
        request = factory.post(
            f'/api/admin/inquiries/{str(inquiry.id)}/messages/',
            data={'message': 'test message'},
            format='json'
        )
        view = InquiryModeratorViewSet.as_view({'post': 'send_message'})
        response = view(request, pk=inquiry.id)
        self.assertEqual(response.status_code, 401)

        # Try to send a message as a moderator that is not assigned to the inquiry
        request = factory.post(
            f'/api/admin/inquiries/{str(inquiry.id)}/messages/',
            data={'message': 'test message'},
            format='json'
        )
        force_authenticate(request, user=self.admin1)
        view = InquiryModeratorViewSet.as_view({'post': 'send_message'})
        response = view(request, pk=inquiry.id)
        self.assertEqual(response.status_code, 404)

        # Assign a moderator to the inquiry
        InquiryModerator.objects.create(
            inquiry=inquiry,
            moderator=self.admin1,
        )

        # Send a message
        request = factory.post(
            f'/api/admin/inquiries/{str(inquiry.id)}/messages/',
            data={'message': 'test message'},
            format='json'
        )
        force_authenticate(request, user=self.admin1)
        response = view(request, pk=inquiry.id)
        self.assertEqual(response.status_code, 201)

        inquiry_message = InquiryModeratorMessage.objects.last()
        if not inquiry_message:
            self.fail('No message was created')
        self.assertEqual(inquiry_message.message, 'test message')

        # Send a message to the solved inquiry
        inquiry.solved = True
        inquiry.save()

        request = factory.post(
            f'/api/admin/inquiries/{str(inquiry.id)}/messages/',
            data={'message': 'test message'},
            format='json'
        )
        force_authenticate(request, user=self.admin1)
        response = view(request, pk=inquiry.id)
        self.assertEqual(response.status_code, 404)

    @patch('management.tasks.broadcast_inquiry_updates_to_all_parties.delay')
    def test_mark_inquiry_as_read(self, mocked):
        # Create an inquiry
        inquiry_type = InquiryType.objects.all().first()
        inquiry = Inquiry.objects.create(
            user=self.user1,
            inquiry_type=inquiry_type,
            title='test title',
        )

        factory = APIRequestFactory()
        request = factory.patch(f'/api/admin/inquiries/{str(inquiry.id)}/mark-as-read/')
        view = InquiryModeratorViewSet.as_view({'patch': 'mark_inquiry_as_read'})
        response = view(request, pk=inquiry.id)
        self.assertEqual(response.status_code, 401)

        # Try to mark the inquiry as read as a moderator that is not assigned to the inquiry
        request = factory.patch(f'/api/admin/inquiries/{str(inquiry.id)}/mark-as-read/')
        force_authenticate(request, user=self.admin1)
        response = view(request, pk=inquiry.id)
        self.assertEqual(response.status_code, 404)

        # Assign a moderator to the inquiry
        moderator = InquiryModerator.objects.create(
            inquiry=inquiry,
            moderator=self.admin1,
        )
        old_last_read_at = moderator.last_read_at

        # Mark the inquiry as read
        request = factory.patch(f'/api/admin/inquiries/{str(inquiry.id)}/mark-as-read/')
        force_authenticate(request, user=self.admin1)
        response = view(request, pk=inquiry.id)
        self.assertEqual(response.status_code, 200)

        moderator.refresh_from_db()
        self.assertTrue(moderator.last_read_at > old_last_read_at)

    def test_list_unassigned_inquiries(self):
        # Create 5 inquiries
        inquiry_type = InquiryType.objects.all().first()
        for i in range(5):
            Inquiry.objects.create(
                user=self.user1,
                inquiry_type=inquiry_type,
                title=f'test title {i}',
            )

        factory = APIRequestFactory()
        request = factory.get('/api/admin/inquiries/unassigned/')
        view = InquiryModeratorViewSet.as_view({'get': 'list_unassigned_inquiries'})
        response = view(request)
        self.assertEqual(response.status_code, 401)

        force_authenticate(request, user=self.admin1)
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('count' in response.data)
        self.assertTrue('next' in response.data)
        self.assertTrue('previous' in response.data)
        self.assertTrue('current_page' in response.data)
        self.assertTrue('first_page' in response.data)
        self.assertTrue('last_page' in response.data)
        self.assertTrue('results' in response.data)
        self.assertEqual(response.data['count'], 5)
        self.assertEqual(response.data['current_page'], 1)
        self.assertEqual(response.data['first_page'], 1)
        self.assertEqual(response.data['last_page'], 1)
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])

        data = response.data['results']
        self.assertEqual(len(data), 5)
        real_index = 0
        for i in range(4, -1, -1):
            self.assertTrue('user_data' in data[real_index])
            self.assertTrue('inquiry_type_data' in data[real_index])
            self.assertTrue('moderators' in data[real_index])
            self.assertTrue('last_message' in data[real_index])
            self.assertTrue('solved' in data[real_index])
            self.assertTrue('last_read_at' in data[real_index])
            self.assertTrue('title' in data[real_index])
            self.assertTrue('created_at' in data[real_index])
            self.assertTrue('updated_at' in data[real_index])

            self.assertEqual(data[real_index]['title'], f'test title {i}')
            self.assertEqual(data[real_index]['user_data']['id'], self.user1.id)
            self.assertEqual(data[real_index]['user_data']['username'], self.user1.username)
            self.assertEqual(data[real_index]['moderators'], [])
            real_index += 1

        
        # Assign a moderator to the first inquiry
        inquiry = Inquiry.objects.get(title='test title 4')
        InquiryModerator.objects.create(
            inquiry=inquiry,
            moderator=self.admin1,
        )

        request = factory.get('/api/admin/inquiries/unassigned/')
        force_authenticate(request, user=self.admin1)
        response = view(request)

        data = response.data['results']
        self.assertEqual(len(data), 4)
        real_index = 0
        for i in range(3, -1, -1):
            self.assertTrue('user_data' in data[real_index])
            self.assertTrue('inquiry_type_data' in data[real_index])
            self.assertTrue('moderators' in data[real_index])
            self.assertTrue('last_message' in data[real_index])
            self.assertTrue('solved' in data[real_index])
            self.assertTrue('last_read_at' in data[real_index])
            self.assertTrue('title' in data[real_index])
            self.assertTrue('created_at' in data[real_index])
            self.assertTrue('updated_at' in data[real_index])

            self.assertEqual(data[real_index]['title'], f'test title {i}')
            self.assertEqual(data[real_index]['user_data']['id'], self.user1.id)
            self.assertEqual(data[real_index]['user_data']['username'], self.user1.username)
            self.assertEqual(data[real_index]['moderators'], [])
            real_index += 1

    def test_list_assigned_inquiries(self):
        # Create 5 inquiries
        inquiry_type = InquiryType.objects.all().first()
        for i in range(5):
            Inquiry.objects.create(
                user=self.user1,
                inquiry_type=inquiry_type,
                title=f'test title {i}',
            )

        factory = APIRequestFactory()
        request = factory.get('/api/admin/inquiries/assigned/')
        view = InquiryModeratorViewSet.as_view({'get': 'list_assigned_inquiries'})
        response = view(request)
        self.assertEqual(response.status_code, 401)

        force_authenticate(request, user=self.admin1)
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('count' in response.data)
        self.assertTrue('next' in response.data)
        self.assertTrue('previous' in response.data)
        self.assertTrue('current_page' in response.data)
        self.assertTrue('first_page' in response.data)
        self.assertTrue('last_page' in response.data)
        self.assertTrue('results' in response.data)

        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['current_page'], 1)
        self.assertEqual(response.data['first_page'], 1)
        self.assertEqual(response.data['last_page'], 1)
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(len(response.data['results']), 0)

        # Assign a moderator to the first inquiry
        inquiry = Inquiry.objects.get(title='test title 4')
        InquiryModerator.objects.create(
            inquiry=inquiry,
            moderator=self.admin1,
        )

        request = factory.get('/api/admin/inquiries/assigned/')
        force_authenticate(request, user=self.admin1)
        response = view(request)

        self.assertEqual(response.data['count'], 1)
        data = response.data['results']
        self.assertEqual(len(data), 1)

        # Assign a moderator to another inquiry
        inquiry = Inquiry.objects.get(title='test title 3')
        InquiryModerator.objects.create(
            inquiry=inquiry,
            moderator=self.admin1,
        )

        request = factory.get('/api/admin/inquiries/assigned/')
        force_authenticate(request, user=self.admin1)
        response = view(request)

        self.assertEqual(response.data['count'], 2)
        data = response.data['results']
        self.assertEqual(len(data), 2)

        for inquiry_item in data:
            self.assertTrue('user_data' in inquiry_item)
            self.assertTrue('inquiry_type_data' in inquiry_item)
            self.assertTrue('moderators' in inquiry_item)
            self.assertTrue('last_message' in inquiry_item)
            self.assertTrue('solved' in inquiry_item)
            self.assertTrue('last_read_at' in inquiry_item)
            self.assertTrue('title' in inquiry_item)
            self.assertTrue('created_at' in inquiry_item)
            self.assertTrue('updated_at' in inquiry_item)

            self.assertEqual(inquiry_item['user_data']['id'], self.user1.id)
            self.assertEqual(inquiry_item['user_data']['username'], self.user1.username)
            self.assertEqual(len(inquiry_item['moderators']), 1)
            self.assertTrue('moderator_data' in inquiry_item['moderators'][0])
            self.assertTrue('last_message' in inquiry_item['moderators'][0])
            self.assertTrue('in_charge' in inquiry_item['moderators'][0])
            self.assertEqual(inquiry_item['moderators'][0]['moderator_data']['id'], self.admin1.id)
            self.assertEqual(inquiry_item['moderators'][0]['moderator_data']['username'], self.admin1.username)
            self.assertEqual(inquiry_item['moderators'][0]['last_message'], None)
            self.assertEqual(inquiry_item['moderators'][0]['in_charge'], True)
            self.assertEqual(inquiry_item['solved'], False)
            self.assertEqual(inquiry_item['inquiry_type_data']['id'], inquiry_type.id)
            self.assertEqual(inquiry_item['inquiry_type_data']['name'], inquiry_type.name)
            self.assertEqual(inquiry_item['inquiry_type_data']['description'], inquiry_type.description)
            self.assertTrue('display_names' in inquiry_item['inquiry_type_data'])
            self.assertTrue(inquiry_item['title'] in ['test title 3', 'test title 4'])

    def test_list_solved_inquiries(self):
        # Create 5 inquiries
        inquiry_type = InquiryType.objects.all().first()
        for i in range(5):
            Inquiry.objects.create(
                user=self.user1,
                inquiry_type=inquiry_type,
                title=f'test title {i}',
            )

        factory = APIRequestFactory()
        request = factory.get('/api/admin/inquiries/solved/')
        view = InquiryModeratorViewSet.as_view({'get': 'list_solved_inquiries'})
        response = view(request)
        self.assertEqual(response.status_code, 401)

        force_authenticate(request, user=self.admin1)
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('count' in response.data)
        self.assertTrue('next' in response.data)
        self.assertTrue('previous' in response.data)
        self.assertTrue('current_page' in response.data)
        self.assertTrue('first_page' in response.data)
        self.assertTrue('last_page' in response.data)
        self.assertTrue('results' in response.data)

        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['current_page'], 1)
        self.assertEqual(response.data['first_page'], 1)
        self.assertEqual(response.data['last_page'], 1)
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(len(response.data['results']), 0)

        # Assign a moderator to the first inquiry
        inquiry = Inquiry.objects.get(title='test title 4')
        InquiryModerator.objects.create(
            inquiry=inquiry,
            moderator=self.admin1,
        )

        request = factory.get('/api/admin/inquiries/solved/')
        force_authenticate(request, user=self.admin1)
        response = view(request)

        self.assertEqual(response.data['count'], 0)
        data = response.data['results']
        self.assertEqual(len(data), 0)

        # Mark the inquiry as solved
        inquiry = Inquiry.objects.get(title='test title 3')
        inquiry.solved = True
        inquiry.save()

        request = factory.get('/api/admin/inquiries/solved/')
        force_authenticate(request, user=self.admin1)
        response = view(request)

        self.assertEqual(response.data['count'], 1)
        data = response.data['results']

        self.assertTrue('user_data' in data[0])
        self.assertTrue('inquiry_type_data' in data[0])
        self.assertTrue('moderators' in data[0])
        self.assertTrue('last_message' in data[0])
        self.assertTrue('solved' in data[0])
        self.assertTrue('last_read_at' in data[0])
        self.assertTrue('title' in data[0])
        self.assertTrue('created_at' in data[0])
        self.assertTrue('updated_at' in data[0])

        self.assertEqual(data[0]['user_data']['id'], self.user1.id)
        self.assertEqual(data[0]['user_data']['username'], self.user1.username)
        self.assertEqual(len(data[0]['moderators']), 0)
        self.assertEqual(data[0]['solved'], True)
        self.assertEqual(data[0]['inquiry_type_data']['id'], inquiry_type.id)
        self.assertEqual(data[0]['inquiry_type_data']['name'], inquiry_type.name)
        self.assertEqual(data[0]['inquiry_type_data']['description'], inquiry_type.description)
        self.assertTrue('display_names' in data[0]['inquiry_type_data'])
        self.assertEqual(data[0]['title'], 'test title 3')
        self.assertEqual(data[0]['created_at'], inquiry.created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
        self.assertEqual(data[0]['updated_at'], inquiry.updated_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))

    def test_list_unsolved_inquiries(self):
        # Create 5 inquiries
        inquiry_type = InquiryType.objects.all().first()
        for i in range(5):
            Inquiry.objects.create(
                user=self.user1,
                inquiry_type=inquiry_type,
                title=f'test title {i}',
            )

        factory = APIRequestFactory()
        request = factory.get('/api/admin/inquiries/unsolved/')
        view = InquiryModeratorViewSet.as_view({'get': 'list_unsolved_inquiries'})
        response = view(request)
        self.assertEqual(response.status_code, 401)

        force_authenticate(request, user=self.admin1)
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('count' in response.data)
        self.assertTrue('next' in response.data)
        self.assertTrue('previous' in response.data)
        self.assertTrue('current_page' in response.data)
        self.assertTrue('first_page' in response.data)
        self.assertTrue('last_page' in response.data)
        self.assertTrue('results' in response.data)

        self.assertEqual(response.data['count'], 5)
        self.assertEqual(response.data['current_page'], 1)
        self.assertEqual(response.data['first_page'], 1)
        self.assertEqual(response.data['last_page'], 1)
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(len(response.data['results']), 5)

        # Mark the inquiry as solved
        inquiry = Inquiry.objects.get(title='test title 3')
        inquiry.solved = True
        inquiry.save()

        request = factory.get('/api/admin/inquiries/unsolved/')
        force_authenticate(request, user=self.admin1)
        response = view(request)

        self.assertEqual(response.data['count'], 4)
        data = response.data['results']

        title_set = set()
        for inquiry_item in data:
            self.assertTrue('user_data' in inquiry_item)
            self.assertTrue('inquiry_type_data' in inquiry_item)
            self.assertTrue('moderators' in inquiry_item)
            self.assertTrue('last_message' in inquiry_item)
            self.assertTrue('solved' in inquiry_item)
            self.assertTrue('last_read_at' in inquiry_item)
            self.assertTrue('title' in inquiry_item)
            self.assertTrue('created_at' in inquiry_item)
            self.assertTrue('updated_at' in inquiry_item)

            self.assertEqual(inquiry_item['user_data']['id'], self.user1.id)
            self.assertEqual(inquiry_item['user_data']['username'], self.user1.username)
            self.assertEqual(len(inquiry_item['moderators']), 0)
            self.assertEqual(inquiry_item['solved'], False)
            self.assertEqual(inquiry_item['inquiry_type_data']['id'], inquiry_type.id)
            self.assertEqual(inquiry_item['inquiry_type_data']['name'], inquiry_type.name)
            self.assertEqual(inquiry_item['inquiry_type_data']['description'], inquiry_type.description)
            self.assertTrue('display_names' in inquiry_item['inquiry_type_data'])
            title_set.add(inquiry_item['title'])

        self.assertEqual(len(title_set), 4)

    def test_list_my_inquiries(self):
        # Create 5 inquiries
        inquiry_type = InquiryType.objects.all().first()
        for i in range(5):
            Inquiry.objects.create(
                user=self.user1,
                inquiry_type=inquiry_type,
                title=f'test title {i}',
            )

        factory = APIRequestFactory()
        request = factory.get('/api/admin/inquiries/mine/')
        view = InquiryModeratorViewSet.as_view({'get': 'list_my_inquiries'})
        response = view(request)
        self.assertEqual(response.status_code, 401)

        force_authenticate(request, user=self.admin1)
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('count' in response.data)
        self.assertTrue('next' in response.data)
        self.assertTrue('previous' in response.data)
        self.assertTrue('current_page' in response.data)
        self.assertTrue('first_page' in response.data)
        self.assertTrue('last_page' in response.data)
        self.assertTrue('results' in response.data)

        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['current_page'], 1)
        self.assertEqual(response.data['first_page'], 1)
        self.assertEqual(response.data['last_page'], 1)
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(len(response.data['results']), 0)

        # Assign a moderator to the first inquiry
        inquiry = Inquiry.objects.get(title='test title 4')
        InquiryModerator.objects.create(
            inquiry=inquiry,
            moderator=self.admin1,
        )

        request = factory.get('/api/admin/inquiries/mine/')
        force_authenticate(request, user=self.admin1)
        response = view(request)

        self.assertEqual(response.data['count'], 1)
        data = response.data['results']
        self.assertEqual(len(data), 1)

        inquiry_item = data[0]
        self.assertTrue('user_data' in inquiry_item)
        self.assertTrue('inquiry_type_data' in inquiry_item)
        self.assertTrue('moderators' in inquiry_item)
        self.assertTrue('last_message' in inquiry_item)
        self.assertTrue('solved' in inquiry_item)
        self.assertTrue('last_read_at' in inquiry_item)
        self.assertTrue('title' in inquiry_item)
        self.assertTrue('created_at' in inquiry_item)
        self.assertTrue('updated_at' in inquiry_item)
        self.assertFalse('unread_messages_count' in inquiry_item)

        self.assertEqual(inquiry_item['user_data']['id'], self.user1.id)
        self.assertEqual(inquiry_item['user_data']['username'], self.user1.username)
        self.assertEqual(len(inquiry_item['moderators']), 1)
        self.assertTrue('moderator_data' in inquiry_item['moderators'][0])
        self.assertTrue('last_message' in inquiry_item['moderators'][0])
        self.assertTrue('in_charge' in inquiry_item['moderators'][0])
        self.assertTrue('unread_messages_count' in inquiry_item['moderators'][0])
        self.assertTrue('unread_other_moderators_messages_count' in inquiry_item['moderators'][0])
        self.assertEqual(inquiry_item['moderators'][0]['moderator_data']['id'], self.admin1.id)
        self.assertEqual(inquiry_item['moderators'][0]['moderator_data']['username'], self.admin1.username)
        self.assertEqual(inquiry_item['moderators'][0]['last_message'], None)
        self.assertEqual(inquiry_item['moderators'][0]['in_charge'], True)
        self.assertEqual(inquiry_item['moderators'][0]['unread_messages_count'], 0)
        self.assertEqual(inquiry_item['moderators'][0]['unread_other_moderators_messages_count'], 0)
        self.assertEqual(inquiry_item['solved'], False)
        self.assertEqual(inquiry_item['inquiry_type_data']['id'], inquiry_type.id)
        self.assertEqual(inquiry_item['inquiry_type_data']['name'], inquiry_type.name)
        self.assertEqual(inquiry_item['inquiry_type_data']['description'], inquiry_type.description)
        self.assertTrue('display_names' in inquiry_item['inquiry_type_data'])
        self.assertEqual(inquiry_item['title'], 'test title 4')
        self.assertEqual(inquiry_item['created_at'], inquiry.created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
        self.assertEqual(inquiry_item['updated_at'], inquiry.updated_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))

        # Assign two moderators to the first inquiry
        second_mod = InquiryModerator.objects.create(
            inquiry=inquiry,
            moderator=self.admin2,
        )

        # Create an Inquiry Message
        InquiryMessage.objects.create(
            inquiry=inquiry,
            message='test message',
        )

        # Create 6 messages for the first inquiry
        for i in range(6):
            InquiryModeratorMessage.objects.create(
                inquiry_moderator=second_mod,
                message=f'test message {i}',
            )

        request = factory.get('/api/admin/inquiries/mine/')
        force_authenticate(request, user=self.admin1)
        response = view(request)

        self.assertEqual(response.data['count'], 1)
        data = response.data['results']
        self.assertEqual(len(data), 1)

        inquiry_item = data[0]
        self.assertTrue('user_data' in inquiry_item)
        self.assertTrue('inquiry_type_data' in inquiry_item)
        self.assertTrue('moderators' in inquiry_item)
        self.assertTrue('last_message' in inquiry_item)
        self.assertTrue('solved' in inquiry_item)
        self.assertTrue('last_read_at' in inquiry_item)
        self.assertTrue('title' in inquiry_item)
        self.assertTrue('created_at' in inquiry_item)
        self.assertTrue('updated_at' in inquiry_item)

        self.assertEqual(inquiry_item['user_data']['id'], self.user1.id)
        self.assertEqual(inquiry_item['user_data']['username'], self.user1.username)
        self.assertEqual(len(inquiry_item['moderators']), 2)

        self.assertTrue('moderator_data' in inquiry_item['moderators'][0])
        self.assertTrue('last_message' in inquiry_item['moderators'][0])
        self.assertTrue('in_charge' in inquiry_item['moderators'][0])
        self.assertTrue('unread_messages_count' in inquiry_item['moderators'][0])
        self.assertTrue('unread_other_moderators_messages_count' in inquiry_item['moderators'][0])

        self.assertTrue('moderator_data' in inquiry_item['moderators'][1])
        self.assertTrue('last_message' in inquiry_item['moderators'][1])
        self.assertTrue('in_charge' in inquiry_item['moderators'][1])
        self.assertTrue('unread_messages_count' in inquiry_item['moderators'][1])
        self.assertTrue('unread_other_moderators_messages_count' in inquiry_item['moderators'][1])

        for mod in inquiry_item['moderators']:
            self.assertTrue('moderator_data' in mod)
            self.assertTrue('last_message' in mod)
            self.assertTrue('in_charge' in mod)
            self.assertTrue('unread_messages_count' in mod)
            self.assertTrue('unread_other_moderators_messages_count' in mod)

            self.assertTrue('id' in mod['moderator_data'])
            self.assertTrue('username' in mod['moderator_data'])

            self.assertEqual(mod['in_charge'], True)
            self.assertEqual(mod['unread_messages_count'], 1)

            if mod['moderator_data']['id'] == self.admin2.id:
                self.assertTrue('message' in mod['last_message'])
                self.assertTrue('created_at' in mod['last_message'])
                self.assertEqual(mod['last_message']['message'], 'test message 5')
                self.assertEqual(mod['unread_other_moderators_messages_count'], 0)
            else:
                self.assertEqual(mod['moderator_data']['id'], self.admin1.id)
                self.assertEqual(mod['last_message'], None)
                self.assertEqual(mod['unread_other_moderators_messages_count'], 6)