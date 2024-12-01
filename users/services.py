from datetime import datetime, timezone
from typing import List
from api.websocket import send_message_to_centrifuge
from management.models import Inquiry, InquiryMessage, InquiryModerator, InquiryModeratorMessage, InquiryTypeDisplayName
from management.serializers import InquirySerializer
from teams.models import Post, PostComment, PostCommentLike, PostLike, PostStatusDisplayName, TeamLike
from users.models import User, UserChat, UserChatParticipant, UserChatParticipantMessage, UserLike

from django.db.models import Q, Exists, OuterRef, Prefetch

from users.serializers import UserChatParticipantMessageCreateSerializer, UserChatParticipantMessageSerializer, UserChatSerializer, UserSerializer, UserUpdateSerializer


user_queryset_allowed_order_by_fields = (
    'username',
    '-username',
    'email',
    '-email',
    'created_at',
    '-created_at',
)

post_queryset_allowed_order_by_fields = (
    'title',
    '-title',
    'created_at',
    '-created_at',
)

comment_queryset_allowed_order_by_fields = (
    'created_at',
    '-created_at',
    'post__title',
    '-post__title',
)

chat_queryset_allowed_order_by_fields = (
    'userchatparticipant__user__username',
    '-userchatparticipant__user__username',
    'created_at',
    '-created_at',
    'updated_at',
    '-updated_at',
)

inquiry_queryset_allowed_order_by_fields = (
    'title',
    '-title',
    'created_at',
    '-created_at',
)

def create_user_queryset_without_prefetch(
    request, 
    fields_only=[], 
    **kwargs
):
    """
    Create a queryset for the User model without prefetching related models.\n
    - request: request object.\n
    - fields_only: list of fields to return in the queryset.\n
    - **kwargs: keyword arguments to filter
    """

    roles_filter : str | None = request.query_params.get('roles', None)
    if roles_filter is not None:
        roles_filter = roles_filter.split(',')

    sort_by : str | None = request.query_params.get('sort', None)
    if sort_by is not None:
        sort_by : List[str] = sort_by.split(',')
        unique_sort_by = set(sort_by)

        for field in unique_sort_by:
            if field not in user_queryset_allowed_order_by_fields:
                unique_sort_by.remove(field)

        sort_by = list(unique_sort_by)

    search_term = request.query_params.get('search', None)

    if kwargs is not None:
        queryset = User.objects.filter(**kwargs)
    else:
        queryset = User.objects.all()

    if search_term is not None:
        queryset = queryset.filter(
            Q(username__icontains=search_term) | Q(email__icontains=search_term)
        )

    if roles_filter is not None:
        queryset = queryset.filter(role__id__in=roles_filter).distinct()

    if sort_by is not None:
        queryset = queryset.order_by(*sort_by)
    else:
        queryset = queryset.order_by('username')

    if fields_only:
        return queryset.only(*fields_only)

    return queryset

