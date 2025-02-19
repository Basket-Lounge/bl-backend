from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any
from api.exceptions import AnonymousUserError, BadRequestError, NotFoundError
from management.models import (
    Inquiry, 
    InquiryMessage, 
    InquiryModerator, 
    InquiryModeratorMessage, 
    InquiryTypeDisplayName
)
from teams.models import (
    Post, 
    PostComment, 
    PostCommentLike, 
    PostLike, 
    PostStatusDisplayName, 
    TeamLike, 
    TeamName
)
from users.models import (
    Block,
    User, 
    UserChat,
    UserChatParticipant, 
    UserChatParticipantMessage, 
    UserLike
)

from django.db.models import Q, Exists, OuterRef, Prefetch, Count, F, Subquery
from django.db.models import Value, CharField, DateTimeField, IntegerField
from django.db.models.manager import BaseManager
from django.db.models.query import QuerySet


from rest_framework.request import Request


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
    request: Request,
    fields_only: List[str] = [],
    **kwargs: Any
) -> BaseManager[User]:
    """
    Create a queryset for the User model without prefetching related models.\n

    Args:
        - request: request object.\n
        - fields_only: list of fields to return in the queryset.\n
        - **kwargs: keyword arguments to filter

    Returns:
        - BaseManager[User]: The queryset of the User model.
    """

    roles_filter : str | None = request.query_params.get('roles', None)
    if roles_filter is not None:
        unfiltered_roles_filter = roles_filter.split(',')
        roles_filter = []

        for role in unfiltered_roles_filter:
            if role.isdigit():
                roles_filter.append(int(role))

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
    request: Request,
    fields_only: List[str] = [],
    **kwargs: Any
) -> BaseManager[Post]:
    """
    Create a queryset for the Post model without prefetching related models.\n

    Args:
        - request: request object.\n
        - fields_only: list of fields to return in the queryset.\n
        - **kwargs: keyword arguments to filter
    
    Returns:
        - BaseManager[Post]: The queryset of the Post model.
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
        if 'Qs' in kwargs:
            Qs = kwargs.pop('Qs')
            if not isinstance(Qs, list):
                Qs = [Qs]

            queryset = Post.objects.filter(*Qs, **kwargs)
        else:
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

    return queryset.exclude(
        status__name='deleted',
    )

def create_comment_queryset_without_prefetch_for_user(
    request: Request,
    fields_only: List[str] = [],
    **kwargs: Any
) -> BaseManager[PostComment]:
    """
    Create a queryset for the PostComment model without prefetching related models.\n

    Args:
        - request: request object.\n
        - fields_only: list of fields to return in the queryset.\n
        - **kwargs: keyword arguments to filter

    Returns:
        - BaseManager[PostComment]: The queryset of the PostComment model.
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
    request: Request,
    fields_only: List[str] = [],
    **kwargs: Any
) -> BaseManager[UserChat]:
    """
    Create a queryset for the UserChat model without prefetching related models.\n

    Args:
        - request: request object.\n
        - fields_only: list of fields to return in the queryset.\n
        - **kwargs: keyword arguments to filter
    
    Returns:
        - BaseManager[UserChat]: The queryset of the UserChat model.
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
    request: Request,
    fields_only: List[str] = [],
    **kwargs: Any
) -> BaseManager[Inquiry]:
    """
    Create a queryset for the Inquiry model without prefetching related models.\n

    Args:
        - request: request object.\n
        - fields_only: list of fields to return in the queryset.\n
        - **kwargs: keyword arguments to filter

    Returns:
        - BaseManager[Inquiry]: The queryset of the Inquiry model.
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

