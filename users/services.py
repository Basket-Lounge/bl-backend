from datetime import datetime, timezone
from typing import List, Tuple, Any
from api.exceptions import AnonymousUserError, BadRequestError, NotFoundError
from api.websocket import send_message_to_centrifuge
from management.models import (
    Inquiry, 
    InquiryMessage, 
    InquiryModerator, 
    InquiryModeratorMessage, 
    InquiryTypeDisplayName
)
from management.serializers import InquiryCommonMessageSerializer, InquiryMessageCreateSerializer, InquirySerializer
from teams.models import Post, PostComment, PostCommentLike, PostLike, PostStatusDisplayName, TeamLike, TeamName
from users.models import User, UserChat, UserChatParticipant, UserChatParticipantMessage, UserLike

from django.db.models import Q, Exists, OuterRef, Prefetch, Count, F, Subquery
from django.db.models import Value, CharField, DateTimeField, IntegerField
from django.db.models.manager import BaseManager
from django.db.models.query import QuerySet

from users.serializers import (
    PostCommentSerializer, 
    UserChatParticipantMessageCreateSerializer, 
    UserChatParticipantMessageSerializer, 
    UserChatSerializer, 
    UserSerializer, 
    UserUpdateSerializer
)

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
    inquiry_update_serializer: InquirySerializer
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

    ## TODO: Fix this to reflect the changes in both the queryset and the serializer 
    for moderator in inquiry.inquirymoderator_set.all():
        moderator_inquiry_notification_channel_name = f'moderators/{moderator.moderator.id}/inquiries/updates'

        inquiry_for_moderators_serializer = InquirySerializer(
            inquiry,
            fields_exclude=['user_data', 'unread_messages_count'],
            context={
                'user': {
                    'fields': ['id', 'username']
                },
                'inquirytypedisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'inquirymoderator': {
                    'fields': ['moderator_data', 'last_message']
                },
                'moderator': {
                    'fields': ['id', 'username']
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
    def get_user_with_liked_only(user_id: int, requesting_user: User = None) -> User | None:
        """
        Get a user with the attribute of "id" and "liked".

        :param user_id: The id of the user to get.
        :param requesting_user: The user that is requesting the data.
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

        :param user_id: The id of the user to get.
        :param requesting_user: The user that is requesting the data.

        :return: The user object.
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
    def update_user(request, user):
        serializer = UserUpdateSerializer(
            user,
            data=request.data,
            partial=True
        )         
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return serializer
    
    @staticmethod
    def create_user_like(user: User, user_to_like: User) -> int:
        '''
        Create a like for a user

        Args:
        user (User): The user that is liking
        user_to_like (User): The user that is being liked

        Returns:
        count (int): The number of likes
        '''

        UserLike.objects.get_or_create(user=user, liked_user=user_to_like)
        count = UserLike.objects.filter(liked_user=user_to_like).count()

        return count
    
    @staticmethod
    def delete_user_like(user: User, user_to_unlike: User):
        '''
        Delete a like for a user
        '''

        UserLike.objects.filter(user=user, liked_user=user_to_unlike).delete()

class UserSerializerService:
    @staticmethod
    def serialize_user(user: User) -> UserSerializer:
        """
        Serialize a user object with the fields that are allowed to be seen by the owner of the account.

        :param user: The user object to serialize.

        :return: The UserSerializer object. 
        """

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
                'login_notification_enabled'
            ),
            context={
                'team': {
                    'fields': ['id', 'symbol']
                },
            }
        )
    
    @staticmethod
    def serialize_another_user(user: User, requesting_user: User = None) -> UserSerializer:
        """
        Serialize a user object with the fields that are allowed to be seen by another user.

        :param user: The user object to serialize.
        :param requesting_user: The user that is requesting the data.

        :return: The UserSerializer object.
        """

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
        ]

        if requesting_user is not None and requesting_user.is_authenticated:
            fields.append('liked')

        return UserSerializer(
            user,
            fields=fields,
            context={
                'team': {
                    'fields': ['id', 'symbol']
                },
            }
        )
    
    @staticmethod
    def serialize_user_with_id_only(user):
        return UserSerializer(
            user,
            fields=['id', 'likes_count', 'liked']
        )

class UserViewService:
    @staticmethod
    def get_user_posts(request, user_id):
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

        return UserChat.objects.filter(
            userchatparticipant__user=requesting_user,
            userchatparticipant__chat_blocked=False,
            userchatparticipant__user__chat_blocked=False,
        ).filter(
            userchatparticipant__user__id=user_id,
        ).prefetch_related(
            Prefetch(
                'userchatparticipant_set',
                # UserChatParticipant.objects.prefetch_related(
                #     Prefetch(
                #         'userchatparticipantmessage_set',
                #         queryset=UserChatParticipantMessage.objects.order_by('-created_at')
                #     ),
                # ).select_related(
                #     'user',
                # )
                UserChatParticipant.objects.select_related(
                    'user'
                )
            )
        ).first()
    
    @staticmethod
    def get_chat_by_id(id):
        return UserChat.objects.prefetch_related(
            Prefetch(
                'userchatparticipant_set',
                # UserChatParticipant.objects.prefetch_related(
                #     Prefetch(
                #         'userchatparticipantmessage_set',
                #         queryset=UserChatParticipantMessage.objects.order_by('-created_at')
                #     ),
                # ).select_related(
                #     'user',
                # )
                UserChatParticipant.objects.select_related(
                    'user'
                )
            )
        ).filter(
            id=id
        ).first()
    
    @staticmethod
    def get_my_chats_with_request(request: Request):
        """
        Get all chats that the user is participating in. The request must be authenticated.

        Args:
            request (Request): The request object.
        
        Returns:
            QuerySet: The queryset of the chats.
        """

        if not request.user.is_authenticated:
            raise AnonymousUserError()

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
                    'user'
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
    
    @staticmethod
    def get_chat_messages(chat: UserChat, user: User = None) -> BaseManager[UserChatParticipantMessage]:
        """
        Get all active messages in a chat.

        Args:
            chat (UserChat): The chat object.
            user (User): The user that is requesting the messages.
        
        Returns:
            QuerySet: The queryset of the messages.

        Raises:
            BadRequestError:
              - If the chat is blocked by the user.
            NotFoundError:
              - If the chat is deleted by the user.
        """

        user_participant = chat.userchatparticipant_set.filter(user=user).first()
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
            sender__chat=chat
        ).select_related(
            'sender__user',
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
            queryset = queryset.filter(created_at__gt=last_at)

        return queryset
    
    @staticmethod
    def mark_chat_as_read(request, user_id):
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
            user__id=user_id
        ).update(last_read_at=datetime.now(timezone.utc))

        return chat

    @staticmethod
    def delete_chat(requesting_user: User, user_id: int):
        """
        Delete a chat between two users.

        Args:
            requesting_user (User): The user that is requesting the deletion.
            user_id (int): The id of the user that the chat is with.
        
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
    def block_chat(request, user_id):
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
        ).update(
            chat_blocked=True, 
            last_blocked_at=datetime.now(timezone.utc)
        )

        UserChatParticipant.objects.filter(
            chat=chat,
            user__id=user_id
        ).update(last_read_at=datetime.now(timezone.utc))

    @staticmethod
    def enable_chat(request, target_user):
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
                return False, {'error': 'Chat is blocked by the other user.'}, None
            
            if user_participant.chat_blocked:
                user_participant.chat_blocked = False
                user_participant.last_blocked_at = datetime.now(timezone.utc)
                user_participant.chat_deleted = False
                user_participant.last_deleted_at = datetime.now(timezone.utc)
                target_participant.last_read_at = datetime.now(timezone.utc)
                user_participant.save()
                target_participant.save()

                return True, None, {'id': str(chat.id)}

            if user_participant.chat_deleted:
                user_participant.chat_deleted = False
                user_participant.last_deleted_at = datetime.now(timezone.utc)
                target_participant.last_read_at = datetime.now(timezone.utc)
                user_participant.save()
                target_participant.save()

                return True, None, {'id': str(chat.id)}

            return False, {'error': 'Chat is already enabled.'}, None

        chat = UserChat.objects.create()
        UserChatParticipant.objects.bulk_create([
            UserChatParticipant(user=request.user, chat=chat),
            UserChatParticipant(user=target_user, chat=chat)
        ])

        return True, None, {'id': str(chat.id)}

    
class UserChatSerializerService:
    @staticmethod
    def serialize_chats(request, chats):
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
                'userchatparticipantmessage_extra': {
                    'user_id': request.user.id
                },
                'user': {
                    'fields': ['id', 'username']
                }
            }
        )
    
    @staticmethod
    def serialize_chats_without_unread_count(chats):
        return UserChatSerializer(
            chats,
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
                    'fields': ['user_data']
                },
                'user': {
                    'fields': ['id', 'username']
                }
            }
        )
    
    @staticmethod
    def serialize_chat_with_entire_log(chat):
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
    
    @staticmethod
    def serialize_messages_for_chat(messages: BaseManager[UserChatParticipantMessage] | list) -> UserChatParticipantMessageSerializer:
        return UserChatParticipantMessageSerializer(
            messages,
            many=True,
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
                )
            )
        ).annotate(
            last_message=Subquery(latest_message_subquery, output_field=CharField()),
            last_message_created_at=Subquery(latest_message_created_at_subquery, output_field=DateTimeField()),
            unread_messages_count=unread_messages_count_subquery
        )
    
    @staticmethod
    def get_inquiry(request, inquiry_id):
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
    def get_inquiry_by_id(inquiry_id):
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
            inquiry_id (str): The id of the inquiry.
            datetime_str (str): The datetime string to filter the messages. Should be in the format of '%Y-%m-%dT%H:%M:%S.%fZ'.
        
        Returns:
            Tuple[BaseManager[InquiryMessage], BaseManager[InquiryModeratorMessage]]: The queryset of the messages.
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
        ).annotate(
            user_type=Value('User', output_field=CharField()),
            user_id=F('inquiry__user__id'),
            user_username=F('inquiry__user__username')
        ).values(
            'id',
            'message',
            'created_at',
            'updated_at',
            'user_type',
            'user_id',
            'user_username'
        )

        if datetime_str is not None:
            datetime_obj = datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S.%fZ')
            messages_qs = messages_qs.filter(created_at__lt=datetime_obj)
        else:
            messages_qs = messages_qs.filter(
                created_at__lt=datetime.now(timezone.utc)
            )

        moderator_messages_qs = InquiryModeratorMessage.objects.filter(
            inquiry_moderator__inquiry__id=inquiry_id,
        ).order_by('-created_at').select_related(
            'inquiry_moderator__moderator'
        ).annotate(
            user_type=Value('Moderator', output_field=CharField()),
            user_id=F('inquiry_moderator__moderator__id'),
            user_username=F('inquiry_moderator__moderator__username')
        ).values(
            'id',
            'message',
            'created_at',
            'updated_at',
            'user_type',
            'user_id',
            'user_username'
        )

        if datetime_str is not None:
            datetime_obj = datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S.%fZ')
            moderator_messages_qs = moderator_messages_qs.filter(created_at__lt=datetime_obj)
        else:
            moderator_messages_qs = moderator_messages_qs.filter(
                created_at__lt=datetime.now(timezone.utc)
            )

        return messages_qs, moderator_messages_qs

    @staticmethod 
    def check_inquiry_exists(**kwargs):
        return Inquiry.objects.filter(
            **kwargs
        ).exists()
    
    @staticmethod
    def mark_inquiry_as_read(inquiry_id):
        Inquiry.objects.filter(id=inquiry_id).update(last_read_at=datetime.now(timezone.utc))

    @staticmethod
    def update_updated_at(inquiry_id: str):
        inquiry = Inquiry.objects.get(id=inquiry_id)
        inquiry.save()
    

