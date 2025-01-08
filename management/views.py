from rest_framework import viewsets
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework.permissions import AllowAny
from rest_framework.decorators import action

from api.paginators import CustomPageNumberPagination
from management.serializers import (
    InquiryCreateSerializer, 
)

from management.services.models_services import (
    UserManagementService,
    PostManagementService,
    InquiryService,
    InquiryModeratorService,
    ReportService,
    filter_and_fetch_inquiries_in_desc_order_based_on_updated_at,
    filter_and_fetch_inquiry
)
from management.services.serializers_services import (
    PostManagementSerializerService,
    UserManagementSerializerService,
    InquirySerializerService,
    ReportSerializerService,
    send_inquiry_notification_to_all_channels_for_moderators,
    send_inquiry_notification_to_specific_moderator,
    send_inquiry_notification_to_user,
    send_new_moderator_to_live_chat,
    send_partially_updated_inquiry_to_live_chat,
    send_unassigned_inquiry_to_live_chat,
    serialize_inquiries_for_list,
    serialize_report,
    serialize_reports
)

from management.tasks import broadcast_inquiry_updates_to_all_parties
from teams.models import  PostComment
from teams.services import PostSerializerService, PostService, TeamSerializerService, TeamService
from users.authentication import CookieJWTAccessAuthentication, CookieJWTAdminAccessAuthentication
from users.models import Role, User
from users.serializers import RoleSerializer
from users.services import PostCommentSerializerService, UserChatSerializerService
from users.utils import generate_websocket_subscription_token


class JWTAdminSubscriptionViewSet(viewsets.ViewSet):
    authentication_classes = [CookieJWTAdminAccessAuthentication]
    permission_classes = [IsAuthenticated]

    @action(
        detail=False,
        methods=['get'],
        url_path=r'inquiry-updates'
    )
    def get_subscription_token_for_moderator_inquiry_updates(self, request):
        channel_name = f'moderators/inquiries/all/updates'
        token = generate_websocket_subscription_token(request.user.id, channel_name)
        return Response({'token': str(token)})

    @action(
        detail=False,
        methods=['get'],
        url_path=r'inquiry-updates/unassigned'
    )
    def get_subscription_token_for_unassigned_inquiry_updates(self, request):
        channel_name = f'moderators/inquiries/unassigned/updates'
        token = generate_websocket_subscription_token(request.user.id, channel_name)
        return Response({'token': str(token)})
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'inquiry-updates/assigned'
    )
    def get_subscription_token_for_assigned_inquiry_updates(self, request):
        channel_name = f'moderators/inquiries/assigned/updates'
        token = generate_websocket_subscription_token(request.user.id, channel_name)
        return Response({'token': str(token)})
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'inquiry-updates/solved'
    )
    def get_subscription_token_for_solved_inquiry_updates(self, request):
        channel_name = f'moderators/inquiries/solved/updates'
        token = generate_websocket_subscription_token(request.user.id, channel_name)
        return Response({'token': str(token)})
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'inquiry-updates/unsolved'
    )
    def get_subscription_token_for_unsolved_inquiry_updates(self, request):
        channel_name = f'moderators/inquiries/unsolved/updates'
        token = generate_websocket_subscription_token(request.user.id, channel_name)
        return Response({'token': str(token)})
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'inquiry-updates/mine'
    )
    def get_subscription_token_for_my_inquiry_updates(self, request):
        channel_name = f'moderators/{request.user.id}/inquiries/updates'
        token = generate_websocket_subscription_token(request.user.id, channel_name)
        return Response({'token': str(token)})
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'inquiries/(?P<inquiry_id>[0-9a-zA-Z-]+)'
    )
    def get_subscription_token_for_inquiry(self, request, inquiry_id=None):
        channel_name = f'users/inquiries/{inquiry_id}'
        token = generate_websocket_subscription_token(request.user.id, channel_name)
        return Response({'token': str(token)})