class UserService:
    @staticmethod
    def check_user_exists(user_id: int) -> bool:
        """
        Check if a user exists.

        Args:
            - user_id (int): The id of the user.

        Returns:
            - bool: True if the user exists, False otherwise.
        """
        return User.objects.filter(id=user_id).exists()
    
    @staticmethod
    def get_user_with_id_only(user_id: int) -> User | None:
        """
        Get a user with the attribute of "id".

        Args:
            - user_id (int): The id of the user to get.

        Returns:
            - User | None: The user object.
        """
        return User.objects.filter(id=user_id).only('id').first()

    @staticmethod
    def get_user_with_liked_only(user_id: int, requesting_user: User = None) -> User | None:
        """
        Get a user with the attribute of "id" and "liked".

        Args:
            - user_id (int): The id of the user to get.
            - requesting_user (User): The user that is requesting the data.

        Returns:
            - User | None: The user object.
        """

        user = User.objects.filter(id=user_id).only('id')

        if requesting_user is not None:
            user = user.annotate(
                liked=Exists(UserLike.objects.filter(user=requesting_user, liked_user=OuterRef('pk')))
            )

        return user.first()

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
    def get_user_with_liked_by_id(user_id: int, requesting_user: User = None) -> User | None:
        """
        Get a user with the attribute of "id" and "liked".

        Args:
            - user_id (int): The id of the user to get.
            - requesting_user (User): The user that is requesting the data.

        Returns:
            - User | None: The user object.
        """

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

        if not requesting_user is None and requesting_user.is_authenticated:
            user = user.annotate(
                liked=Exists(UserLike.objects.filter(user=requesting_user, liked_user=OuterRef('pk')))
            )

        return user.first()
    
    @staticmethod
    def create_user_like(user: User, user_to_like: User) -> int:
        """
        Create a like for a user

        Args:
            - user (User): The user that is liking 
            - user_to_like (User): The user that is being liked

        Returns:
            - int: The count of likes for the user
        """

        UserLike.objects.get_or_create(user=user, liked_user=user_to_like)
        count = UserLike.objects.filter(liked_user=user_to_like).count()

        return count
    
    @staticmethod
    def delete_user_like(user: User, user_to_unlike: User):
        """
        Delete a like for a user

        Args:
            - user (User): The user that is unliking
            - user_to_unlike (User): The user that is being unliked

        Returns:
            - None
        """

        UserLike.objects.filter(user=user, liked_user=user_to_unlike).delete()

    @staticmethod
    def check_user_blocked(user: User, user_to_check: User) -> bool:
        """
        Check if a user is blocked by another user.

        Args:
            - user (User): The user that is blocking.
            - user_to_check (User): The user that is being checked.

        Returns:
            - bool: True if the user is blocked, False otherwise.
        """
        return Block.objects.filter(user=user, blocked_user=user_to_check).exists()
    
    @staticmethod
    def block_user(user: User, user_to_block: User) -> None:
        """
        Block a user.

        Args:
            - user (User): The user that is blocking.
            - user_to_block (User): The user that is being blocked.

        Returns:
            - None
        """
        Block.objects.get_or_create(user=user, blocked_user=user_to_block)

    @staticmethod
    def unblock_user(user: User, user_to_unblock: User) -> None:
        """
        Unblock a user.

        Args:
            - user (User): The user that is unblocking.
            - user_to_unblock (User): The user that is being unblocked.

        Returns:
            - None
        """
        Block.objects.filter(user=user, blocked_user=user_to_unblock).delete()

    @staticmethod
    def get_user_blocks(user: User) -> BaseManager[Block]:
        """
        Get all blocks of a user.

        Args:
            - user (User): The user that is blocking.

        Returns:
            - BaseManager[Block]: The queryset of the blocks.
        """
        return Block.objects.filter(user=user)

