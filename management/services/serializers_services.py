from datetime import datetime
from typing import List
from api.websocket import broadcast_message_to_centrifuge, send_message_to_centrifuge
from management.models import (
    Inquiry, 
    InquiryModerator, 
    InquiryModeratorMessage, 
    InquiryType, 
    Report, 
    ReportType, 
)
from management.serializers import (
    InquiryModeratorMessageCreateSerializer, 
    InquiryModeratorMessageSerializer, 
    InquiryModeratorSerializer, 
    InquirySerializer, 
    InquiryTypeSerializer, 
    InquiryUpdateSerializer, 
    ReportCreateSerializer, 
    ReportSerializer, 
    ReportTypeSerializer, 
    UserUpdateSerializer
)

from django.db.models import Prefetch
from django.db.models.manager import BaseManager

from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from teams.models import Post 
from users.models import User
from users.serializers import PostSerializer, PostUpdateSerializer, UserSerializer


post_queryset_allowed_order_by_fields = (
    'title',
    '-title',
    'created_at',
    '-created_at',
    'status__name',
    '-status__name',
    'team__symbol',
    '-team__symbol',
)

post_comment_queryset_allowed_order_by_fields = (
    'post__title',
    '-post__title',
    'created_at',
    '-created_at',
    'status__name',
    '-status__name',
)

userchat_queryset_allowed_order_by_fields = (
    'created_at',
    '-created_at',
    'updated_at',
    '-updated_at',
    'userchatparticipant__user__username',
    '-userchatparticipant__user__username',
)

report_queryset_allowed_order_by_fields = (
    'created_at',
    '-created_at',
    'updated_at',
    '-updated_at',
    'resolved',
    '-resolved',
    'title',
    '-title',
)

def send_inquiry_notification_to_all_channels_for_moderators(inquiry: Inquiry) -> None:
    moderator_inquiry_serializer = InquirySerializer(
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
                'fields_exclude': ['inquiry_data', 'user_data']
            },
            'inquirymoderator': {
                'fields': ['moderator_data', 'last_message', 'in_charge']
            },
            'moderator': {
                'fields': ['username', 'id']
            },
            'inquirymoderatormessage': {
                'fields_exclude': ['inquiry_moderator_data', 'user_data']
            },
            'language': {
                'fields': ['name']
            }
        }
    )

    channel_names = [
        'moderators/inquiries/all/updates',
        'moderators/inquiries/unassigned/updates',
        'moderators/inquiries/assigned/updates',
        'moderators/inquiries/solved/updates',
        'moderators/inquiries/unsolved/updates',
    ]

    resp_json = broadcast_message_to_centrifuge(
        channel_names,
        moderator_inquiry_serializer.data
    )
    if resp_json.get('error', None):
        print(f"Error sending message to {channel_names}: {resp_json['error']}")


def send_inquiry_notification_to_specific_moderator(
    inquiry: Inquiry, 
    user_id: int, 
    last_read_at: datetime
) -> None:
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
                'fields_exclude': ['inquiry_data', 'user_data']
            },
            'inquirymessage_extra': {
                'user_last_read_at': {
                    'id': user_id,
                    'last_read_at': last_read_at
                }
            },
            'inquirymoderator': {
                'fields': [
                    'moderator_data', 
                    'last_message', 
                    'unread_messages_count', 
                    'in_charge'
                ]
            },
            'moderator': {
                'fields': ['username', 'id']
            },
            'inquirymoderatormessage': {
                'fields_exclude': ['inquiry_moderator_data', 'user_data']
            },
            'inquirymoderatormessage_extra': {
                'user_last_read_at': {
                    'id': user_id,
                    'last_read_at': last_read_at
                }
            },
            'language': {
                'fields': ['name']
            }
        }
    )

    moderator_inquiry_notification_channel_name = f'moderators/{user_id}/inquiries/updates'
    resp_json = send_message_to_centrifuge(
        moderator_inquiry_notification_channel_name,
        inquiry_serializer.data
    )
    if resp_json.get('error', None):
        print(f"Error sending message to {moderator_inquiry_notification_channel_name}: {resp_json['error']}")


