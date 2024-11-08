from rest_framework import viewsets
from rest_framework.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.db.models import Prefetch
from rest_framework.decorators import action

from api.paginators import CustomPageNumberPagination
from api.websocket import send_message_to_centrifuge
from management.models import Inquiry, InquiryMessage, InquiryModerator, InquiryModeratorMessage, InquiryTypeDisplayName
from management.serializers import InquiryCreateSerializer, InquiryModeratorMessageCreateSerializer, InquiryModeratorMessageSerializer, InquirySerializer

from users.authentication import CookieJWTAccessAuthentication, CookieJWTAdminAccessAuthentication


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
        user = request.user

        inquiry_ref = Inquiry.objects.filter(user=user).filter(id=pk).only('id').first()

        if not inquiry_ref:
            return Response(status=HTTP_404_NOT_FOUND)

        inquiry = Inquiry.objects.filter(id=inquiry_ref.id).select_related(
            'inquiry_type',
            'user'
        ).prefetch_related(
            Prefetch(
                'inquiry_type__inquirytypedisplayname_set',
                queryset=InquiryTypeDisplayName.objects.select_related(
                    'language'
                ).all()
            ),
            Prefetch(
                'inquirymessage_set',
                queryset=InquiryMessage.objects.filter(
                    inquiry__id=pk
                ).order_by('created_at')
            ),
            Prefetch(
                'inquirymoderator_set',
                queryset=InquiryModerator.objects.filter(
                    inquiry__id=pk
                ).select_related(
                    'moderator'
                ).prefetch_related(
                    Prefetch(
                        'inquirymoderatormessage_set',
                        queryset=InquiryModeratorMessage.objects.filter(
                            inquiry_moderator__inquiry__id=pk
                        ).order_by('created_at')
                    )
                )
            )
        ).first()

        serializer = InquirySerializer(
            inquiry,
            fields_exclude=['last_message'],
            context={
                'user': {
                    'fields': ['username', 'id']
                },
                'inquirytypedisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'inquirymessage': {
                    'fields_exclude': ['inquiry_data']
                },
                'inquirymoderator': {
                    'fields': ['moderator_data', 'messages']
                },
                'moderator': {
                    'fields': ['username', 'id']
                },
                'inquirymoderatormessage': {
                    'fields_exclude': ['inquiry_moderator_data']
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
                ).all()
            ),
            Prefetch(
                'inquirymessage_set',
                queryset=InquiryMessage.objects.filter(
                    inquiry__id=pk
                ).order_by('created_at')
            ),
            Prefetch(
                'inquirymoderator_set',
                queryset=InquiryModerator.objects.filter(
                    inquiry__id=pk
                ).select_related(
                    'moderator'
                ).prefetch_related(
                    Prefetch(
                        'inquirymoderatormessage_set',
                        queryset=InquiryModeratorMessage.objects.filter(
                            inquiry_moderator__inquiry__id=pk
                        ).order_by('created_at')
                    )
                )
            )
        ).first()

        if not inquiry:
            return Response(status=HTTP_404_NOT_FOUND)

        serializer = InquirySerializer(
            inquiry,
            fields_exclude=['last_message'],
            context={
                'user': {
                    'fields': ['username', 'id']
                },
                'inquirytypedisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'inquirymessage': {
                    'fields_exclude': ['inquiry_data']
                },
                'inquirymoderator': {
                    'fields': ['moderator_data', 'messages']
                },
                'moderator': {
                    'fields': ['username', 'id']
                },
                'inquirymoderatormessage': {
                    'fields_exclude': ['inquiry_moderator_data']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

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
                ).all()
            ),
            Prefetch(
                'inquirymessage_set',
                queryset=InquiryMessage.objects.all()
            ),
            Prefetch(
                'inquirymoderator_set',
                queryset=InquiryModerator.objects.select_related(
                    'moderator'
                ).prefetch_related(
                    Prefetch(
                        'inquirymoderatormessage_set',
                        queryset=InquiryModeratorMessage.objects.all()
                    )
                )
            )
        )

        pagination = CustomPageNumberPagination()
        inquiries = pagination.paginate_queryset(inquiries, request)

        serializer = InquirySerializer(
            inquiries,
            many=True,
            fields_exclude=['messages'],
            context={
                'user': {
                    'fields': ['username', 'id']
                },
                'inquirytypedisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'inquirymessage': {
                    'fields_exclude': ['inquiry_data']
                },
                'inquirymoderator': {
                    'fields': ['moderator_data', 'last_message']
                },
                'moderator': {
                    'fields': ['username', 'id']
                },
                'inquirymoderatormessage': {
                    'fields_exclude': ['inquiry_moderator_data']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        return Response(serializer.data)
    
    @action(
        detail=True,
        methods=['post'],
        url_path='moderators'
    )
    def assign_moderator(self, request, pk=None):
        inquiry = Inquiry.objects.filter(id=pk).first()

        if not inquiry:
            return Response(status=HTTP_404_NOT_FOUND)
        
        InquiryModerator.objects.create(
            inquiry=inquiry,
            moderator=request.user
        )

        return Response(status=HTTP_201_CREATED)
    
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

        message_serializer = InquiryModeratorMessageSerializer(
            message,
            context={
                'inquirymoderator': {
                    'fields': ['moderator_data']
                },
                'moderator': {
                    'fields': ['username', 'id']
                }
            }
        )

        inquiry = Inquiry.objects.filter(id=pk).select_related(
            'inquiry_type',
            'user'
        ).prefetch_related(
            Prefetch(
                'inquiry_type__inquirytypedisplayname_set',
                queryset=InquiryTypeDisplayName.objects.select_related(
                    'language'
                ).all()
            ),
            Prefetch(
                'inquirymessage_set',
                queryset=InquiryMessage.objects.filter(
                    inquiry__id=pk
                ).order_by('created_at')
            ),
            Prefetch(
                'inquirymoderator_set',
                queryset=InquiryModerator.objects.filter(
                    inquiry__id=pk
                ).select_related(
                    'moderator'
                ).prefetch_related(
                    Prefetch(
                        'inquirymoderatormessage_set',
                        queryset=InquiryModeratorMessage.objects.filter(
                            inquiry_moderator__inquiry__id=pk
                        ).order_by('created_at')
                    )
                )
            )
        ).get()

        user_inquiry_serializer = InquirySerializer(
            inquiry,
            fields_exclude=['messages', 'unread_messages_count'],
            context={
                'user': {
                    'fields': ['username', 'id']
                },
                'inquirytypedisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'inquirymessage': {
                    'fields_exclude': ['inquiry_data']
                },
                'inquirymoderator': {
                    'fields': ['moderator_data', 'last_message', 'unread_messages_count']
                },
                'moderator': {
                    'fields': ['username', 'id']
                },
                'inquirymoderatormessage': {
                    'fields_exclude': ['inquiry_moderator_data']
                },
                'inquirymoderatormessage_extra': {
                    'user_last_read_at': {
                        'id': inquiry.user.id,
                        'last_read_at': inquiry.last_read_at
                    }
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        inquiry_channel_name = f'inquiries/{pk}'
        resp_json = send_message_to_centrifuge(
            inquiry_channel_name,
            message_serializer.data
        )
        if resp_json.get('error', None):
            return Response(
                status=HTTP_404_NOT_FOUND, 
                data={'error': 'Failed to send message'}
            )

        user_inquiry_notification_channel_name = f'users/{inquiry.user.id}/inquiries/updates'
        resp_json = send_message_to_centrifuge(
            user_inquiry_notification_channel_name,
            user_inquiry_serializer.data
        )
        if resp_json.get('error', None):
            return Response(
                {'error': 'Notification Delivery To User Unsuccessful'},
                status=HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        for moderator in inquiry.inquirymoderator_set.all():
            inquiry_serializer = InquirySerializer(
                inquiry,
                fields_exclude=['messages'],
                context={
                    'user': {
                        'fields': ['username', 'id']
                    },
                    'inquirytypedisplayname': {
                        'fields': ['display_name', 'language_data']
                    },
                    'inquirymessage': {
                        'fields_exclude': ['inquiry_data']
                    },
                    'inquirymessage_extra': {
                        'user_last_read_at': {
                            'id': moderator.moderator.id,
                            'last_read_at': moderator.last_read_at
                        }
                    },
                    'inquirymoderator': {
                        'fields': ['moderator_data', 'last_message', 'unread_messages_count']
                    },
                    'moderator': {
                        'fields': ['username', 'id']
                    },
                    'inquirymoderatormessage': {
                        'fields_exclude': ['inquiry_moderator_data']
                    },
                    'inquirymoderatormessage_extra': {
                        'user_last_read_at': {
                            'id': moderator.moderator.id,
                            'last_read_at': moderator.last_read_at
                        }
                    },
                    'language': {
                        'fields': ['name']
                    }
                }
            )

            moderator_inquiry_notification_channel_name = f'moderators/{moderator.moderator.id}/inquiries/updates'
            resp_json = send_message_to_centrifuge(
                moderator_inquiry_notification_channel_name,
                inquiry_serializer.data
            )
            if resp_json.get('error', None):
                return Response(
                    {'error': 'Notification Delivery To Moderator Unsuccessful'},
                    status=HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(status=HTTP_201_CREATED, data={'id': str(message.id)})
    