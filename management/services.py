from datetime import datetime, timezone
from typing import List
from api.websocket import broadcast_message_to_centrifuge, send_message_to_centrifuge
from management.models import Inquiry, InquiryMessage, InquiryModerator, InquiryModeratorMessage, InquiryType, InquiryTypeDisplayName, Report, ReportType, ReportTypeDisplayName
from management.serializers import InquiryModeratorMessageCreateSerializer, InquiryModeratorMessageSerializer, InquiryModeratorSerializer, InquirySerializer, InquiryTypeSerializer, InquiryUpdateSerializer, ReportCreateSerializer, ReportSerializer, ReportTypeSerializer, UserUpdateSerializer

from django.db.models import Prefetch, Q
from django.db.models.manager import BaseManager

from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from teams.models import Post, PostComment, PostCommentLike, PostCommentReply, PostLike, PostStatusDisplayName, Team, TeamLike
from users.models import User, UserChat, UserChatParticipant, UserLike
from users.serializers import PostSerializer, PostUpdateSerializer, UserSerializer
from users.services import create_user_queryset_without_prefetch


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

def filter_and_fetch_inquiries_in_desc_order_based_on_updated_at(request, **kwargs) -> BaseManager[Inquiry]:
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
            queryset=InquiryMessage.objects.order_by('-created_at')
        ),
        Prefetch(
            'inquirymoderator_set',
            queryset=InquiryModerator.objects.select_related(
                'moderator'
            ).prefetch_related(
                Prefetch(
                    'inquirymoderatormessage_set',
                    queryset=InquiryModeratorMessage.objects.order_by('-created_at')
                )
            )
        )
    ).order_by('-updated_at')

    search_term = request.query_params.get('search', None)
    if search_term is not None:
        queryset = queryset.filter(
            Q(user__username__icontains=search_term) | Q(user__email__icontains=search_term) |
            Q(title__icontains=search_term)
        )

    if kwargs:
        return queryset.filter(**kwargs)
    
    return queryset