def send_inquiry_notification_to_user(
    inquiry: Inquiry, 
    user_id: int, 
    last_read_at: datetime
) -> None:
    inquiry_serializer = InquirySerializer(
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
                'fields_exclude': ['inquiry_data', 'user_data']
            },
            'inquirymoderator': {
                'fields': [
                    'moderator_data', 
                    'last_message', 
                    'unread_messages_count', 
                    'in_charge'
                ]
            },
            'moderator': {
                'fields': ['username', 'id']
            },
            'inquirymoderatormessage': {
                'fields_exclude': ['inquiry_moderator_data', 'user_data']
            },
            'inquirymoderatormessage_extra': {
                'user_last_read_at': {
                    'id': user_id,
                    'last_read_at': last_read_at
                }
            },
            'language': {
                'fields': ['name']
            }
        }
    )

    user_inquiry_notification_channel_name = f'users/{user_id}/inquiries/updates'
    resp_json = send_message_to_centrifuge(
        user_inquiry_notification_channel_name,
        inquiry_serializer.data
    )
    if resp_json.get('error', None):
        print(f"Error sending message to {user_inquiry_notification_channel_name}: {resp_json['error']}")


def send_inquiry_message_to_live_chat(
    message: InquiryModeratorMessage, 
    chat_id: str
):
    message_serializer = InquiryModeratorMessageSerializer(
        message,
        fields_exclude=['inquiry_moderator_data'],
        context={
            'user': {
                'fields': ['username', 'id']
            }
        }
    )

    data = {
        'type': 'message',
        'message': message_serializer.data
    }

    inquiry_channel_name = f'users/inquiries/{chat_id}'
    resp_json = send_message_to_centrifuge(
        inquiry_channel_name,
        data
    )
    if resp_json.get('error', None):
        print(f"Error sending message to {inquiry_channel_name}: {resp_json['error']}")


def send_new_moderator_to_live_chat(
    inquiry: Inquiry,
    moderator_user_id: int
):
    inquiry_serializer = InquirySerializer(
        inquiry,
        fields_exclude=[
            'last_message', 
            'unread_messages_count', 
            'messages', 
            'moderators'
        ],
        context={
            'user': {
                'fields': ['username', 'id']
            },
            'inquirytypedisplayname': {
                'fields': ['display_name', 'language_data']
            },
            'language': {
                'fields': ['name']
            }
        }
    )

    inquiry_moderators = InquiryModerator.objects.filter(
        inquiry=inquiry,
        moderator__id=moderator_user_id
    ).select_related(
        'moderator'
    ).prefetch_related(
        Prefetch(
            'inquirymoderatormessage_set',
            queryset=InquiryModeratorMessage.objects.order_by('created_at')
        )
    )

    inquiry_moderator_serializer = InquiryModeratorSerializer(
        inquiry_moderators,
        many=True,
        fields=['moderator_data', 'messages', 'in_charge'],
        context={
            'moderator': {
                'fields': ['username', 'id']
            },
            'inquirymoderatormessage': {
                'fields_exclude': ['inquiry_moderator_data', 'user_data']
            },
        }
    )

    inquiry_serializer_data = inquiry_serializer.data
    inquiry_serializer_data['moderators'] = inquiry_moderator_serializer.data

    data = {
        'inquiry': inquiry_serializer_data
    }

    inquiry_channel_name = f'users/inquiries/{inquiry.id}'
    resp_json = send_message_to_centrifuge(
        inquiry_channel_name,
        data,
        type='new_moderator'
    )
    if resp_json.get('error', None):
        print(f"Error sending message to {inquiry_channel_name}: {resp_json['error']}")


def send_unassigned_inquiry_to_live_chat(
    inquiry: Inquiry,
    moderator_user_id: int
):
    inquiry_serializer = InquirySerializer(
        inquiry,
        fields_exclude=[
            'last_message', 
            'unread_messages_count', 
            'messages', 
        ],
        context={
            'user': {
                'fields': ['username', 'id']
            },
            'inquirytypedisplayname': {
                'fields': ['display_name', 'language_data']
            },
            'language': {
                'fields': ['name']
            },
            'inquirymoderator': {
                'fields': ['moderator_data', 'in_charge']
            },
            'moderator': {
                'fields': ['username', 'id']
            }
        }
    )

    inquiry_moderators = InquiryModerator.objects.filter(
        inquiry=inquiry,
        moderator__id=moderator_user_id
    ).select_related(
        'moderator'
    ).prefetch_related(
        Prefetch(
            'inquirymoderatormessage_set',
            queryset=InquiryModeratorMessage.objects.order_by('created_at')
        )
    )

    inquiry_moderator_serializer = InquiryModeratorSerializer(
        inquiry_moderators,
        many=True,
        fields=['moderator_data', 'messages', 'in_charge'],
        context={
            'moderator': {
                'fields': ['username', 'id']
            },
            'inquirymoderatormessage': {
                'fields_exclude': ['inquiry_moderator_data', 'user_data']
            },
        }
    )

    inquiry_serializer_data = inquiry_serializer.data
    inquiry_serializer_data['moderators'] = inquiry_moderator_serializer.data

    data = {
        'inquiry': inquiry_serializer_data
    }

    inquiry_channel_name = f'users/inquiries/{inquiry.id}'
    resp_json = send_message_to_centrifuge(
        inquiry_channel_name,
        data,
        type='unassign_moderator'
    )
    if resp_json.get('error', None):
        print(f"Error sending message to {inquiry_channel_name}: {resp_json['error']}")