class UserViewService:
    @staticmethod
    def get_user_posts(request: Request, user_id: int) -> BaseManager[Post]:
        """
        Get all posts of a user.

        Args:
            - request (Request): The request object.
            - user_id (int): The id of the user.
        
        Returns:
            - BaseManager[Post]: The queryset of the posts.
        """
        q = Q(status__name='created')
        if request.user.is_authenticated:
            if request.user.id == user_id:
                q = Q(status__name='created') | Q(status__name='hidden')

        teamname_queryset = TeamName.objects.select_related('language')

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
        ).annotate(
            likes_count=Count('postlike'),
            comments_count=Count('postcomment'),
        ).prefetch_related(
            Prefetch(
                'status__poststatusdisplayname_set',
                queryset=PostStatusDisplayName.objects.select_related(
                    'language'
                )
            ),
            Prefetch(
                'team__teamname_set',
                queryset=teamname_queryset
            ),
            Prefetch(
                'user__teamlike_set',
                queryset=TeamLike.objects.select_related('team').prefetch_related(
                    Prefetch(
                        'team__teamname_set',
                        queryset=teamname_queryset
                    )
                )
            )
        ).filter(q)

        if request.user.is_authenticated:
            posts = posts.annotate(
                liked=Exists(PostLike.objects.filter(user=request.user, post=OuterRef('pk')))
            )

        return posts
    
    @staticmethod
    def get_user_comments(request: Request, user_id: int) -> BaseManager[PostComment]:
        """
        Get all comments of a user.

        Args:
            - request (Request): The request object.
            - user_id (int): The id of the user.
        
        Returns:
            - BaseManager[PostComment]: The queryset of the comments.
        """
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
            status__name='created'
        ).annotate(
            likes_count=Count('postcommentlike'),
            replies_count=Count('postcommentreply')
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
    def get_user_chat(requesting_user: User, user_id: int):
        """
        Get a chat between two users.

        Args:
            requesting_user (User): The user that is requesting the chat.
            user_id (int): The id of the user that the chat is with.
        
        Returns:
            UserChat | None
        """
        last_message_subquery = UserChatParticipantMessage.objects.filter(
            sender=OuterRef('id')
        ).order_by('-created_at').values('message')[:1]

        last_message_subquery_created_at = UserChatParticipantMessage.objects.filter(
            sender=OuterRef('id')
        ).order_by('-created_at').values('created_at')[:1]

        unread_messages_count_subquery = UserChatParticipantMessage.objects.filter(
            ~Q(sender__user=OuterRef('user')) &
            Q(created_at__gt=OuterRef('last_read_at'))
        ).values('sender').annotate(
            count=Count('id')
        ).values('count')

        return UserChat.objects.filter(
            userchatparticipant__user=requesting_user,
            userchatparticipant__chat_blocked=False,
            userchatparticipant__user__chat_blocked=False,
        ).filter(
            userchatparticipant__user__id=user_id,
        ).prefetch_related(
            Prefetch(
                'userchatparticipant_set',
                UserChatParticipant.objects.select_related(
                    'user'
                ).annotate(
                    unread_messages_count=Subquery(unread_messages_count_subquery, output_field=CharField()),
                    last_message=Subquery(last_message_subquery, output_field=CharField()),
                    last_message_created_at=Subquery(last_message_subquery_created_at, output_field=DateTimeField())
                ).prefetch_related(
                    Prefetch(
                        'user__teamlike_set',
                        queryset=TeamLike.objects.select_related('team').prefetch_related(
                            Prefetch(
                                'team__teamname_set',
                                queryset=TeamName.objects.select_related('language')
                            )
                        )
                    )
                )
            )
        ).first()
    
    @staticmethod
    def get_chat_by_id(id: str) -> UserChat | None:
        """
        Get a chat by id.

        Args:
            - id (str): The id of the chat.
        
        Returns:
            - UserChat | None: The chat if it exists.
        """
        last_message_subquery = UserChatParticipantMessage.objects.filter(
            sender=OuterRef('id')
        ).order_by('-created_at').values('message')[:1]

        last_message_subquery_created_at = UserChatParticipantMessage.objects.filter(
            sender=OuterRef('id')
        ).order_by('-created_at').values('created_at')[:1]

        unread_messages_count_subquery = UserChatParticipantMessage.objects.filter(
            ~Q(sender__user=OuterRef('user')) &
            Q(created_at__gt=OuterRef('last_read_at'))
        ).values('sender').annotate(
            count=Count('id')
        ).values('count')

        return UserChat.objects.prefetch_related(
            Prefetch(
                'userchatparticipant_set',
                UserChatParticipant.objects.select_related(
                    'user'
                ).annotate(
                    unread_messages_count=Subquery(unread_messages_count_subquery, output_field=IntegerField()),
                    last_message=Subquery(last_message_subquery, output_field=CharField()),
                    last_message_created_at=Subquery(last_message_subquery_created_at, output_field=DateTimeField())
                ).prefetch_related(
                    Prefetch(
                        'user__teamlike_set',
                        queryset=TeamLike.objects.select_related('team').prefetch_related(
                            Prefetch(
                                'team__teamname_set',
                                queryset=TeamName.objects.select_related('language')
                            )
                        )
                    )
                )
            )
        ).filter(
            id=id
        ).first()
    
    @staticmethod
    def get_my_chats_with_request(request: Request) -> BaseManager[UserChat]:
        """
        Get all chats that the user is participating in. The request must be authenticated.

        Args:
            request (Request): The request object.
        
        Returns:
            QuerySet: The queryset of the chats.
        """
        if not request.user.is_authenticated:
            raise AnonymousUserError()
        
        last_message_subquery = UserChatParticipantMessage.objects.filter(
            sender=OuterRef('id')
        ).order_by('-created_at').values('message')[:1]

        last_message_subquery_created_at = UserChatParticipantMessage.objects.filter(
            sender=OuterRef('id')
        ).order_by('-created_at').values('created_at')[:1]

        unread_messages_count_subquery = UserChatParticipantMessage.objects.filter(
            ~Q(sender__user=OuterRef('user')) &
            Q(created_at__gt=OuterRef('last_read_at'))
        ).values('sender').annotate(
            count=Count('id')
        ).values('count')

        return create_userchat_queryset_without_prefetch_for_user(
            request,
            fields_only=[],
            userchatparticipant__user=request.user,
            userchatparticipant__chat_blocked=False,
            userchatparticipant__chat_deleted=False
        ).prefetch_related(
            Prefetch(
                'userchatparticipant_set',
                UserChatParticipant.objects.select_related(
                    'user',
                    'chat'
                ).annotate(
                    unread_messages_count=Subquery(unread_messages_count_subquery, output_field=IntegerField()),
                    last_message=Subquery(last_message_subquery, output_field=CharField()),
                    last_message_created_at=Subquery(last_message_subquery_created_at, output_field=DateTimeField())
                ).prefetch_related(
                    Prefetch(
                        'user__teamlike_set',
                        queryset=TeamLike.objects.select_related('team').prefetch_related(
                            Prefetch(
                                'team__teamname_set',
                                queryset=TeamName.objects.select_related('language')
                            )
                        )
                    )
                )
            )
        )

    @staticmethod
    def get_chat_message(chat_message_id: str) -> UserChatParticipantMessage | None:
        """
        Get a chat message by id.

        Args:
            - chat_message_id (str): The id of the chat message.

        Returns:
            - UserChatParticipantMessage | None: The chat message if it exists.
        """
        return UserChatParticipantMessage.objects.filter(
            id=chat_message_id
        ).select_related(
            'sender__user'
        ).prefetch_related(
            Prefetch(
                'sender__user__teamlike_set',
                queryset=TeamLike.objects.select_related('team').prefetch_related(
                    Prefetch(
                        'team__teamname_set',
                        queryset=TeamName.objects.select_related('language')
                    )
                )
            )
        ).first()

    
    @staticmethod
    def get_chat_messages(chat_id: str, user: User = None) -> BaseManager[UserChatParticipantMessage]:
        """
        Get all active messages in a chat.

        Args:
            chat_id (str): The id of the chat.
            user (User): The user that is requesting the messages.
        
        Returns:
            QuerySet: The queryset of the messages.

        Raises:
            BadRequestError:
              - If the chat is blocked by the user.
            NotFoundError:
              - If the chat is deleted by the user.
        """
        user_participant = UserChatParticipant.objects.filter(
            chat__id=chat_id,
            user=user
        ).first()

        if user_participant is None:
            return None

        if user_participant.chat_blocked:
            raise BadRequestError('A user has blocked the chat.')
        
        if user_participant.chat_deleted:
            raise NotFoundError()
        
        last_deleted_at = user_participant.last_deleted_at 
        last_blocked_at = user_participant.last_blocked_at 

        last_at = None

        if last_deleted_at is not None and last_blocked_at is not None:
            if last_deleted_at > last_blocked_at:
                last_at = last_deleted_at
        elif last_deleted_at is not None:
            last_at = last_deleted_at
        elif last_blocked_at is not None:
            last_at = last_blocked_at

        queryset = UserChatParticipantMessage.objects.filter(
            sender__chat__id=chat_id
        ).select_related(
            'sender__user',
        ).prefetch_related(
            Prefetch(
                'sender__user__teamlike_set',
                queryset=TeamLike.objects.select_related('team').prefetch_related(
                    Prefetch(
                        'team__teamname_set',
                        queryset=TeamName.objects.select_related('language')
                    )
                )
            )
        ).order_by(
            '-created_at'
        ).only(
            'id',
            'message',
            'created_at',
            'updated_at',
            'sender__id',
            'sender__last_deleted_at',
            'sender__last_blocked_at',
            'sender__user__id',
            'sender__user__username',
        )

        if last_at is not None:
            queryset = queryset.filter(
                created_at__gt=last_at
            )

        return queryset
    
    @staticmethod
    def mark_chat_as_read(request: Request, user_id: int) -> UserChat | None:
        """
        Mark a chat as read.

        Args:
            - request (Request): The request object.
            - user_id (int): The id of the user that the chat is with.
        
        Returns:
            - UserChat | None: The chat if it exists.
        """

        user = request.user
        chat = UserChat.objects.filter(
            userchatparticipant__user=user
        ).filter(
            userchatparticipant__user__id=user_id
        ).first()

        if not chat:
            return None

        UserChatParticipant.objects.filter(
            chat=chat,
            user=user
        ).update(last_read_at=datetime.now(timezone.utc))

        return chat

    @staticmethod
    def delete_chat(requesting_user: User, user_id: int) -> None:
        """
        Delete a chat between two users.

        Args:
            - requesting_user (User): The user that is requesting the deletion.
            - user_id (int): The id of the user that the chat is with.
        
        Returns:
            None
        """

        chat = UserChat.objects.filter(
            userchatparticipant__user=requesting_user
        ).filter(
            userchatparticipant__user__id=user_id
        ).first()

        if not chat:
            return

        UserChatParticipant.objects.filter(
            chat=chat,
            user=requesting_user
        ).update(chat_deleted=True, last_deleted_at=datetime.now(timezone.utc))

        UserChatParticipant.objects.filter(
            chat=chat,
            user__id=user_id
        ).update(last_read_at=datetime.now(timezone.utc))


    @staticmethod
    def block_chat(request: Request, user_id: int) -> None:
        """
        Block a chat between two users.

        Args:
            - request (Request): The request object.
            - user_id (int): The id of the user that the chat is with.

        Returns:
            None
        """
        user = request.user
        chat = UserChat.objects.filter(
            userchatparticipant__user=user
        ).filter(
            userchatparticipant__user__id=user_id
        ).first()

        if not chat:
            return

        UserChatParticipant.objects.filter(
            chat=chat,
            user=user
        ).update(
            chat_blocked=True, 
            last_blocked_at=datetime.now(timezone.utc)
        )

        UserChatParticipant.objects.filter(
            chat=chat,
            user__id=user_id
        ).update(last_read_at=datetime.now(timezone.utc))

    @staticmethod
    def enable_chat(request: Request, target_user: User) -> Dict[str, str]:
        """
        Enable a chat between two users after it has been blocked or deleted.

        Args:
            - request (Request): The request object.
            - target_user (User): The user to enable the chat with.

        Returns:
            - Dict[str, str]: The id of the chat.
        """
        if not request.user.is_authenticated:
            raise AnonymousUserError()
        
        if not target_user.is_authenticated:
            raise BadRequestError('User is not authenticated.')
        
        if request.user.id == target_user.id:
            raise BadRequestError('User cannot chat with themselves.')

        chat = UserChat.objects.filter(
            userchatparticipant__user=request.user
        ).filter(
            userchatparticipant__user=target_user
        ).first()
        
        if chat:
            participants = UserChatParticipant.objects.filter(
                chat=chat,
            )

            user_participant = participants.filter(user=request.user).first()
            target_participant = participants.filter(user=target_user).first()

            # If the chat is blocked by a user that is not the current user, then return 400
            if target_user.chat_blocked or target_participant.chat_blocked:
                raise BadRequestError('Chat is blocked by the other user.')
            
            if user_participant.chat_blocked:
                user_participant.chat_blocked = False
                user_participant.last_blocked_at = datetime.now(timezone.utc)
                user_participant.chat_deleted = False
                user_participant.last_deleted_at = datetime.now(timezone.utc)
                user_participant.last_read_at = datetime.now(timezone.utc)
                user_participant.save()

                return {'id': str(chat.id)}

            if user_participant.chat_deleted:
                user_participant.chat_deleted = False
                user_participant.last_deleted_at = datetime.now(timezone.utc)
                user_participant.last_read_at = datetime.now(timezone.utc)
                user_participant.save()

                return {'id': str(chat.id)}

            raise BadRequestError('Chat is already enabled.')

        chat = UserChat.objects.create()
        UserChatParticipant.objects.bulk_create([
            UserChatParticipant(user=request.user, chat=chat),
            UserChatParticipant(user=target_user, chat=chat)
        ])

        return {'id': str(chat.id)}
    
    @staticmethod
    def check_chat_exists(user: User, user_id: int) -> int | None:
        """
        Check if a chat exists between two users.

        Args:
            - user (User): The user that is checking the chat.
            - user_id (int): The id of the user to check the chat with.
        
        Returns:
            - int | None: The id of the chat if it exists.
        """
        chat = UserChat.objects.filter(
            userchatparticipant__user=user
        ).filter(
            userchatparticipant__user__id=user_id
        ).only('id').first()

        return chat.id if chat else None

class InquiryService:
    @staticmethod
    def get_my_inquiries_with_request(request: Request) -> BaseManager[Inquiry]:
        """
        Get all inquiries of the user with the latest message and unread messages count. 
        The request must be authenticated.

        Args:
            - request (Request): The request object.

        Returns:
            - BaseManager[Inquiry]: The queryset of the inquiries.
        """
        if not request.user.is_authenticated:
            raise AnonymousUserError()

        latest_message_subquery = InquiryMessage.objects.filter(
            inquiry=OuterRef('id')
        ).order_by('-created_at').values('message')[:1]

        latest_message_created_at_subquery = InquiryMessage.objects.filter(
            inquiry=OuterRef('id')
        ).order_by('-created_at').values('created_at')[:1]

        unread_messages_count_subquery = Count(
            'inquirymoderator__inquirymoderatormessage',
            filter=Q(inquirymoderator__inquirymoderatormessage__created_at__gt=F('last_read_at'))
        )

        latest_moderator_message_subquery = InquiryModeratorMessage.objects.filter(
            inquiry_moderator__inquiry=OuterRef('inquiry__id')
        ).order_by('-created_at').values('message')[:1]

        latest_moderator_message_created_at_subquery = InquiryModeratorMessage.objects.filter(
            inquiry_moderator__inquiry=OuterRef('inquiry__id')
        ).order_by('-created_at').values('created_at')[:1]

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
                'inquirymoderator_set',
                queryset=InquiryModerator.objects.select_related(
                    'inquiry',
                    'moderator'
                ).annotate(
                    last_message=Subquery(latest_moderator_message_subquery, output_field=CharField()),
                    last_message_created_at=Subquery(latest_moderator_message_created_at_subquery, output_field=DateTimeField()),
                ).prefetch_related(
                    Prefetch(
                        'moderator__teamlike_set',
                        queryset=TeamLike.objects.select_related('team').prefetch_related(
                            Prefetch(
                                'team__teamname_set',
                                queryset=TeamName.objects.select_related('language')
                            )
                        )
                    )
                )
            ),
            Prefetch(
                'user__teamlike_set',
                queryset=TeamLike.objects.select_related('team').prefetch_related(
                    Prefetch(
                        'team__teamname_set',
                        queryset=TeamName.objects.select_related('language')
                    )
                )
            )
        ).annotate(
            last_message=Subquery(latest_message_subquery, output_field=CharField()),
            last_message_created_at=Subquery(latest_message_created_at_subquery, output_field=DateTimeField()),
            unread_messages_count=unread_messages_count_subquery
        ).order_by('-updated_at')
    
    @staticmethod
    def get_inquiry_with_request(request: Request, inquiry_id: str):
        """
        Get an inquiry with the latest message and unread messages count.
        The request must be authenticated.

        Args:
            - request (Request): The request object.
            - inquiry_id (str): The id of the inquiry.
        
        Returns:
            - Inquiry | None: The inquiry object.
        """
        if not request.user.is_authenticated:
            raise AnonymousUserError()

        latest_message_subquery = InquiryMessage.objects.filter(
            inquiry=OuterRef('id')
        ).order_by('-created_at').values('message')[:1]

        latest_message_created_at_subquery = InquiryMessage.objects.filter(
            inquiry=OuterRef('id')
        ).order_by('-created_at').values('created_at')[:1]

        unread_messages_count_subquery = Count(
            'inquirymoderator__inquirymoderatormessage',
            filter=Q(inquirymoderator__inquirymoderatormessage__created_at__gt=F('last_read_at'))
        )

        latest_moderator_message_subquery = InquiryModeratorMessage.objects.filter(
            inquiry_moderator__inquiry=OuterRef('inquiry__id')
        ).order_by('-created_at').values('message')[:1]

        latest_moderator_message_created_at_subquery = InquiryModeratorMessage.objects.filter(
            inquiry_moderator__inquiry=OuterRef('inquiry__id')
        ).order_by('-created_at').values('created_at')[:1]

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
                'inquirymoderator_set',
                queryset=InquiryModerator.objects.select_related(
                    'inquiry',
                    'moderator'
                ).annotate(
                    last_message=Subquery(latest_moderator_message_subquery, output_field=CharField()),
                    last_message_created_at=Subquery(latest_moderator_message_created_at_subquery, output_field=DateTimeField()),
                )
            )
        ).annotate(
            last_message=Subquery(latest_message_subquery, output_field=CharField()),
            last_message_created_at=Subquery(latest_message_created_at_subquery, output_field=DateTimeField()),
            unread_messages_count=unread_messages_count_subquery
        ).first()

    @staticmethod
    def get_inquiry_by_id(inquiry_id: str) -> Inquiry | None:
        """
        Get an inquiry by id.

        Args:
            - inquiry_id (str): The id of the inquiry.

        Returns:
            - Inquiry | None: The inquiry object.
        """
        latest_message_subquery = InquiryMessage.objects.filter(
            inquiry=OuterRef('id')
        ).order_by('-created_at').values('message')[:1]

        latest_message_created_at_subquery = InquiryMessage.objects.filter(
            inquiry=OuterRef('id')
        ).order_by('-created_at').values('created_at')[:1]

        unread_messages_count_subquery = Count(
            'inquirymoderator__inquirymoderatormessage',
            filter=Q(inquirymoderator__inquirymoderatormessage__created_at__gt=F('last_read_at'))
        )

        latest_moderator_message_subquery = InquiryModeratorMessage.objects.filter(
            inquiry_moderator__inquiry=OuterRef('inquiry__id')
        ).order_by('-created_at').values('message')[:1]

        latest_moderator_message_created_at_subquery = InquiryModeratorMessage.objects.filter(
            inquiry_moderator__inquiry=OuterRef('inquiry__id')
        ).order_by('-created_at').values('created_at')[:1]

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
                'inquirymoderator_set',
                queryset=InquiryModerator.objects.select_related(
                    'inquiry',
                    'moderator'
                ).annotate(
                    last_message=Subquery(latest_moderator_message_subquery, output_field=CharField()),
                    last_message_created_at=Subquery(latest_moderator_message_created_at_subquery, output_field=DateTimeField()),
                )
            )
        ).annotate(
            last_message=Subquery(latest_message_subquery, output_field=CharField()),
            last_message_created_at=Subquery(latest_message_created_at_subquery, output_field=DateTimeField()),
            unread_messages_count=unread_messages_count_subquery
        ).first()
    
    @staticmethod
    def get_inquiry_messages(
        inquiry_id: str, 
        datetime_str: str = None
    ) -> Tuple[QuerySet[InquiryMessage, dict[str, Any]], QuerySet[InquiryModeratorMessage, dict[str, Any]]]:
        """
        Retrieve the messages of an inquiry.

        Args:
            - inquiry_id (str): The id of the inquiry.
            - datetime_str (str): The datetime string to filter the messages. Should be in the format of '%Y-%m-%dT%H:%M:%S.%fZ'.
        
        Returns:
            - Tuple[BaseManager[InquiryMessage], BaseManager[InquiryModeratorMessage]]: The queryset of the messages.
        """
        if not inquiry_id:
            raise BadRequestError('Inquiry id is required.')
        
        if datetime_str is not None:
            try:
                datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S.%fZ')
            except ValueError:
                raise BadRequestError('Invalid datetime string.')
        
        messages_qs = InquiryMessage.objects.filter(
            inquiry__id=inquiry_id,
        ).order_by('-created_at').select_related(
            'inquiry__user'
        ).prefetch_related(
            Prefetch(
                'inquiry__user__teamlike_set',
                queryset=TeamLike.objects.select_related('team').prefetch_related(
                    Prefetch(
                        'team__teamname_set',
                        queryset=TeamName.objects.select_related('language')
                    )
                )
            )
        ).annotate(
            user_type=Value('User', output_field=CharField()),
            user_id=F('inquiry__user__id'),
            user_username=F('inquiry__user__username')
        )

        if datetime_str is not None:
            datetime_obj = datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S.%fZ')
            messages_qs = messages_qs.filter(created_at__lt=datetime_obj)

        moderator_messages_qs = InquiryModeratorMessage.objects.filter(
            inquiry_moderator__inquiry__id=inquiry_id,
        ).order_by('-created_at').select_related(
            'inquiry_moderator__moderator'
        ).prefetch_related(
            Prefetch(
                'inquiry_moderator__moderator__teamlike_set',
                queryset=TeamLike.objects.select_related('team').prefetch_related(
                    Prefetch(
                        'team__teamname_set',
                        queryset=TeamName.objects.select_related('language')
                    )
                )
            )
        ).annotate(
            user_type=Value('Moderator', output_field=CharField()),
            user_id=F('inquiry_moderator__moderator__id'),
            user_username=F('inquiry_moderator__moderator__username')
        )

        if datetime_str is not None:
            datetime_obj = datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S.%fZ')
            moderator_messages_qs = moderator_messages_qs.filter(created_at__lt=datetime_obj)

        return messages_qs, moderator_messages_qs

    @staticmethod 
    def check_inquiry_exists(**kwargs: Any) -> bool:
        """
        Check if an inquiry exists.

        Args:
            - **kwargs: The keyword arguments to filter the inquiry.
        
        Returns:
            - bool: True if the inquiry exists.
        """
        return Inquiry.objects.filter(
            **kwargs
        ).exists()
    
    @staticmethod
    def mark_inquiry_as_read(inquiry_id: str) -> None:
        """
        Mark an inquiry as read for the user.

        Args:
            - inquiry_id (str): The id of the inquiry.

        Returns:
            - None
        """
        Inquiry.objects.filter(id=inquiry_id).update(last_read_at=datetime.now(timezone.utc))

    @staticmethod
    def update_updated_at(inquiry_id: str) -> None:
        """
        Update the updated_at field of an inquiry.

        Args:
            - inquiry_id (str): The id of the inquiry.

        Returns:
            - None
        """
        inquiry = Inquiry.objects.get(id=inquiry_id)
        inquiry.save()