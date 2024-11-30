from datetime import datetime, timezone
from typing import List
from management.models import Inquiry, InquiryMessage, InquiryModerator, InquiryModeratorMessage, InquiryTypeDisplayName
from teams.models import Post, PostComment, PostCommentLike, PostLike, PostStatusDisplayName
from users.models import User, UserChat, UserChatParticipant, UserChatParticipantMessage

from django.db.models import Q, Exists, OuterRef, Prefetch

from users.serializers import UserChatParticipantMessageCreateSerializer


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