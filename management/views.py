from rest_framework import viewsets
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.db.models import Prefetch, Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework.permissions import AllowAny
from rest_framework.decorators import action

from api.paginators import CustomPageNumberPagination
from management.models import (
    Inquiry, 
    InquiryModerator, 
    InquiryType, 
    InquiryTypeDisplayName,
    Report,
    ReportType,
    ReportTypeDisplayName
)
from management.serializers import (
    InquiryCreateSerializer, 
    InquiryModeratorMessageCreateSerializer, 
    InquiryTypeSerializer,
    InquiryUpdateSerializer,
    ReportCreateSerializer,
    ReportTypeSerializer
)
from management.services import ( 
    create_post_comment_queryset_without_prefetch,
    create_post_queryset_without_prefetch,
    filter_and_fetch_inquiries_in_desc_order_based_on_updated_at,
    filter_and_fetch_inquiry,
    send_inquiry_message_to_live_chat,
    send_inquiry_notification_to_all_channels_for_moderators,
    send_inquiry_notification_to_specific_moderator,
    send_inquiry_notification_to_user,
    send_new_moderator_to_live_chat,
    send_partially_updated_inquiry_to_live_chat,
    send_unassigned_inquiry_to_live_chat,
    serialize_inquiries_for_list,
    serialize_inquiry,
    serialize_inquiry_for_specific_moderator,
    serialize_report,
    serialize_reports
)
from teams.models import Post, PostComment, PostCommentLike, PostCommentReply, PostLike, PostStatus, PostStatusDisplayName, Team, TeamLike
from teams.serializers import TeamSerializer
from users.authentication import CookieJWTAccessAuthentication, CookieJWTAdminAccessAuthentication
from users.models import Role, User, UserChat, UserChatParticipant, UserLike
from users.serializers import PostCommentSerializer, PostCommentUpdateSerializer, PostSerializer, PostUpdateSerializer, RoleSerializer, UserChatSerializer, UserSerializer, UserUpdateSerializer
from users.services import create_user_queryset_without_prefetch
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
        inquiry = filter_and_fetch_inquiry(id=pk)
        if not inquiry:
            return Response(status=HTTP_404_NOT_FOUND)

        serializer = serialize_inquiry(inquiry)
        return Response(serializer.data)
    
    @method_decorator(cache_page(60 * 60 * 24))
    @action(
        detail=False,
        methods=['get'],
        url_path=r'types',
        permission_classes=[AllowAny]
    )
    def get_inquiry_types(self, request):
        statuses = InquiryType.objects.prefetch_related(
            Prefetch(
                'inquirytypedisplayname_set',
                queryset=InquiryTypeDisplayName.objects.select_related(
                    'language'
                )
            )
        )

        serializer = InquiryTypeSerializer(
            statuses,
            many=True,
            context={
                'inquirytypedisplayname': {
                    'fields_exclude': ['inquiry_type_data']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        return Response(serializer.data)
    

class InquiryModeratorViewSet(viewsets.ViewSet):
    authentication_classes = [CookieJWTAdminAccessAuthentication]
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, pk=None):
        inquiry = filter_and_fetch_inquiry(id=pk)
        if not inquiry:
            return Response(status=HTTP_404_NOT_FOUND)

        serializer = serialize_inquiry(inquiry)
        return Response(serializer.data)
    
    def list(self, request):
        inquiries = filter_and_fetch_inquiries_in_desc_order_based_on_updated_at()

        pagination = CustomPageNumberPagination()
        inquiries = pagination.paginate_queryset(inquiries, request)
        serializer = serialize_inquiries_for_list(inquiries)

        return pagination.get_paginated_response(serializer.data)
    
    def partial_update(self, request, pk=None):
        data = request.data
        inquiry = Inquiry.objects.filter(
            inquirymoderator__moderator=request.user
        ).filter(id=pk).first()

        if not inquiry:
            return Response(status=HTTP_404_NOT_FOUND)

        serializer = InquiryUpdateSerializer(
            inquiry, 
            data=data, 
            partial=True
        )         
        serializer.is_valid(raise_exception=True)
        serializer.save()

        inquiry = Inquiry.objects.filter(id=pk).select_related(
            'inquiry_type',
            'user'
        ).prefetch_related(
            Prefetch(
                'inquiry_type__inquirytypedisplayname_set',
                queryset=InquiryTypeDisplayName.objects.select_related(
                    'language'
                )
            ),
        ).get()

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
            inquirymoderator__moderator=request.user
        )

        pagination = CustomPageNumberPagination()
        inquiries = pagination.paginate_queryset(inquiries, request)

        data = []
        for inquiry in inquiries:
            last_read_at = None
            for moderator in inquiry.inquirymoderator_set.all():
                if moderator.moderator == request.user:
                    last_read_at = moderator.last_read_at
                    break

            serializer = serialize_inquiry_for_specific_moderator(
                inquiry,
                request.user.id, 
                last_read_at
            )

            data.append(serializer.data)

        return pagination.get_paginated_response(data)
    
    @action(
        detail=True,
        methods=['post'],
        url_path='moderators'
    )
    def assign_moderator(self, request, pk=None):
        inquiry = Inquiry.objects.filter(id=pk).select_related(
            'inquiry_type',
            'user'
        ).prefetch_related(
            Prefetch(
                'inquiry_type__inquirytypedisplayname_set',
                queryset=InquiryTypeDisplayName.objects.select_related(
                    'language'
                )
            ),
        ).first()

        if not inquiry:
            return Response(status=HTTP_404_NOT_FOUND)
        
        _, created = InquiryModerator.objects.get_or_create(
            inquiry=inquiry,
            moderator=request.user
        )
        if not created:
            InquiryModerator.objects.filter(
                inquiry=inquiry,
                moderator=request.user
            ).update(in_charge=True)

        inquiry.save()

        send_new_moderator_to_live_chat(inquiry, request.user.id)
        return Response(status=HTTP_201_CREATED)
    
    @assign_moderator.mapping.delete
    def unassign_moderator(self, request, pk=None):
        inquiry = Inquiry.objects.filter(id=pk).select_related(
            'inquiry_type',
            'user'
        ).prefetch_related(
            Prefetch(
                'inquiry_type__inquirytypedisplayname_set',
                queryset=InquiryTypeDisplayName.objects.select_related(
                    'language'
                )
            ),
        ).first()

        if not inquiry:
            return Response(status=HTTP_404_NOT_FOUND)
        
        InquiryModerator.objects.filter(
            inquiry=inquiry,
            moderator=request.user
        ).update(in_charge=False)
        inquiry.save()

        send_unassigned_inquiry_to_live_chat(inquiry, request.user.id)
        return Response(status=HTTP_200_OK)
    
    @action(
        detail=True,
        methods=['post'],
        url_path='messages'
    )
    def send_message(self, request, pk=None):
        inquiry_moderator = InquiryModerator.objects.filter(
            inquiry__id=pk, 
            inquiry__solved=False
        ).filter(moderator=request.user).first()

        if not inquiry_moderator:
            return Response(
                status=HTTP_404_NOT_FOUND, 
                data={'error': 'Inquiry moderator not found'}
            )
        
        message_serializer = InquiryModeratorMessageCreateSerializer(data=request.data)
        message_serializer.is_valid(raise_exception=True)
        message = message_serializer.save(inquiry_moderator=inquiry_moderator)

        inquiry = filter_and_fetch_inquiry(id=pk)
        inquiry.save()

        send_inquiry_message_to_live_chat(message, inquiry.id)
        send_inquiry_notification_to_user(
            inquiry,
            inquiry.user.id,
            inquiry.last_read_at
        )
        send_inquiry_notification_to_all_channels_for_moderators(inquiry)

        for moderator in inquiry.inquirymoderator_set.all():
            send_inquiry_notification_to_specific_moderator(
                inquiry,
                moderator.moderator.id,
                moderator.last_read_at
            )
        
        return Response(status=HTTP_201_CREATED, data={'id': str(message.id)})


class ReportAdminViewSet(viewsets.ViewSet):
    authentication_classes = [CookieJWTAdminAccessAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request):
        reports = Report.objects.select_related(
            'type'
        ).prefetch_related(
            Prefetch(
                'type__reporttypedisplayname_set',
                queryset=ReportTypeDisplayName.objects.select_related(
                    'language'
                )
            )
        ).order_by('-created_at')

        pagination = CustomPageNumberPagination()
        reports = pagination.paginate_queryset(reports, request)

        serializer = serialize_reports(reports)
        return pagination.get_paginated_response(serializer.data)
    
    def retrieve(self, request, pk=None):
        report = Report.objects.filter(id=pk).select_related(
            'type',
            'accused',
            'accuser'
        ).prefetch_related(
            Prefetch(
                'type__reporttypedisplayname_set',
                queryset=ReportTypeDisplayName.objects.select_related(
                    'language'
                )
            )
        ).first()

        if not report:
            return Response(status=HTTP_404_NOT_FOUND)

        serializer = serialize_report(report)
        return Response(serializer.data)
    
    def partial_update(self, request, pk=None):
        data = request.data
        report = Report.objects.filter(id=pk).first()

        if not report:
            return Response(status=HTTP_404_NOT_FOUND)

        serializer = InquiryUpdateSerializer(
            report, 
            data=data, 
            partial=True
        )         
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(status=HTTP_200_OK)
    
    @action(
        detail=False,
        methods=['get'],
        url_path='resolved' 
    )
    def list_resolved_reports(self, request):
        reports = Report.objects.filter(resolved=True).select_related(
            'type'
        ).prefetch_related(
            Prefetch(
                'type__reporttypedisplayname_set',
                queryset=ReportTypeDisplayName.objects.select_related(
                    'language'
                )
            )
        ).order_by('-created_at')

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
        reports = Report.objects.filter(resolved=False).select_related(
            'type'
        ).prefetch_related(
            Prefetch(
                'type__reporttypedisplayname_set',
                queryset=ReportTypeDisplayName.objects.select_related(
                    'language'
                )
            )
        ).order_by('-created_at')

        pagination = CustomPageNumberPagination()
        reports = pagination.paginate_queryset(reports, request)

        serializer = serialize_reports(reports)
        return pagination.get_paginated_response(serializer.data)
    

class ReportViewSet(viewsets.ViewSet):
    authentication_classes = [CookieJWTAccessAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request):
        user = request.user

        data = request.data
        accused = data.pop('accused', None)

        if not accused:
            return Response(status=HTTP_404_NOT_FOUND)
        
        accused = User.objects.filter(id=accused).first()
        if not accused:
            return Response(status=HTTP_404_NOT_FOUND)
        if accused == user:
            return Response(status=HTTP_400_BAD_REQUEST)

        serializer = ReportCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            accused=accused,
            accuser=user
        )

        return Response(status=HTTP_201_CREATED)
    
    @action(
        detail=False,
        methods=['get'],
        url_path=r'types',
    )
    def get_report_types(self, request):
        types = ReportType.objects.prefetch_related(
            Prefetch(
                'reporttypedisplayname_set',
                queryset=ReportTypeDisplayName.objects.select_related(
                    'language'
                )
            )
        )

        serializer = ReportTypeSerializer(
            types,
            many=True,
            context={
                'reporttypedisplayname': {
                    'fields_exclude': ['report_type_data']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        return Response(serializer.data)
    

class PostManagementViewSet(viewsets.ViewSet):
    authentication_classes = [CookieJWTAdminAccessAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request):
        fields_exclude = ['content', 'liked']
        posts = Post.objects.order_by('-created_at').select_related(
            'user',
            'team',
            'status'
        ).prefetch_related(
            Prefetch(
                'postlike_set',
                queryset=PostLike.objects.all()
            ),
            Prefetch(
                'postcomment_set',
                queryset=PostComment.objects.all()
            ),
            Prefetch(
                'status__poststatusdisplayname_set',
                queryset=PostStatusDisplayName.objects.select_related(
                    'language'
                ).all()
            ),
        ).only(
            'id', 
            'title', 
            'created_at', 
            'updated_at', 
            'user__id', 
            'user__username', 
            'team__id', 
            'team__symbol', 
            'status__id', 
            'status__name'
        )

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(posts, request)

        serializer = PostSerializer(
            paginated_data,
            many=True,
            fields_exclude=fields_exclude,
            context={
                'user': {
                    'fields': ('id', 'username')
                },
                'team': {
                    'fields': ('id', 'symbol')
                },
                'poststatusdisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        return pagination.get_paginated_response(serializer.data)

    def partial_update(self, request, pk=None): 
        try:
            post = Post.objects.get(id=pk)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=HTTP_404_NOT_FOUND)

        serializer = PostUpdateSerializer(post, data=request.data, partial=True) 
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {'message': 'Post updated successfully!'}, 
            status=HTTP_200_OK
        )
    

class UserManagementViewSet(viewsets.ViewSet):
    authentication_classes = [CookieJWTAdminAccessAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request):
        queryset = create_user_queryset_without_prefetch(
            request, 
            fields_only=[
                'id', 
                'username', 
                'email',
                'role__id',
                'role__name',
                'role__description',
                'role__weight'
            ]
        ).select_related('role')

        pagination = CustomPageNumberPagination()
        users = pagination.paginate_queryset(queryset, request)

        serializer = UserSerializer(
            users, 
            many=True,
            fields=[
                'id',
                'first_name',
                'last_name',
                'username',
                'email',
                'role_data'
            ]
        )

        return pagination.get_paginated_response(serializer.data)
    
    def retrieve(self, request, pk=None):
        user = User.objects.filter(id=pk).select_related(
            'role'
        ).prefetch_related(
            Prefetch(
                'liked_user',
                queryset=UserLike.objects.all()
            ),
        ).first()

        if not user:
            return Response(status=HTTP_404_NOT_FOUND)

        serializer = UserSerializer(
            user,
            fields=[
                'id',
                'username',
                'email',
                'role_data',
                'introduction',
                'level',
                'created_at',
                'is_profile_visible',
                'chat_blocked',
                'likes_count',
            ]
        )

        return Response(serializer.data)
    
    def partial_update(self, request, pk=None):
        user = User.objects.filter(id=pk).first()

        if not user:
            return Response(status=HTTP_404_NOT_FOUND)
        
        serializer = UserUpdateSerializer(
            user, 
            data=request.data,
            partial=True
        )         
        serializer.is_valid(raise_exception=True)
        serializer.save()

        user = User.objects.filter(id=pk).select_related(
            'role'
        ).prefetch_related(
            Prefetch(
                'liked_user',
                queryset=UserLike.objects.all()
            ),
        ).first()

        serializer = UserSerializer(
            user,
            fields=[
                'id',
                'username',
                'email',
                'role_data',
                'introduction',
                'level',
                'created_at',
                'is_profile_visible',
                'chat_blocked',
                'likes_count',
            ]
        )

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

        data = request.data
        if not isinstance(data, list):
            return Response(status=HTTP_400_BAD_REQUEST)

        if not data:
            TeamLike.objects.filter(user=user).delete()
            return Response(status=HTTP_200_OK, data=[])

        try:
            team_ids = [team['id'] for team in data]
        except KeyError:
            return Response(
                status=HTTP_400_BAD_REQUEST, 
                data={'error': 'Invalid data'}
            )

        teams = Team.objects.filter(id__in=team_ids)

        if not teams:
            return Response(status=HTTP_400_BAD_REQUEST)

        TeamLike.objects.filter(user=user).delete()
        TeamLike.objects.bulk_create([
            TeamLike(user=user, team=team) for team in teams
        ])

        query = Team.objects.prefetch_related(
            'teamname_set'
        ).filter(
            teamlike__user=user
        ).order_by('symbol').only('id', 'symbol')

        if not query.exists():
            return Response([])

        serializer = TeamSerializer(
            query,
            many=True,
            fields=['id', 'symbol', 'teamname_set'],
            context={
                'teamname': {
                    'fields': ['name', 'language']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        return Response(status=HTTP_200_OK, data=serializer.data)
    
    @action(
        detail=True,
        methods=['get'],
        url_path=r'posts'
    )
    def get_user_posts(self, request, pk=None):
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)

        fields_exclude = ['content', 'liked']
        posts = create_post_queryset_without_prefetch(
            request,
            fields_only=[
                'id',
                'title',
                'created_at', 
                'updated_at', 
                'user__id', 
                'user__username', 
                'team__id', 
                'team__symbol', 
                'status__id', 
                'status__name'
            ],
            user=user
        ).prefetch_related(
            Prefetch(
                'postlike_set',
                queryset=PostLike.objects.all()
            ),
            Prefetch(
                'postcomment_set',
                queryset=PostComment.objects.all()
            ),
            Prefetch(
                'status__poststatusdisplayname_set',
                queryset=PostStatusDisplayName.objects.select_related(
                    'language'
                ).all()
            ),
        )

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(posts, request)

        serializer = PostSerializer(
            paginated_data,
            many=True,
            fields_exclude=fields_exclude,
            context={
                'user': {
                    'fields': ('id', 'username')
                },
                'team': {
                    'fields': ('id', 'symbol')
                },
                'poststatusdisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=True,
        methods=['delete'],
        url_path=r'posts/(?P<post_id>[0-9a-zA-Z-]+)'
    )
    def delete_post(self, request, pk=None, post_id=None):
        post = Post.objects.filter(user__id=pk, id=post_id).first()

        if not post:
            return Response(status=HTTP_404_NOT_FOUND)
        
        post.status = PostStatus.objects.get(name='deleted')
        post.save()

        return Response(status=HTTP_200_OK)
    
    @action(
        detail=True,
        methods=['get'],
        url_path=r'comments'
    )
    def get_user_comments(self, request, pk=None):
        comments = create_post_comment_queryset_without_prefetch(
            request, 
            fields_only=[
                'id',
                'content',
                'created_at',
                'updated_at',
                'user__id',
                'user__username',
                'status__id',
                'status__name',
                'post__id',
                'post__title',
                'post__team__id',
                'post__team__symbol',
                'post__user__id',
                'post__user__username'
            ],
            user__id=pk
        ).prefetch_related(
            Prefetch(
                'postcommentlike_set',
                queryset=PostCommentLike.objects.all()
            ),
            Prefetch(
                'postcommentreply_set',
                queryset=PostCommentReply.objects.all()
            ),
        ).select_related(
            'user',
            'status',
            'post__team',
            'post__user'
        )

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(comments, request)

        serializer = PostCommentSerializer(
            paginated_data,
            fields_exclude=['liked'],
            many=True,
            context={
                'user': {
                    'fields': ('id', 'username')
                },
                'status': {
                    'fields': ('id', 'name')
                },
                'post': {
                    'fields': ('id', 'title', 'team_data', 'user_data')
                },
                'team': {
                    'fields': ('id', 'symbol')
                }
            }
        )

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

        serializer = PostCommentUpdateSerializer(
            comment,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(status=HTTP_200_OK)
    
    @update_user_comment.mapping.delete
    def delete_user_comment(self, request, pk=None, comment_id=None):
        comment = PostComment.objects.filter(user__id=pk, id=comment_id).first()

        if not comment:
            return Response(status=HTTP_404_NOT_FOUND)

        comment.status = PostStatus.objects.get(name='deleted')
        comment.save()

        return Response(status=HTTP_200_OK)
    
    @action(
        detail=True,
        methods=['get'],
        url_path=r'chats'
    )
    def get_user_chats(self, request, pk=None):
        chat_query = UserChat.objects.filter(
            userchatparticipant__user__id=pk,
        ).prefetch_related(
            Prefetch(
                'userchatparticipant_set',
                UserChatParticipant.objects.prefetch_related(
                    'userchatparticipantmessage_set',
                ).select_related(
                    'user',
                )
            )
        ).order_by('-updated_at')

        pagination = CustomPageNumberPagination()
        paginated_data = pagination.paginate_queryset(chat_query, request)

        serializer = UserChatSerializer(
            paginated_data,
            many=True,
            fields=['id', 'participants'],
            context={
                'userchatparticipant': {
                    'fields': [
                        'user_data', 
                        'last_message', 
                    ]
                },
                'userchatparticipantmessage': {
                    'fields_exclude': ['sender_data', 'user_data']
                },
                'user': {
                    'fields': ['id', 'username']
                }
            }
        )

        return pagination.get_paginated_response(serializer.data)
    
    @action(
        detail=True,
        methods=['get'],
        url_path=r'chats/(?P<chat_id>[0-9a-zA-Z-]+)'
    )
    def get_user_chat(self, request, pk=None, chat_id=None):
        chat = UserChat.objects.filter(
            userchatparticipant__user__id=pk
        ).filter(
            id=chat_id
        ).prefetch_related(
            Prefetch(
                'userchatparticipant_set',
                UserChatParticipant.objects.prefetch_related(
                    'userchatparticipantmessage_set',
                ).select_related(
                    'user',
                )
            )
        ).first()

        if not chat:
            return Response(status=HTTP_404_NOT_FOUND)

        serializer = UserChatSerializer(
            chat,
            fields=[
                'id', 
                'participants', 
                'created_at', 
                'updated_at'
            ],
            context={
                'userchatparticipant': {
                    'fields': ['user_data', 'messages']
                },
                'userchatparticipantmessage': {
                    'fields_exclude': ['sender_data', 'user_data'],
                },
                'user': {
                    'fields': ['id', 'username']
                }
            }
        )

        return Response(serializer.data)