class InquirySerializerService:
    @staticmethod
    def create_inquiry_message(inquiry_id, data: dict[str, str]) -> InquiryMessage:
        if not inquiry_id:
            raise BadRequestError('Inquiry id is required.')
        
        if not "message" in data:
            raise BadRequestError('Message is required.')

        serializer = InquiryMessageCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.save(
            inquiry=inquiry_id
        )

    @staticmethod
    def serialize_inquiries(request, inquiries):
        return InquirySerializer(
            inquiries,
            many=True,
            fields_exclude=[
                'user_data', 
            ],
            context={
                'inquiry': {
                    'fields': ['id']
                },
                'inquirytypedisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'inquirymoderator': {
                    'fields': [
                        'moderator_data', 
                        'last_message',
                    ]
                },
                'moderator': {
                    'fields': ['id', 'username']
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
    def serialize_inquiry_for_update(inquiry):
        return InquirySerializer(
            inquiry,
            fields_exclude=[
                'user_data', 
            ],
            context={
                'user': {
                    'fields': ['id', 'username']
                },
                'inquirytypedisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'inquirymoderator': {
                    'fields': [
                        'moderator_data', 
                        'last_message', 
                    ]
                },
                'moderator': {
                    'fields': ['id', 'username']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )
    
    @staticmethod
    def serialize_inquiry_messages(messages) -> InquiryCommonMessageSerializer:
        return InquiryCommonMessageSerializer(
            messages,
            many=True,
        )
    
class PostCommentSerializerService:
    @staticmethod
    def serialize_comments(request, comments):
        return PostCommentSerializer(
            comments,
            fields_exclude=['liked'] if not request.user.is_authenticated else [],
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
    
    @staticmethod
    def serialize_comments_without_liked(comments):
        return PostCommentSerializer(
            comments,
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