def filter_and_fetch_inquiry(**kwargs) -> Inquiry | None:
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
            queryset=InquiryMessage.objects.order_by('-created_at')
        ),
        Prefetch(
            'inquirymoderator_set',
            queryset=InquiryModerator.objects.select_related(
                'moderator'
            ).prefetch_related(
                Prefetch(
                    'inquirymoderatormessage_set',
                    queryset=InquiryModeratorMessage.objects.order_by('-created_at')
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

def create_report_queryset_without_prefetch(
    request, 
    fields_only=[], 
    **kwargs
) -> BaseManager[Report]:
    """
    Create a queryset for the Report model without prefetching and selecting related models.\n
    - request: request object.\n
    - fields_only: list of fields to return in the queryset.\n
    - **kwargs: keyword arguments to filter
    """

    if kwargs is not None:
        queryset = Report.objects.filter(**kwargs)
    else:
        queryset = Report.objects.all()

    search_term = request.query_params.get('search', None)
    if search_term is not None:
        queryset = queryset.filter(
            Q(accused__username__icontains=search_term) | 
            Q(accuser__username__icontains=search_term)
        )

    sort_by : str | None = request.query_params.get('sort', None)
    if sort_by is not None:
        sort_by : List[str] = sort_by.split(',')
        unique_sort_by = set(sort_by)

        for field in unique_sort_by:
            if field not in report_queryset_allowed_order_by_fields:
                unique_sort_by.remove(field)

        sort_by = list(unique_sort_by)

    if sort_by is not None:
        queryset = queryset.order_by(*sort_by)
    else:
        queryset = queryset.order_by('-created_at')

    resolved = request.query_params.get('resolved', None)
    if resolved == '1':
        queryset = queryset.filter(resolved=True)
    elif resolved == '0':
        queryset = queryset.filter(resolved=False)

    if fields_only:
        return queryset.only(*fields_only)

    return queryset

class InquiryService:
    @staticmethod
    def get_inquiry_by_user_id_and_id(user_id: int, inquiry_id) -> Inquiry:
        return filter_and_fetch_inquiry(
            user__id=user_id,
            id=inquiry_id
        )

    @staticmethod
    def get_inquiry_by_id(pk):
        return filter_and_fetch_inquiry(id=pk)
    
    @staticmethod
    def get_inquiry_without_messages(pk):
        return Inquiry.objects.filter(id=pk).select_related(
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
    
    @staticmethod
    def get_all_inquiry_types() -> BaseManager[InquiryType]:
        return InquiryType.objects.prefetch_related(
            Prefetch(
                'inquirytypedisplayname_set',
                queryset=InquiryTypeDisplayName.objects.select_related(
                    'language'
                )
            )
        )
    
class InquiryModeratorService:
    @staticmethod
    def get_inquiries_based_on_recent_updated_at(request):
        return filter_and_fetch_inquiries_in_desc_order_based_on_updated_at(request)
    
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
    def assign_moderator(request, inquiry):
        _, created = InquiryModerator.objects.get_or_create(
            inquiry=inquiry,
            moderator=request.user
        )
        if not created:
            InquiryModerator.objects.filter(
                inquiry=inquiry,
                moderator=request.user
            ).update(in_charge=True)

        inquiry.updated_at = datetime.now(timezone.utc)
        inquiry.save()

    @staticmethod
    def unassign_moderator(request, inquiry):
        InquiryModerator.objects.filter(
            inquiry=inquiry,
            moderator=request.user
        ).update(in_charge=False)
        inquiry.save()

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

class ReportService:
    @staticmethod
    def get_reports(request, **kwargs):
        return create_report_queryset_without_prefetch(
            request, 
            fields_only=[], 
            **kwargs
        ).select_related(
            'type'
        ).prefetch_related(
            Prefetch(
                'type__reporttypedisplayname_set',
                queryset=ReportTypeDisplayName.objects.select_related(
                    'language'
                )
            )
        )
    
    @staticmethod
    def get_report(pk):
        return Report.objects.filter(id=pk).select_related(
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
    def get_report_types():
        return ReportType.objects.prefetch_related(
            Prefetch(
                'reporttypedisplayname_set',
                queryset=ReportTypeDisplayName.objects.select_related(
                    'language'
                )
            )
        )
    
class ReportSerializerService:
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

class PostManagementService:
    @staticmethod
    def get_all_posts():
        return Post.objects.order_by('-created_at').select_related(
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
                )
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
    
class PostManagementSerializerService:
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

class UserManagementService:
    @staticmethod
    def get_user_list(request):
        return create_user_queryset_without_prefetch(
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
    
    @staticmethod
    def get_user(pk) -> User | None:
        user = User.objects.filter(id=pk).select_related(
            'role'
        ).prefetch_related(
            Prefetch(
                'liked_user',
                queryset=UserLike.objects.all()
            ),
            Prefetch(
                'teamlike_set',
                queryset=TeamLike.objects.select_related('team')
            )
        ).first()

    @staticmethod
    def get_user_chats(request, pk):
        return create_userchat_queryset_without_prefetch(
            request,
            fields_only=[],
            userchatparticipant__user__id=pk 
        ).prefetch_related(
            Prefetch(
                'userchatparticipant_set',
                UserChatParticipant.objects.prefetch_related(
                    'userchatparticipantmessage_set',
                ).select_related(
                    'user',
                )
            )
        )

    @staticmethod 
    def get_chat(request, pk, chat_id):
        return UserChat.objects.filter(
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
    
    @staticmethod
    def get_user_posts(request, pk):
        return create_post_queryset_without_prefetch(
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
            user__id=pk
        ).prefetch_related(
            'postlike_set',
            'postcomment_set',
            Prefetch(
                'status__poststatusdisplayname_set',
                queryset=PostStatusDisplayName.objects.select_related(
                    'language'
                )
            ),
        )
    
    @staticmethod
    def get_user_comments(request, pk):
        return create_post_comment_queryset_without_prefetch(
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
    def update_user_favorite_teams(request, pk):
        user = User.objects.filter(id=pk).first()
        if not user:
            return False, {'error': 'User not found'}, HTTP_404_NOT_FOUND

        data = request.data
        if not isinstance(data, list):
            return False, {'error': 'Invalid data'}, HTTP_400_BAD_REQUEST

        if not data:
            TeamLike.objects.filter(user=user).delete()
            return True, None, None

        try:
            team_ids = [team['id'] for team in data]
        except KeyError:
            return False, {'error': 'Invalid data'}, HTTP_400_BAD_REQUEST

        teams = Team.objects.filter(id__in=team_ids)

        if not teams:
            return False, {'error': 'Teams not found'}, HTTP_404_NOT_FOUND

        TeamLike.objects.filter(user=user).delete()
        TeamLike.objects.bulk_create([
            TeamLike(user=user, team=team) for team in teams
        ])

        return True, None, None
    

class UserManagementSerializerService:
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
                'favorite_team'
            ],
            context={
                'team': {
                    'fields': ['id', 'symbol']
                }
            }
        )