class InquiryViewSet(viewsets.ViewSet):
    authentication_classes = [CookieJWTAccessAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request):
        user = request.user

        serializer = InquiryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user)

        return Response(status=HTTP_201_CREATED)
    
    def retrieve(self, request, pk=None):
        inquiry = InquiryService.get_inquiry_by_user_id_and_id(request.user.id, pk)
        if not inquiry:
            return Response(status=HTTP_404_NOT_FOUND)

        serializer = InquirySerializerService.serialize_inquiry(inquiry)
        return Response(serializer.data)
    
    @method_decorator(cache_page(60 * 60 * 24))
    @action(
        detail=False,
        methods=['get'],
        url_path=r'types',
        permission_classes=[AllowAny]
    )
    def get_inquiry_types(self, request):
        types = InquiryService.get_all_inquiry_types()
        serializer = InquirySerializerService.serialize_inquiry_types(types)
        return Response(serializer.data)
    

class InquiryModeratorViewSet(viewsets.ViewSet):
    authentication_classes = [CookieJWTAdminAccessAuthentication]
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, pk=None):
        inquiry = InquiryService.get_inquiry_by_id(pk)
        if not inquiry:
            return Response(status=HTTP_404_NOT_FOUND)

        serializer = InquirySerializerService.serialize_inquiry(inquiry)
        return Response(serializer.data)
    
    def list(self, request):
        inquiries = InquiryModeratorService.get_inquiries_based_on_recent_updated_at(request)

        pagination = CustomPageNumberPagination()
        inquiries = pagination.paginate_queryset(inquiries, request)

        serializer = InquirySerializerService.serialize_inquiries(inquiries)
        return pagination.get_paginated_response(serializer.data)
    
    def partial_update(self, request, pk=None):
        updated, error, status = InquiryModeratorService.update_inquiry(request, pk)
        if error:
            return Response(status=status, data=error)

        inquiry = InquiryService.get_inquiry_without_messages(pk)
        notification_inquiry = filter_and_fetch_inquiry(id=pk)

        send_partially_updated_inquiry_to_live_chat(inquiry)
        send_inquiry_notification_to_user(
            notification_inquiry,
            inquiry.user.id,
            inquiry.last_read_at
        )
        send_inquiry_notification_to_all_channels_for_moderators(notification_inquiry)

        for moderator in inquiry.inquirymoderator_set.all():
            send_inquiry_notification_to_specific_moderator(
                notification_inquiry,
                moderator.moderator.id,
                moderator.last_read_at
            )

        return Response(status=HTTP_200_OK)
    
    @action(
        detail=False,
        methods=['get'],
        url_path='unassigned'
    )
    def list_unassigned_inquiries(self, request):
        inquiries = filter_and_fetch_inquiries_in_desc_order_based_on_updated_at(
            request,
            inquirymoderator__isnull=True
        )

        pagination = CustomPageNumberPagination()
        inquiries = pagination.paginate_queryset(inquiries, request)
        serializer = serialize_inquiries_for_list(inquiries)

        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'assigned'
    )
    def list_assigned_inquiries(self, request):
        inquiries = filter_and_fetch_inquiries_in_desc_order_based_on_updated_at(
            request,
            inquirymoderator__isnull=False
        )

        pagination = CustomPageNumberPagination()
        inquiries = pagination.paginate_queryset(inquiries, request)
        serializer = serialize_inquiries_for_list(inquiries)

        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'solved'
    )
    def list_solved_inquiries(self, request):
        inquiries = filter_and_fetch_inquiries_in_desc_order_based_on_updated_at(
            request,
            solved=True
        )

        pagination = CustomPageNumberPagination()
        inquiries = pagination.paginate_queryset(inquiries, request)
        serializer = serialize_inquiries_for_list(inquiries)

        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'unsolved'
    )
    def list_unsolved_inquiries(self, request):
        inquiries = filter_and_fetch_inquiries_in_desc_order_based_on_updated_at(
            request,
            solved=False
        )

        pagination = CustomPageNumberPagination()
        inquiries = pagination.paginate_queryset(inquiries, request)
        serializer = serialize_inquiries_for_list(inquiries)

        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'mine'
    )
    def list_my_inquiries(self, request):
        inquiries = filter_and_fetch_inquiries_in_desc_order_based_on_updated_at(
            request,
            inquirymoderator__moderator=request.user
        )

        pagination = CustomPageNumberPagination()
        inquiries = pagination.paginate_queryset(inquiries, request)

        data = InquirySerializerService.serialize_inquiries_for_specific_moderator(
            request,
            inquiries,
        )
        return pagination.get_paginated_response(data)
    
    @action(
        detail=True,
        methods=['post'],
        url_path='moderators'
    )
    def assign_moderator(self, request, pk=None):
        inquiry = InquiryService.get_inquiry_without_messages(pk)
        if not inquiry:
            return Response(status=HTTP_404_NOT_FOUND)
        
        InquiryModeratorService.assign_moderator(request, inquiry)
        send_new_moderator_to_live_chat(inquiry, request.user.id)
        return Response(status=HTTP_201_CREATED)
    
    @assign_moderator.mapping.delete
    def unassign_moderator(self, request, pk=None):
        inquiry = InquiryService.get_inquiry_without_messages(pk)
        if not inquiry:
            return Response(status=HTTP_404_NOT_FOUND)
        
        InquiryModeratorService.unassign_moderator(request, inquiry)
        send_unassigned_inquiry_to_live_chat(inquiry, request.user.id)
        return Response(status=HTTP_200_OK)
    
    @action(
        detail=True,
        methods=['post'],
        url_path='messages'
    )
    def send_message(self, request, pk=None):
        message, error, status = InquiryModeratorService.create_message_for_inquiry(request, pk)
        if not message:
            return Response(status=status, data=error)

        broadcast_inquiry_updates_to_all_parties.delay(pk, message.id)
        return Response(status=HTTP_201_CREATED, data={'id': str(message.id)})


