from datetime import datetime
from typing import List
from api.websocket import broadcast_message_to_centrifuge, send_message_to_centrifuge
from management.models import Inquiry, InquiryModerator, InquiryModeratorMessage
from management.serializers import InquiryModeratorMessageSerializer, InquiryModeratorSerializer, InquirySerializer

from django.db.models import Prefetch


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
        'type': 'new_moderator',
        'inquiry': inquiry_serializer_data
    }

    inquiry_channel_name = f'users/inquiries/{inquiry.id}'
    resp_json = send_message_to_centrifuge(
        inquiry_channel_name,
        data
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
        'type': 'unassign_moderator',
        'inquiry': inquiry_serializer_data
    }

    inquiry_channel_name = f'users/inquiries/{inquiry.id}'
    resp_json = send_message_to_centrifuge(
        inquiry_channel_name,
        data
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
        'type': 'inquiry_state_update',
        'inquiry': inquiry_serializer.data
    }

    inquiry_channel_name = f'users/inquiries/{inquiry.id}'
    resp_json = send_message_to_centrifuge(
        inquiry_channel_name,
        data
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