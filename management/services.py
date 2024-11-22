from datetime import datetime
from typing import List
from api.websocket import broadcast_message_to_centrifuge, send_message_to_centrifuge
from management.models import Inquiry, InquiryMessage, InquiryModerator, InquiryModeratorMessage, InquiryTypeDisplayName, Report
from management.serializers import InquiryModeratorMessageSerializer, InquiryModeratorSerializer, InquirySerializer, ReportSerializer

from django.db.models import Prefetch, Q
from django.db.models.manager import BaseManager

from teams.models import Post, PostComment
from users.models import UserChat


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

def filter_and_fetch_inquiries_in_desc_order_based_on_updated_at(**kwargs) -> BaseManager[Inquiry]:
    queryset = Inquiry.objects.select_related(
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

    if kwargs:
        return queryset.filter(**kwargs)
    
    return queryset


def filter_and_fetch_inquiry(**kwargs) -> Inquiry:
    queryset = Inquiry.objects.select_related(
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
    )

    if kwargs:
        return queryset.filter(**kwargs).first()
    
    return queryset.first()

def create_post_queryset_without_prefetch(
    request, 
    fields_only=[], 
    **kwargs
) -> BaseManager[Post]:
    """
    Create a queryset for the Post model without prefetching and selecting related models.\n 
    - request: request object.\n
    - fields_only: list of fields to return in the queryset.\n
    - **kwargs: keyword arguments to filter
    """

    sort_by : str | None = request.query_params.get('sort', None)
    if sort_by is not None:
        sort_by : List[str] = sort_by.split(',')
        unique_sort_by = set(sort_by)

        for field in unique_sort_by:
            if field not in post_queryset_allowed_order_by_fields:
                unique_sort_by.remove(field)

        sort_by = list(unique_sort_by)

    if kwargs is not None:
        queryset = Post.objects.filter(**kwargs)
    else:
        queryset = Post.objects.all()

    search_term = request.query_params.get('search', None)
    if search_term is not None:
        queryset = queryset.filter(
            Q(title__icontains=search_term) | Q(content__icontains=search_term)
        )

    teams_filter : str | None = request.query_params.get('teams', None)
    if teams_filter is not None:
        teams_filter = teams_filter.split(',')
        queryset = queryset.filter(team__symbol__in=teams_filter)

    status_filter : str | None = request.query_params.get('status', None)
    if status_filter is not None:
        status_filter = status_filter.split(',')
        queryset = queryset.filter(status__id__in=status_filter)

    if sort_by is not None:
        queryset = queryset.order_by(*sort_by)
    else:
        queryset = queryset.order_by('-created_at')

    if fields_only:
        return queryset.only(*fields_only)

    return queryset

def create_post_comment_queryset_without_prefetch(
    request, 
    fields_only=[], 
    **kwargs
) -> BaseManager[Post]:
    """
    Create a queryset for the PostComment model without prefetching and selecting related models.\n
    - request: request object.\n
    - fields_only: list of fields to return in the queryset.\n
    - **kwargs: keyword arguments to filter
    """

    sort_by : str | None = request.query_params.get('sort', None)
    if sort_by is not None:
        sort_by : List[str] = sort_by.split(',')
        unique_sort_by = set(sort_by)

        for field in unique_sort_by:
            if field not in post_comment_queryset_allowed_order_by_fields:
                unique_sort_by.remove(field)

        sort_by = list(unique_sort_by)

    if kwargs is not None:
        queryset = PostComment.objects.filter(**kwargs)
    else:
        queryset = PostComment.objects.all()

    search_term = request.query_params.get('search', None)
    if search_term is not None:
        queryset = queryset.filter(
            Q(post__title__icontains=search_term) | Q(content__icontains=search_term)
        )

    teams_filter : str | None = request.query_params.get('teams', None)
    if teams_filter is not None:
        teams_filter = teams_filter.split(',')
        queryset = queryset.filter(post__team__symbol__in=teams_filter)

    status_filter : str | None = request.query_params.get('status', None)
    if status_filter is not None:
        status_filter = status_filter.split(',')
        queryset = queryset.filter(status__id__in=status_filter)

    if sort_by is not None:
        queryset = queryset.order_by(*sort_by)
    else:
        queryset = queryset.order_by('-created_at')

    if fields_only:
        return queryset.only(*fields_only)

    return queryset

def create_userchat_queryset_without_prefetch(
    request, 
    fields_only=[], 
    **kwargs
):
    """
    Create a queryset for the UserChat model without prefetching and selecting related models.\n
    - request: request object.\n
    - fields_only: list of fields to return in the queryset.\n
    - **kwargs: keyword arguments to filter
    """

    sort_by : str | None = request.query_params.get('sort', None)
    if sort_by is not None:
        sort_by : List[str] = sort_by.split(',')
        unique_sort_by = set(sort_by)

        for field in unique_sort_by:
            if field not in userchat_queryset_allowed_order_by_fields:
                unique_sort_by.remove(field)

        sort_by = list(unique_sort_by)

    if kwargs is not None:
        queryset = UserChat.objects.filter(**kwargs)
    else:
        queryset = UserChat.objects.all()

    search_term = request.query_params.get('search', None)
    if search_term is not None:
        queryset = queryset.filter(
            Q(userchatparticipant__user__username__icontains=search_term) | 
            Q(userchatparticipant__user__email__icontains=search_term)
        )

    if sort_by is not None:
        queryset = queryset.order_by(*sort_by)
    else:
        queryset = queryset.order_by('-created_at')

    if fields_only:
        return queryset.only(*fields_only)

    return queryset