def send_partially_updated_inquiry_to_live_chat(
    inquiry: Inquiry,
):
    inquiry_serializer = InquirySerializer(
        inquiry,
        fields_exclude=[
            'last_message', 
            'unread_messages_count', 
            'messages', 
            'moderators'
        ],
        context={
            'user': {
                'fields': ['username', 'id']
            },
            'inquirytypedisplayname': {
                'fields': ['display_name', 'language_data']
            },
            'language': {
                'fields': ['name']
            },
        }
    )

    data = {
        'inquiry': inquiry_serializer.data
    }

    inquiry_channel_name = f'users/inquiries/{inquiry.id}'
    resp_json = send_message_to_centrifuge(
        inquiry_channel_name,
        data,
        type='inquiry_state_update'
    )
    if resp_json.get('error', None):
        print(f"Error sending message to {inquiry_channel_name}: {resp_json['error']}")


def serialize_inquiries_for_list(inquiries: List[Inquiry]) -> InquirySerializer:
    return InquirySerializer(
        inquiries,
        many=True,
        fields_exclude=['messages', 'unread_messages_count'],
        context={
            'user': {
                'fields': ['username', 'id']
            },
            'inquirytypedisplayname': {
                'fields': ['display_name', 'language_data']
            },
            'inquirymessage': {
                'fields_exclude': ['inquiry_data', 'user_data']
            },
            'inquirymoderator': {
                'fields': ['moderator_data', 'last_message', 'in_charge']
            },
            'moderator': {
                'fields': ['username', 'id']
            },
            'inquirymoderatormessage': {
                'fields_exclude': ['inquiry_moderator_data', 'user_data']
            },
            'language': {
                'fields': ['name']
            }
        }
    )

def serialize_inquiry_for_specific_moderator(
    inquiry: Inquiry,
    user_id: int, 
    last_read_at: datetime
) -> InquirySerializer:
    return InquirySerializer(
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
                'fields_exclude': ['inquiry_data', 'user_data']
            },
            'inquirymessage_extra': {
                'user_last_read_at': {
                    'id': user_id,
                    'last_read_at': last_read_at
                }
            },
            'inquirymoderator': {
                'fields': [
                    'moderator_data', 
                    'last_message', 
                    'unread_messages_count', 
                    'in_charge'
                ]
            },
            'moderator': {
                'fields': ['username', 'id']
            },
            'inquirymoderatormessage': {
                'fields_exclude': ['inquiry_moderator_data', 'user_data']
            },
            'inquirymoderatormessage_extra': {
                'user_last_read_at': {
                    'id': user_id,
                    'last_read_at': last_read_at
                }
            },
            'language': {
                'fields': ['name']
            }
        }
    )

def serialize_inquiry(
   inquiry: Inquiry,
):
    return InquirySerializer(
        inquiry,
        fields_exclude=['last_message', 'unread_messages_count'],
        context={
            'user': {
                'fields': ['username', 'id']
            },
            'inquirytypedisplayname': {
                'fields': ['display_name', 'language_data']
            },
            'inquirymessage': {
                'fields_exclude': ['inquiry_data', 'user_data']
            },
            'inquirymoderator': {
                'fields': [
                    'moderator_data', 
                    'messages', 
                    'in_charge'
                ]
            },
            'moderator': {
                'fields': ['username', 'id']
            },
            'inquirymoderatormessage': {
                'fields_exclude': ['inquiry_moderator_data', 'user_data']
            },
            'language': {
                'fields': ['name']
            }
        }
    )


def serialize_reports(reports: List[Report]):
    return ReportSerializer(
        reports,
        many=True,
        fields_exclude=['accused_data', 'accuser_data', 'description'],
        context={
            'reporttypedisplayname': {
                'fields': ['display_name', 'language_data']
            },
            'language': {
                'fields': ['name']
            }
        }
    )


