from rest_framework import viewsets
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.db.models import Prefetch
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework.permissions import AllowAny
from rest_framework.decorators import action

from api.paginators import CustomPageNumberPagination
from management.models import (
    Inquiry, 
    InquiryMessage, 
    InquiryModerator, 
    InquiryModeratorMessage, 
    InquiryType, 
    InquiryTypeDisplayName
)
from management.serializers import (
    InquiryCreateSerializer, 
    InquiryModeratorMessageCreateSerializer, 
    InquiryTypeSerializer,
    InquiryUpdateSerializer
)
from management.services import ( 
    send_inquiry_message_to_live_chat,
    send_inquiry_notification_to_all_channels_for_moderators,
    send_inquiry_notification_to_specific_moderator,
    send_inquiry_notification_to_user,
    send_new_moderator_to_live_chat,
    send_partially_updated_inquiry_to_live_chat,
    send_unassigned_inquiry_to_live_chat,
    serialize_inquiries_for_list,
    serialize_inquiry,
    serialize_inquiry_for_specific_moderator
)
from users.authentication import CookieJWTAccessAuthentication, CookieJWTAdminAccessAuthentication
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
            Prefetch(
                'messages',
                queryset=InquiryMessage.objects.order_by('created_at')
            ),
            Prefetch(
                'inquirymoderator_set',
                queryset=InquiryModerator.objects.select_related(
                    'moderator'
                ).prefetch_related(
                    Prefetch(
                        'inquirymoderatormessage_set',
                        queryset=InquiryModeratorMessage.objects.order_by('created_at')
                    )
                )
            )
        ).first()

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
            Prefetch(
                'messages',
                queryset=InquiryMessage.objects.order_by('created_at')
            ),
            Prefetch(
                'inquirymoderator_set',
                queryset=InquiryModerator.objects.select_related(
                    'moderator'
                ).prefetch_related(
                    Prefetch(
                        'inquirymoderatormessage_set',
                        queryset=InquiryModeratorMessage.objects.order_by('created_at')
                    )
                )
            )
        ).first()

        if not inquiry:
            return Response(status=HTTP_404_NOT_FOUND)

        serializer = serialize_inquiry(inquiry)
        return Response(serializer.data)
    
    def list(self, request):
        inquiries = Inquiry.objects.select_related(
            'inquiry_type',
            'user'
        ).prefetch_related(
            Prefetch(
                'inquiry_type__inquirytypedisplayname_set',
                queryset=InquiryTypeDisplayName.objects.select_related(
                    'language'
                )
            ),
            Prefetch(
                'messages',
                queryset=InquiryMessage.objects.order_by('created_at')
            ),
            Prefetch(
                'inquirymoderator_set',
                queryset=InquiryModerator.objects.select_related(
                    'moderator'
                ).prefetch_related(
                    Prefetch(
                        'inquirymoderatormessage_set',
                        queryset=InquiryModeratorMessage.objects.order_by('created_at')
                    )
                )
            )
        ).order_by('-updated_at')

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

        notification_inquiry = Inquiry.objects.filter(id=pk).select_related(
            'inquiry_type',
            'user'
        ).prefetch_related(
            Prefetch(
                'inquiry_type__inquirytypedisplayname_set',
                queryset=InquiryTypeDisplayName.objects.select_related(
                    'language'
                )
            ),
            Prefetch(
                'messages',
                queryset=InquiryMessage.objects.order_by('created_at')
            ),
            Prefetch(
                'inquirymoderator_set',
                queryset=InquiryModerator.objects.select_related(
                    'moderator'
                ).prefetch_related(
                    Prefetch(
                        'inquirymoderatormessage_set',
                        queryset=InquiryModeratorMessage.objects.order_by('created_at')
                    )
                )
            )
        ).get()

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
        inquiries = Inquiry.objects.filter(
            inquirymoderator__isnull=True
        ).select_related(
            'inquiry_type',
            'user'
        ).prefetch_related(
            Prefetch(
                'inquiry_type__inquirytypedisplayname_set',
                queryset=InquiryTypeDisplayName.objects.select_related(
                    'language'
                )
            ),
            Prefetch(
                'messages',
                queryset=InquiryMessage.objects.order_by('created_at')
            ),
            Prefetch(
                'inquirymoderator_set',
                queryset=InquiryModerator.objects.select_related(
                    'moderator'
                ).prefetch_related(
                    Prefetch(
                        'inquirymoderatormessage_set',
                        queryset=InquiryModeratorMessage.objects.order_by('created_at')
                    )
                )
            )
        ).order_by('-updated_at')

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
        inquiries = Inquiry.objects.filter(
            inquirymoderator__isnull=False
        ).select_related(
            'inquiry_type',
            'user'
        ).prefetch_related(
            Prefetch(
                'inquiry_type__inquirytypedisplayname_set',
                queryset=InquiryTypeDisplayName.objects.select_related(
                    'language'
                )
            ),
            Prefetch(
                'messages',
                queryset=InquiryMessage.objects.order_by('created_at')
            ),
            Prefetch(
                'inquirymoderator_set',
                queryset=InquiryModerator.objects.select_related(
                    'moderator'
                ).prefetch_related(
                    Prefetch(
                        'inquirymoderatormessage_set',
                        queryset=InquiryModeratorMessage.objects.order_by('created_at')
                    )
                )
            )
        ).order_by('-updated_at')

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
        inquiries = Inquiry.objects.filter(solved=True).select_related(
            'inquiry_type',
            'user'
        ).prefetch_related(
            Prefetch(
                'inquiry_type__inquirytypedisplayname_set',
                queryset=InquiryTypeDisplayName.objects.select_related(
                    'language'
                )
            ),
            Prefetch(
                'messages',
                queryset=InquiryMessage.objects.order_by('created_at')
            ),
            Prefetch(
                'inquirymoderator_set',
                queryset=InquiryModerator.objects.select_related(
                    'moderator'
                ).prefetch_related(
                    Prefetch(
                        'inquirymoderatormessage_set',
                        queryset=InquiryModeratorMessage.objects.order_by('created_at')
                    )
                )
            )
        ).order_by('-updated_at')

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
        inquiries = Inquiry.objects.filter(solved=False).select_related(
            'inquiry_type',
            'user'
        ).prefetch_related(
            Prefetch(
                'inquiry_type__inquirytypedisplayname_set',
                queryset=InquiryTypeDisplayName.objects.select_related(
                    'language'
                )
            ),
            Prefetch(
                'messages',
                queryset=InquiryMessage.objects.order_by('created_at')
            ),
            Prefetch(
                'inquirymoderator_set',
                queryset=InquiryModerator.objects.select_related(
                    'moderator'
                ).prefetch_related(
                    Prefetch(
                        'inquirymoderatormessage_set',
                        queryset=InquiryModeratorMessage.objects.order_by('created_at')
                    )
                )
            )
        ).order_by('-updated_at')

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
        inquiries = Inquiry.objects.filter(
            inquirymoderator__moderator=request.user
        ).select_related(
            'inquiry_type',
            'user'
        ).prefetch_related(
            Prefetch(
                'inquiry_type__inquirytypedisplayname_set',
                queryset=InquiryTypeDisplayName.objects.select_related('language')
            ),
            Prefetch(
                'messages',
                queryset=InquiryMessage.objects.order_by('created_at')
            ),
            Prefetch(
                'inquirymoderator_set',
                queryset=InquiryModerator.objects.select_related('moderator').prefetch_related(
                    Prefetch(
                        'inquirymoderatormessage_set',
                        queryset=InquiryModeratorMessage.objects.order_by('created_at')
                    )
                )
            )
        ).order_by('-updated_at')

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
            Prefetch(
                'messages',
                queryset=InquiryMessage.objects.order_by('created_at')
            ),
            Prefetch(
                'inquirymoderator_set',
                queryset=InquiryModerator.objects.select_related(
                    'moderator'
                ).prefetch_related(
                    Prefetch(
                        'inquirymoderatormessage_set',
                        queryset=InquiryModeratorMessage.objects.order_by('created_at')
                    )
                )
            )
        ).get()
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
    