def create_post_queryset_without_prefetch_for_user(
    request,
    fields_only=[],
    **kwargs
):
    """
    Create a queryset for the Post model without prefetching related models.\n
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

    search_term = request.query_params.get('search', None)

    if kwargs is not None:
        queryset = Post.objects.filter(**kwargs)
    else:
        queryset = Post.objects.all()

    if search_term is not None:
        queryset = queryset.filter(
            Q(title__icontains=search_term) | Q(content__icontains=search_term)
        )

    if sort_by is not None:
        queryset = queryset.order_by(*sort_by)
    else:
        queryset = queryset.order_by('-created_at')

    if fields_only:
        return queryset.only(*fields_only)

    return queryset.exclude(status__name='deleted')

def create_comment_queryset_without_prefetch_for_user(
    request,
    fields_only=[],
    **kwargs
):
    """
    Create a queryset for the PostComment model without prefetching related models.\n
    - request: request object.\n
    - fields_only: list of fields to return in the queryset.\n
    - **kwargs: keyword arguments to filter
    """

    sort_by : str | None = request.query_params.get('sort', None)
    if sort_by is not None:
        sort_by : List[str] = sort_by.split(',')
        unique_sort_by = set(sort_by)

        for field in unique_sort_by:
            if field not in comment_queryset_allowed_order_by_fields:
                unique_sort_by.remove(field)

        sort_by = list(unique_sort_by)

    search_term = request.query_params.get('search', None)

    if kwargs is not None:
        queryset = PostComment.objects.filter(**kwargs)
    else:
        queryset = PostComment.objects.all()

    if search_term is not None:
        queryset = queryset.filter(
            Q(content__icontains=search_term)
        )

    if sort_by is not None:
        queryset = queryset.order_by(*sort_by)
    else:
        queryset = queryset.order_by('-created_at')

    if fields_only:
        return queryset.only(*fields_only)

    return queryset.exclude(status__name='deleted')

def create_userchat_queryset_without_prefetch_for_user(
    request,
    fields_only=[],
    **kwargs
):
    """
    Create a queryset for the UserChat model without prefetching related models.\n
    - request: request object.\n
    - fields_only: list of fields to return in the queryset.\n
    - **kwargs: keyword arguments to filter
    """

    sort_by : str | None = request.query_params.get('sort', None)
    if sort_by is not None:
        sort_by : List[str] = sort_by.split(',')
        unique_sort_by = set(sort_by)

        for field in unique_sort_by:
            if field not in chat_queryset_allowed_order_by_fields:
                unique_sort_by.remove(field)

        sort_by = list(unique_sort_by)

    search_term = request.query_params.get('search', None)

    if kwargs is not None:
        queryset = UserChat.objects.filter(**kwargs)
    else:
        queryset = UserChat.objects.all()

    if search_term is not None:
        queryset = queryset.filter(
            Q(userchatparticipant__user__username__icontains=search_term)
        )

    if sort_by is not None:
        queryset = queryset.order_by(*sort_by)
    else:
        queryset = queryset.order_by('-updated_at')

    if fields_only:
        return queryset.only(*fields_only)

    return queryset

def create_inquiry_queryset_without_prefetch_for_user(
    request,
    fields_only=[],
    **kwargs
):
    """
    Create a queryset for the Inquiry model without prefetching related models.\n
    - request: request object.\n
    - fields_only: list of fields to return in the queryset.\n
    - **kwargs: keyword arguments to filter
    """

    sort_by : str | None = request.query_params.get('sort', None)
    if sort_by is not None:
        sort_by : List[str] = sort_by.split(',')
        unique_sort_by = set(sort_by)

        for field in unique_sort_by:
            if field not in inquiry_queryset_allowed_order_by_fields:
                unique_sort_by.remove(field)

        sort_by = list(unique_sort_by)

    search_term = request.query_params.get('search', None)

    if kwargs is not None:
        queryset = Inquiry.objects.filter(**kwargs)
    else:
        queryset = Inquiry.objects.all()

    if search_term is not None:
        queryset = queryset.filter(
            Q(title__icontains=search_term)
        )

    if sort_by is not None:
        queryset = queryset.order_by(*sort_by)
    else:
        queryset = queryset.order_by('-updated_at')

    if fields_only:
        return queryset.only(*fields_only)

    return queryset

def send_update_to_all_parties_regarding_chat(
    request,
    recipient_user_id,
    chat_id,
    chat_serializer,
    message_serializer
):
    sender_chat_notification_channel_name = f'users/{request.user.id}/chats/updates'
    send_message_to_centrifuge(
        sender_chat_notification_channel_name,
        chat_serializer.data
    )

    recipient_chat_notification_channel_name = f'users/{recipient_user_id}/chats/updates'
    send_message_to_centrifuge(
        recipient_chat_notification_channel_name,
        chat_serializer.data
    ) 

    chat_channel_name = f'users/chats/{chat_id}'
    send_message_to_centrifuge(
        chat_channel_name, 
        message_serializer.data
    )


def send_update_to_all_parties_regarding_inquiry(
    inquiry: Inquiry,
    user: User,
    message_serializer,
    inquiry_update_serializer
):
    inquiry_channel_name = f'users/inquiries/{inquiry.id}'
    send_message_to_centrifuge(
        inquiry_channel_name,
        message_serializer.data
    )
    
    user_inquiry_notification_channel_name = f'users/{user.id}/inquiries/updates'
    send_message_to_centrifuge(
        user_inquiry_notification_channel_name,
        inquiry_update_serializer.data
    )
    
    for moderator in inquiry.inquirymoderator_set.all():
        moderator_inquiry_notification_channel_name = f'moderators/{moderator.moderator.id}/inquiries/updates'

        inquiry_for_moderators_serializer = InquirySerializer(
            inquiry,
            fields_exclude=['user_data', 'messages'],
            context={
                'user': {
                    'fields': ['id', 'username']
                },
                'inquirytypedisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'inquirymessage': {
                    'fields_exclude': ['inquiry_data', 'user_data']
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
                    'fields': ['id', 'username']
                },
                'inquirymoderatormessage': {
                    'fields_exclude': ['inquiry_moderator_data', 'user_data']
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

        send_message_to_centrifuge(
            moderator_inquiry_notification_channel_name,
            inquiry_for_moderators_serializer.data
        )

class UserService:
    @staticmethod
    def get_user_by_id(user_id):
        return User.objects.filter(id=user_id).select_related(
            'role'
        ).prefetch_related(
            'liked_user',
            Prefetch(
                'teamlike_set',
                queryset=TeamLike.objects.select_related('team')
            )
        ).first()
    

    @staticmethod
    def get_user_with_liked_by_id(request, user_id):
        user = User.objects.select_related('role').only(
            'username', 
            'role', 
            'experience', 
            'introduction', 
            'is_profile_visible', 
            'id', 
            'chat_blocked', 
            'created_at'
        ).prefetch_related(
            'liked_user',
            Prefetch(
                'teamlike_set',
                queryset=TeamLike.objects.select_related('team')
            )
        ).filter(id=user_id)

        if request.user.is_authenticated:
            user = user.annotate(
                liked=Exists(UserLike.objects.filter(user=request.user, liked_user=OuterRef('pk')))
            )

        return user.first()
        
    
    @staticmethod
    def update_user(request, user):
        serializer = UserUpdateSerializer(
            user,
            data=request.data,
            partial=True
        )         
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return serializer

class UserSerializerService:
    @staticmethod
    def serialize_user(user):
        return UserSerializer(
            user,
            fields=(
                'id',
                'username', 
                'email', 
                'role_data',
                'level',
                'introduction', 
                'created_at',
                'is_profile_visible',
                'chat_blocked',
                'likes_count',
                'favorite_team',
            ),
            context={
                'team': {
                    'fields': ['id', 'symbol']
                },
            }
        )
    
    @staticmethod
    def serialize_user_with_liked(user):
        fields = [
            'id',
            'username',
            'role_data',
            'level',
            'introduction',
            'created_at',
            'is_profile_visible',
            'chat_blocked',
            'likes_count',
            'favorite_team',
            'liked'
        ]

        return UserSerializer(
            user,
            fields=fields,
            context={
                'team': {
                    'fields': ['id', 'symbol']
                },
            }
        )

class UserViewService:
    @staticmethod
    def get_user_posts(request, user_id):
        posts = create_post_queryset_without_prefetch_for_user(
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
            user__id=user_id,
            status__name='created'
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

        if request.user.is_authenticated:
            posts = posts.annotate(
                liked=Exists(PostLike.objects.filter(user=request.user, post=OuterRef('pk')))
            )

        return posts
    
    @staticmethod
    def get_user_comments(request, user_id):
        query = create_comment_queryset_without_prefetch_for_user(
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
            user__id=user_id,
        ).prefetch_related(
            'postcommentlike_set',
            'postcommentreply_set',
        ).select_related(
            'user',
            'status',
            'post__team',
            'post__user'
        )

        if request.user.is_authenticated:
            query = query.annotate(
                liked=Exists(PostCommentLike.objects.filter(user=request.user, post_comment=OuterRef('pk')))
            )

        return query
    

class UserChatService:
    @staticmethod
    def get_chat(request, user_id):
        return UserChat.objects.filter(
            userchatparticipant__user=request.user,
            userchatparticipant__chat_blocked=False,
            userchatparticipant__user__chat_blocked=False,
        ).filter(
            userchatparticipant__user__id=user_id,
        ).prefetch_related(
            Prefetch(
                'userchatparticipant_set',
                UserChatParticipant.objects.prefetch_related(
                    Prefetch(
                        'userchatparticipantmessage_set',
                        queryset=UserChatParticipantMessage.objects.order_by('-created_at')
                    ),
                ).select_related(
                    'user',
                )
            )
        ).first()
    
    @staticmethod
    def get_chat_by_id(id):
        return UserChat.objects.prefetch_related(
            Prefetch(
                'userchatparticipant_set',
                UserChatParticipant.objects.prefetch_related(
                    Prefetch(
                        'userchatparticipantmessage_set',
                        queryset=UserChatParticipantMessage.objects.order_by('-created_at')
                    ),
                ).select_related(
                    'user',
                )
            )
        ).filter(
            id=id
        ).first()
    
    @staticmethod
    def get_my_chats(request):
        return create_userchat_queryset_without_prefetch_for_user(
            request,
            fields_only=[],
            userchatparticipant__user=request.user,
            userchatparticipant__chat_blocked=False,
            userchatparticipant__chat_deleted=False
        ).prefetch_related(
            Prefetch(
                'userchatparticipant_set',
                UserChatParticipant.objects.prefetch_related(
                    Prefetch(
                        'userchatparticipantmessage_set',
                        queryset=UserChatParticipantMessage.objects.order_by('created_at')
                    ),
                ).select_related(
                    'user',
                )
            )
        )
    
    @staticmethod
    def create_chat_message(request, user_id):
        chat = UserChat.objects.filter(
            userchatparticipant__user=request.user,
        ).filter(
            userchatparticipant__user__id=user_id,
            userchatparticipant__chat_blocked=False,
            userchatparticipant__user__chat_blocked=False,
        ).first()

        if not chat:
            return None, None

        participants = chat.userchatparticipant_set.all()

        serializer = UserChatParticipantMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save(
            sender=participants.get(user=request.user),
            receiver=participants.get(user__id=user_id)
        )
        chat.updated_at = datetime.now(timezone.utc)
        chat.save()

        return message, chat
    
class UserChatSerializerService:
    @staticmethod
    def serialize_chats(chats):
        return UserChatSerializer(
            chats,
            many=True,
            fields=['id', 'participants'],
            context={
                'userchatparticipant': {
                    'fields': [
                        'user_data', 
                        'last_message', 
                        'unread_messages_count'
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

    @staticmethod
    def serialize_chat(chat: UserChat, user_participant: UserChatParticipant):
        return UserChatSerializer(
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
                'userchatparticipantmessage_extra': {
                    'user_last_deleted_at': {
                        'id': user_participant.id,
                        'last_deleted_at': user_participant.last_deleted_at
                    }
                },
                'user': {
                    'fields': ['id', 'username']
                }
            }
        )

    @staticmethod
    def serialize_chat_for_update(chat : UserChat):
        return UserChatSerializer(
            chat,
            fields=['id', 'participants', 'created_at', 'updated_at'],
            context={
                'userchatparticipant': {
                    'fields': [
                        'user_data', 
                        'last_message', 
                        'unread_messages_count'
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

    @staticmethod
    def serialize_message_for_chat(message : UserChatParticipantMessage):
        return UserChatParticipantMessageSerializer(
            message,
            fields_exclude=['sender_data'],
            context={
                'user': {
                    'fields': ['id', 'username']
                }
            }
        )
    

class InquiryService:
    @staticmethod
    def get_my_inquiries(request):
        return Inquiry.objects.filter(user=request.user).order_by('-created_at').select_related(
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
    
    @staticmethod
    def get_inquiry(request, inquiry_id):
        return Inquiry.objects.filter(
            id=inquiry_id, 
            user=request.user
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
        ).first()

    @staticmethod
    def get_inquiry_by_id(inquiry_id):
        return Inquiry.objects.filter(id=inquiry_id).select_related(
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
        ).first()
    

class InquirySerializerService:
    @staticmethod
    def serialize_inquiries(request, inquiries):
        return InquirySerializer(
            inquiries,
            many=True,
            fields_exclude=[
                'user_data', 
                'unread_messages_count', 
                'messages'
            ],
            context={
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
                        'last_message',
                        'unread_messages_count'
                    ]
                },
                'moderator': {
                    'fields': ['id', 'username']
                },
                'inquirymoderatormessage': {
                    'fields_exclude': ['inquiry_moderator_data', 'user_data']
                },
                'inquirymoderatormessage_extra': {
                    'user_last_read_at': {
                        inquiry.id: {
                            'id': request.user.id, 
                            'last_read_at': inquiry.last_read_at
                        }
                        for inquiry in inquiries
                    }
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

    @staticmethod
    def serialize_inquiry(inquiry):
        return InquirySerializer(
            inquiry,
            fields_exclude=[
                'user_data', 
                'last_message', 
                'unread_messages_count'
            ],
            context={
                'inquirytypedisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'inquirymessage': {
                    'fields_exclude': ['inquiry_data', 'user_data']
                },
                'inquirymoderator': {
                    'fields': ['moderator_data', 'messages']
                },
                'moderator': {
                    'fields': ['id', 'username']
                },
                'inquirymoderatormessage': {
                    'fields_exclude': ['inquiry_moderator_data', 'user_data']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )
    
    @staticmethod
    def serialize_inquiry_for_update(request, inquiry):
        return InquirySerializer(
            inquiry,
            fields_exclude=[
                'user_data', 
                'messages', 
                'unread_messages_count'
            ],
            context={
                'user': {
                    'fields': ['id', 'username']
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
                        'unread_messages_count'
                    ]
                },
                'moderator': {
                    'fields': ['id', 'username']
                },
                'inquirymoderatormessage': {
                    'fields_exclude': ['inquiry_moderator_data', 'user_data']
                },
                'inquirymoderatormessage_extra': {
                    'user_last_read_at': {
                        'id': request.user.id,
                        'last_read_at': inquiry.last_read_at
                    }
                },
                'language': {
                    'fields': ['name']
                }
            }
        )