def serialize_report(report: Report) -> ReportSerializer:
    return ReportSerializer(
        report,
        context={
            'user': {
                'fields': ['username', 'id']
            },
            'reporttypedisplayname': {
                'fields': ['display_name', 'language_data']
            },
            'language': {
                'fields': ['name']
            }
        }
    )

class InquiryModeratorSerializerService:
    @staticmethod
    def update_inquiry(request, pk):
        data = request.data
        inquiry = Inquiry.objects.filter(
            inquirymoderator__moderator=request.user
        ).filter(id=pk).first()

        if not inquiry:
            return False, {'error': 'Inquiry not found'}, HTTP_404_NOT_FOUND

        serializer = InquiryUpdateSerializer(
            inquiry, 
            data=data, 
            partial=True
        )         
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return True, None, None
    
    @staticmethod
    def create_message_for_inquiry(request, pk):
        inquiry_moderator = InquiryModerator.objects.filter(
            inquiry__id=pk, 
            inquiry__solved=False
        ).filter(moderator=request.user).first()

        if not inquiry_moderator:
            return None, {'error': 'Inquiry not found'}, HTTP_404_NOT_FOUND
        
        message_serializer = InquiryModeratorMessageCreateSerializer(data=request.data)
        message_serializer.is_valid(raise_exception=True)
        message = message_serializer.save(inquiry_moderator=inquiry_moderator)

        return message, None, None


class InquirySerializerService:
    @staticmethod
    def serialize_inquiry(inquiry: Inquiry) -> InquirySerializer:
        return serialize_inquiry(inquiry)
    
    @staticmethod
    def serialize_inquiries(inquiries: List[Inquiry]) -> InquirySerializer:
        return serialize_inquiries_for_list(inquiries)

    @staticmethod
    def serialize_inquiry_types(types : BaseManager[InquiryType]) -> InquiryTypeSerializer:
        return InquiryTypeSerializer(
            types,
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
    
    @staticmethod
    def serialize_inquiries_for_specific_moderator(
        request,
        inquiries: List[Inquiry],
    ) -> InquirySerializer:
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

        return data

    
class ReportSerializerService:
    @staticmethod
    def update_report(request, pk):
        data = request.data
        report = Report.objects.filter(id=pk).first()

        if not report:
            return False, {'error': 'Report not found'}, HTTP_404_NOT_FOUND

        serializer = InquiryUpdateSerializer(
            report, 
            data=data, 
            partial=True
        )         
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return True, None, None
    

    @staticmethod
    def create_report(request):
        user = request.user

        data = request.data
        accused = data.pop('accused', None)

        if not accused:
            return False, {'error': 'Accused user not provided'}, HTTP_400_BAD_REQUEST
        
        accused = User.objects.filter(id=accused).first()
        if not accused:
            return False, {'error': 'Accused user not found'}, HTTP_404_NOT_FOUND
        if accused == user:
            return False, {'error': 'You cannot report yourself'}, HTTP_400_BAD_REQUEST

        serializer = ReportCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            accused=accused,
            accuser=user
        )
        
        return True, None, None

    @staticmethod
    def serialize_report_types(types: BaseManager[ReportType]) -> ReportTypeSerializer:
        return ReportTypeSerializer(
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

class PostManagementSerializerService:
    @staticmethod
    def update_post(request, pk):
        try:
            post = Post.objects.get(id=pk)
        except Post.DoesNotExist:
            return False, {'error': 'Post not found'}, HTTP_404_NOT_FOUND

        serializer = PostUpdateSerializer(post, data=request.data, partial=True) 
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return True, None, None

    @staticmethod
    def serialize_posts(posts: List[Post]):
        return PostSerializer(
            posts,
            many=True,
            fields_exclude=['content', 'liked'],
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

class UserManagementSerializerService:
    @staticmethod
    def update_user(request, pk):
        user = User.objects.filter(id=pk).first()

        if not user:
            return False, {'error': 'User not found'}, HTTP_404_NOT_FOUND
        
        if request.user == user:
            return False, {'error': 'You cannot update your own account'}, HTTP_400_BAD_REQUEST

        if request.user.role.weight >= user.role.weight:
            return False, {'error': 'You cannot update a user with the same or higher role'}, HTTP_400_BAD_REQUEST

        serializer = UserUpdateSerializer(
            user, 
            data=request.data,
            partial=True
        )         
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return True, None, None

    @staticmethod
    def serialize_users(users):
        return UserSerializer(
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
    
    @staticmethod
    def serialize_user(user : User) -> UserSerializer:
        return UserSerializer(
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
                'favorite_team'
            ],
            context={
                'team': {
                    'fields': ['id', 'symbol']
                }
            }
        )