class ReportAdminViewSet(viewsets.ViewSet):
    authentication_classes = [CookieJWTAdminAccessAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request):
        reports = ReportService.get_reports(request)
        pagination = CustomPageNumberPagination()
        reports = pagination.paginate_queryset(reports, request)

        serializer = serialize_reports(reports)
        return pagination.get_paginated_response(serializer.data)
    
    def retrieve(self, request, pk=None):
        report = ReportService.get_report(pk)
        if not report:
            return Response(status=HTTP_404_NOT_FOUND)

        serializer = serialize_report(report)
        return Response(serializer.data)
    
    def partial_update(self, request, pk=None):
        updated, error, status = ReportService.update_report(request, pk)
        if error:
            return Response(status=status, data=error)

        return Response(status=HTTP_200_OK)
    
    @action(
        detail=False,
        methods=['get'],
        url_path='resolved' 
    )
    def list_resolved_reports(self, request):
        reports = ReportService.get_reports(resolved=True)

        pagination = CustomPageNumberPagination()
        reports = pagination.paginate_queryset(reports, request)

        serializer = serialize_reports(reports)
        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=False,
        methods=['get'],
        url_path='unresolved'
    )
    def list_unresolved_reports(self, request):
        reports = ReportService.get_reports(resolved=False)

        pagination = CustomPageNumberPagination()
        reports = pagination.paginate_queryset(reports, request)

        serializer = serialize_reports(reports)
        return pagination.get_paginated_response(serializer.data)
    

class ReportViewSet(viewsets.ViewSet):
    authentication_classes = [CookieJWTAccessAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request):
        created, error, status = ReportService.create_report(request)
        if error:
            return Response(status=status, data=error)

        return Response(status=HTTP_201_CREATED)
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'types',
    )
    def get_report_types(self, request):
        types = ReportService.get_report_types()
        serializer = ReportSerializerService.serialize_report_types(types)
        return Response(serializer.data)
    

class PostManagementViewSet(viewsets.ViewSet):
    authentication_classes = [CookieJWTAdminAccessAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request):
        posts = PostManagementService.get_all_posts()

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(posts, request)

        serializer = PostManagementSerializerService.serialize_posts(paginated_data)
        return pagination.get_paginated_response(serializer.data)

    def partial_update(self, request, pk=None): 
        updated, error, status = PostManagementService.update_post(request, pk)
        if not updated:
            return Response(status=status, data=error)

        return Response(
            {'message': 'Post updated successfully!'}, 
            status=HTTP_200_OK
        )
    

class UserManagementViewSet(viewsets.ViewSet):
    authentication_classes = [CookieJWTAdminAccessAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request):
        users = UserManagementService.get_user_list(request)

        pagination = CustomPageNumberPagination()
        users = pagination.paginate_queryset(users, request)

        serializer = UserManagementSerializerService.serialize_users(users)
        return pagination.get_paginated_response(serializer.data)
    
    def retrieve(self, request, pk=None):
        user = UserManagementService.get_user(pk)
        if not user:
            return Response(status=HTTP_404_NOT_FOUND)

        serializer = UserManagementSerializerService.serialize_user(user)
        return Response(serializer.data)
    
    def partial_update(self, request, pk=None):
        updated, error, status = UserManagementService.update_user(request, pk)
        if not updated:
            return Response(status=status, data=error)

        user = UserManagementService.get_user(pk)
        serializer = UserManagementSerializerService.serialize_user(user)
        return Response(serializer.data)

    @method_decorator(cache_page(60 * 60 * 24))
    @action(
        detail=False,
        methods=['get'],
        url_path='roles'
    )
    def get_user_roles(self, request):
        roles = Role.objects.all()
        serializer = RoleSerializer(roles, many=True)

        return Response(serializer.data)
    
    @action(
        detail=True,
        methods=['put'],
        url_path='favorite-teams'
    )
    def update_favorite_teams(self, request, pk=None):
        user = User.objects.filter(id=pk).first()
        if not user:
            return Response(status=HTTP_404_NOT_FOUND)

        updated, error, status = UserManagementService.update_user_favorite_teams(request, pk)
        if not updated:
            return Response(status=status, data=error)

        teams = TeamService.get_team_with_user_like(user)
        if not teams.exists():
            return Response([])

        serializer = TeamSerializerService.serialize_teams_with_user_favorite(teams, user)
        return Response(status=HTTP_200_OK, data=serializer.data)
    
    @action(
        detail=True,
        methods=['get'],
        url_path=r'posts'
    )
    def get_user_posts(self, request, pk=None):
        try:
            User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)

        posts = UserManagementService.get_user_posts(request, pk)

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(posts, request)

        serializer = PostSerializerService.serialize_posts_without_liked(paginated_data)
        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=True,
        methods=['delete'],
        url_path=r'posts/(?P<post_id>[0-9a-zA-Z-]+)'
    )
    def delete_post(self, request, pk=None, post_id=None):
        PostService.delete_post(pk, post_id)
        return Response(status=HTTP_200_OK)
    
    @action(
        detail=True,
        methods=['get'],
        url_path=r'comments'
    )
    def get_user_comments(self, request, pk=None):
        comments = UserManagementService.get_user_comments(request, pk)

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(comments, request)

        serializer = PostCommentSerializerService.serialize_comments_without_liked(paginated_data)
        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=True,
        methods=['patch'],
        url_path=r'comments/(?P<comment_id>[0-9a-zA-Z-]+)'
    )
    def update_user_comment(self, request, pk=None, comment_id=None):
        comment = PostComment.objects.filter(user__id=pk, id=comment_id).first()

        if not comment:
            return Response(status=HTTP_404_NOT_FOUND)

        PostService.update_comment_via_serializer(request, comment)
        return Response(status=HTTP_200_OK)
    
    @update_user_comment.mapping.delete
    def delete_user_comment(self, request, pk=None, comment_id=None):
        PostService.delete_comment(pk, comment_id)
        return Response(status=HTTP_200_OK)
    
    @action(
        detail=True,
        methods=['get'],
        url_path=r'chats'
    )
    def get_user_chats(self, request, pk=None):
        chats = UserManagementService.get_user_chats(request, pk)
        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(chats, request)

        serializer = UserChatSerializerService.serialize_chats_without_unread_count(paginated_data)
        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=True,
        methods=['get'],
        url_path=r'chats/(?P<chat_id>[0-9a-zA-Z-]+)'
    )
    def get_user_chat(self, request, pk=None, chat_id=None):
        chat = UserManagementService.get_chat(request, pk, chat_id)
        if not chat:
            return Response(status=HTTP_404_NOT_FOUND)

        serializer = UserChatSerializerService.serialize_chat_with_entire_log(chat)
        return Response(serializer.data)