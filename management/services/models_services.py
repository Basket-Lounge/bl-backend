from datetime import datetime, timezone
from typing import List, Union
import uuid

from django.db import IntegrityError
from api.exceptions import BadRequestError
from games.models import Game, GameChat, GameChatBan, GameChatMute
from management.models import (
    Inquiry, 
    InquiryMessage, 
    InquiryModerator, 
    InquiryModeratorMessage, 
    InquiryType, 
    InquiryTypeDisplayName, 
    Report, 
    ReportType, 
    ReportTypeDisplayName
)

from django.db.models import Prefetch, Q, Count, OuterRef, F, Subquery, Value
from django.db.models.manager import BaseManager
from django.db.models.fields import CharField, DateTimeField, IntegerField
from django.db.models.expressions import Window
from django.db.models.functions import RowNumber

from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST
from rest_framework.request import Request

from teams.models import (
    Post, 
    PostComment, 
    PostLike, 
    PostStatusDisplayName, 
    Team, 
    TeamLike,
    TeamName
)
from users.models import Block, User, UserChat, UserChatParticipant, UserLike
from users.services.models_services import create_user_queryset_without_prefetch

from django_cte import With

def test_django_cte():
    item = Inquiry.objects.annotate(
        row_number=Window(
            expression=RowNumber(),
            partition_by=[F('user_id')],
            order_by=F('created_at').desc()
        ),
        last_message=Subquery(
            InquiryMessage.objects.annotate(
                row_number=Window(
                    expression=RowNumber(),
                    partition_by=[F('inquiry_id')],
                    order_by=F('created_at').desc()
                )
            ).filter(row_number=1).values('message')[:1]
        ),
    ).filter(row_number=1).values('id', 'user_id', 'created_at', 'last_message')

    print(item.query)

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

def _filter_and_fetch_inquiries_with_request(request, **kwargs) -> BaseManager[Inquiry]:
    """
    Filter and fetch inquiries in descending order based on the updated_at field and the request query parameters.

    Args:
        - request: request object.
        - **kwargs: keyword arguments to filter

    Returns:
        - BaseManager[Inquiry]: queryset of inquiries
    """
    latest_message_subquery = InquiryMessage.objects.filter(
        inquiry=OuterRef('id')
    ).order_by('-created_at').values('message')[:1]

    latest_message_created_at_subquery = InquiryMessage.objects.filter(
        inquiry=OuterRef('id')
    ).order_by('-created_at').values('created_at')[:1]

    latest_moderator_message_subquery = InquiryModeratorMessage.objects.filter(
        inquiry_moderator__moderator=OuterRef('moderator')
    ).order_by('-created_at').values('message')[:1]

    latest_moderator_message_created_at_subquery = InquiryModeratorMessage.objects.filter(
        inquiry_moderator__moderator=OuterRef('moderator')
    ).order_by('-created_at').values('created_at')[:1]

    unread_other_moderator_messages_count_subquery = InquiryModeratorMessage.objects.filter(
        ~Q(inquiry_moderator__moderator=OuterRef('moderator')),
        created_at__gt=OuterRef('last_read_at')
    ).values('inquiry_moderator').annotate(count=Count('id')).values('count')

    unread_messages_count_subquery = InquiryMessage.objects.filter(
        inquiry__id=OuterRef('inquiry__id'),
        created_at__gt=OuterRef('last_read_at')
    ).values('inquiry').annotate(count=Count('id')).values('count')

    user_teamlike_queryset = TeamLike.objects.select_related('team').prefetch_related(
        Prefetch(
            'team__teamname_set',
            queryset=TeamName.objects.select_related('language')
        )
    )
    
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
            'inquirymoderator_set',
            queryset=InquiryModerator.objects.select_related(
                'inquiry',
                'moderator'
            ).annotate(
                last_message=Subquery(latest_moderator_message_subquery, output_field=CharField()),
                last_message_created_at=Subquery(latest_moderator_message_created_at_subquery, output_field=DateTimeField()),
                unread_other_moderators_messages_count=Subquery(unread_other_moderator_messages_count_subquery, output_field=IntegerField()),
                unread_messages_count=Subquery(unread_messages_count_subquery, output_field=IntegerField())
            ).filter(
                in_charge=True
            ).prefetch_related(
                Prefetch(
                    'moderator__teamlike_set',
                    queryset=user_teamlike_queryset
                )
            )
        )
    ).prefetch_related(
        Prefetch(
            'user__teamlike_set',
            queryset=user_teamlike_queryset
        )
    ).annotate(
        last_message=Subquery(latest_message_subquery, output_field=CharField()),
        last_message_created_at=Subquery(latest_message_created_at_subquery, output_field=DateTimeField()),
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
    """
    Filter and fetch an inquiry based on the keyword arguments.

    Args:
        - **kwargs: keyword arguments to filter
    
    Returns:
        - Inquiry | None: inquiry or None
    """
    latest_message_subquery = InquiryMessage.objects.filter(
        inquiry=OuterRef('id')
    ).order_by('-created_at').values('message')[:1]

    latest_message_created_at_subquery = InquiryMessage.objects.filter(
        inquiry=OuterRef('id')
    ).order_by('-created_at').values('created_at')[:1]

    unread_moderator_messages_count_subquery = Count(
        'inquirymoderator__inquirymoderatormessage',
        filter=Q(inquirymoderator__inquirymoderatormessage__created_at__gt=F('last_read_at'))
    )

    unread_other_moderator_messages_count_subquery = InquiryModeratorMessage.objects.filter(
        ~Q(inquiry_moderator__moderator=OuterRef('moderator')),
        created_at__gt=OuterRef('last_read_at')
    ).values('inquiry_moderator').annotate(count=Count('id')).values('count')

    latest_moderator_message_subquery = InquiryModeratorMessage.objects.filter(
        inquiry_moderator__moderator=OuterRef('moderator'),
        inquiry_moderator__inquiry=OuterRef('inquiry__id')
    ).order_by('-created_at').values('message')[:1]

    latest_moderator_message_created_at_subquery = InquiryModeratorMessage.objects.filter(
        inquiry_moderator__moderator=OuterRef('moderator'),
        inquiry_moderator__inquiry=OuterRef('inquiry__id')
    ).order_by('-created_at').values('created_at')[:1]

    unread_messages_count_subquery = InquiryMessage.objects.filter(
        inquiry__id=OuterRef('inquiry__id'),
        created_at__gt=OuterRef('last_read_at')
    ).values('inquiry').annotate(count=Count('id')).values('count')

    user_teamlike_queryset = TeamLike.objects.select_related('team').prefetch_related(
        Prefetch(
            'team__teamname_set',
            queryset=TeamName.objects.select_related('language')
        )
    )

    inquiry = Inquiry.objects.select_related(
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
                unread_messages_count=unread_messages_count_subquery,
                unread_other_moderators_messages_count=Subquery(unread_other_moderator_messages_count_subquery, output_field=IntegerField())
            ).filter(
                in_charge=True
            ).prefetch_related(
                Prefetch(
                    'moderator__teamlike_set',
                    queryset=user_teamlike_queryset
                )
            )
        )
    ).prefetch_related(
        Prefetch(
            'user__teamlike_set',
            queryset=user_teamlike_queryset
        )
    ).annotate(
        last_message=Subquery(latest_message_subquery, output_field=CharField()),
        last_message_created_at=Subquery(latest_message_created_at_subquery, output_field=DateTimeField()),
        unread_messages_count=unread_moderator_messages_count_subquery
    )

    if kwargs:
        return inquiry.filter(**kwargs).first()
    
    return inquiry.first()

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
        unfiltered_status_filter = status_filter.split(',')
        status_filter = []

        for status in unfiltered_status_filter:
            if status.isdigit():
                status_filter.append(int(status))
        
        if status_filter:
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
        unfiltered_status_filter = status_filter.split(',')
        status_filter = []

        for status in unfiltered_status_filter:
            if status.isdigit():
                status_filter.append(int(status))
        
        if status_filter:
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
    def check_inquiry_exists(pk):
        return Inquiry.objects.filter(id=pk).exists()
    
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

    @staticmethod
    def get_inquiry_message(
        inquiry_message_id: str | uuid.UUID
    ) -> Union[InquiryMessage, None]:
        """
        Retrieve an inquiry message by its id.

        Args:
            - inquiry_message_id: id of the inquiry message.
        
        Returns:
            - Union[InquiryMessage, None]: inquiry message or None.
        """
        if not inquiry_message_id:
            raise BadRequestError('Invalid inquiry message id.')
        
        if not isinstance(inquiry_message_id, str) and not isinstance(inquiry_message_id, uuid.UUID):
            raise BadRequestError('inquiry_message_id must be a string.')
        
        return InquiryMessage.objects.filter(
            id=inquiry_message_id
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
        ).first()

    
class InquiryModeratorService:
    @staticmethod
    def get_inquiries_with_request(request: Request, **kwargs: dict) -> BaseManager[Inquiry]:
        """
        Retrieve inquiries with the request query parameters and the keyword arguments.

        Args:
            - request: request object.
            - **kwargs: keyword arguments to filter

        Returns:
            - BaseManager[Inquiry]: queryset of inquiries
        """
        return _filter_and_fetch_inquiries_with_request(request, **kwargs)
    
    @staticmethod
    def check_inquiry_moderator_exists(inquiry_id: str, moderator: User) -> bool:
        """
        Check if an inquiry moderator exists.

        Args:
            - inquiry_id: id of the inquiry.
            - moderator: User object.
        
        Returns:
            - bool: True if the inquiry moderator exists, False otherwise.
        """
        return InquiryModerator.objects.filter(
            inquiry__id=inquiry_id,
            moderator=moderator
        ).exists()
    
    @staticmethod
    def assign_moderator(request: Request, inquiry: Inquiry) -> None:
        """
        Assign a moderator to an inquiry.

        Args:
            - request: request object.
            - inquiry: inquiry object.

        Returns:
            - None
        """
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
    def unassign_moderator(request: Request, inquiry: Inquiry) -> None:
        """
        Unassign a moderator from an inquiry.

        Args:
            - request: request object.
            - inquiry: inquiry object.

        Returns:
            - None
        """
        InquiryModerator.objects.filter(
            inquiry=inquiry,
            moderator=request.user
        ).update(in_charge=False)
        inquiry.save()

    @staticmethod
    def mark_inquiry_as_read(inquiry_id: str, moderator: User) -> None:
        """
        Mark an inquiry as read by a moderator.

        Args:
            - inquiry_id: id of the inquiry.
            - moderator: User object.

        Returns:
            - None
        """
        InquiryModerator.objects.filter(
            inquiry__id=inquiry_id,
            moderator=moderator
        ).update(last_read_at=datetime.now(timezone.utc))

    @staticmethod
    def update_updated_at(inquiry_id: str) -> None:
        """
        Update the updated_at field of an inquiry.

        Args:
            - inquiry_id: id of the inquiry.
        
        Returns:
            - None
        """
        inquiry = Inquiry.objects.get(id=inquiry_id)
        inquiry.save()

    @staticmethod
    def get_inquiry_moderator_message(
        inquiry_moderator_message_id: str | uuid.UUID
    ) -> Union[InquiryModeratorMessage, None]:
        """
        Retrieve an inquiry moderator message by its id.

        Args:
            - inquiry_moderator_message_id: id of the inquiry moderator message.
        
        Returns:
            - Union[InquiryModeratorMessage, None]: inquiry moderator message or None.
        """
        if not inquiry_moderator_message_id:
            raise BadRequestError('Invalid inquiry moderator message id.')
        
        if not isinstance(inquiry_moderator_message_id, str) and not isinstance(inquiry_moderator_message_id, uuid.UUID):
            raise BadRequestError('inquiry_moderator_message_id must be a string.')
        
        return InquiryModeratorMessage.objects.filter(
            id=inquiry_moderator_message_id
        ).select_related(
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
        ).first()


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
    def get_report_types():
        return ReportType.objects.prefetch_related(
            Prefetch(
                'reporttypedisplayname_set',
                queryset=ReportTypeDisplayName.objects.select_related(
                    'language'
                )
            )
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
        return User.objects.filter(id=pk).select_related(
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
        ).select_related(
            'user',
            'status',
            'post__team',
            'post__user'
        ).annotate(
            likes_count=Count('postcommentlike'),
            replies_count=Count('postcommentreply')
        )
    
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
    
class GameManagementService:
    @staticmethod
    def check_game_exists(pk):
        return Game.objects.filter(game_id=pk).exists()

    @staticmethod
    def check_user_is_banned_from_game_chat(
        game_id: str, 
        user_id: int
    ) -> bool:
        return GameChatBan.objects.filter(
            chat__game__game_id=game_id,
            user__id=user_id
        ).exists()
    
    @staticmethod
    def check_user_is_muted_from_game_chat(
        game_id: str, 
        user_id: int
    ) -> bool:
        return GameChatMute.objects.filter(
            chat__game__game_id=game_id,
            user__id=user_id,
            disabled=False,
        ).exists()

    @staticmethod
    def ban_user_from_game_chat(
        game_chat: GameChat,
        user: User,
        reason: str | None
    ) -> None:
        try:
            ban = GameChatBan.objects.create(
                chat=game_chat,
                user=user,
            )

            if reason and type(reason) == str:
                ban.reason = reason
                ban.save()
        except IntegrityError:
            raise BadRequestError('User is already banned from the game chat.')

    @staticmethod
    def unban_user_from_game_chat(
        game_chat: GameChat,
        user: User
    ) -> None:
        GameChatBan.objects.filter(
            chat=game_chat,
            user=user
        ).update(disabled=True)

    @staticmethod
    def mute_game_chat(
        game_chat: GameChat,
        mute_until: datetime | None
    ) -> None:
        game_chat.mute_mode = True
        if (
            mute_until and
            type(mute_until) == datetime and
            mute_until > datetime.now(timezone.utc)
        ):
            game_chat.mute_until = mute_until

        game_chat.save()

    @staticmethod
    def unmute_game_chat(
        game_chat: GameChat
    ) -> None:
        game_chat.mute_mode = False
        game_chat.mute_until = None
        game_chat.save()

    @staticmethod
    def update_mute_mode_game_chat(
        game_chat: GameChat,
        mute_mode: bool,
        mute_until: datetime | None = None
    ) -> None:
        if type(mute_mode) != bool:
            raise BadRequestError('Invalid mute mode value.')
    
        if not type(mute_until) == datetime and mute_until != None:
            raise BadRequestError('Invalid mute until value.')
        
        if mute_until and mute_until < datetime.now(timezone.utc):
            raise BadRequestError('Invalid mute until value.')
        
        game_chat.mute_mode = mute_mode
        game_chat.mute_until = mute_until
        game_chat.save()

    @staticmethod
    def mute_user_from_game_chat(
        game_chat: GameChat,
        user: User,
        reason: str | None,
        mute_until: datetime | None
    ) -> None:
        try:
            mute = GameChatMute.objects.create(
                chat=game_chat,
                user=user,
                mute_until=mute_until
            )
        except IntegrityError:
            raise BadRequestError('User is already muted from the game chat.')
        
        if reason and type(reason) == str:
            mute.reason = reason

        if (
            mute_until and 
            type(mute_until) == datetime and 
            mute_until > datetime.now(timezone.utc)
        ):
            mute.mute_until = mute_until

        mute.save()

    @staticmethod
    def unmute_user_from_game_chat(
        game_chat: GameChat,
        user: User
    ) -> None:
        GameChatMute.objects.filter(
            chat=game_chat,
            user=user
        ).update(disabled=True)

    @staticmethod
    def update_slow_mode(
        game_chat: GameChat,
        slow_mode: bool,
        slow_mode_time: int | None
    ) -> None:
        """
        Update slow mode settings of a game chat.

        Args:
            - game_chat: GameChat object.
            - slow_mode: boolean.
            - slow_mode_time: how many seconds a user has to wait before sending another message.
        
        Returns:
            - None
        """
        if type(slow_mode) != bool:
            raise BadRequestError('Invalid slow mode value.')

        if slow_mode:
            if not type(slow_mode_time) == int or slow_mode_time <= 0:
                raise BadRequestError('Invalid slow mode time.')
        else:
            slow_mode_time = 0

        game_chat.slow_mode = slow_mode
        game_chat.slow_mode_time = slow_mode_time
        game_chat.save()

    @staticmethod
    def get_game_chat_with_id_only(pk: str) -> GameChat | None:
        return GameChat.objects.filter(
            game__game_id=pk
        ).only(
            'id'
        ).first()

    @staticmethod
    def get_game_chat(pk: str) -> GameChat:
        return GameChat.objects.filter(
            game__game_id=pk
        ).select_related(
            'game'
        ).only(
            'game__game_id',
            'game__game_status_id',
            'id',
            'slow_mode',
            'slow_mode_time',
            'mute_until'
        ).first()
    
    @staticmethod
    def get_banned_users(game_id: str) -> BaseManager[GameChatBan]:
        return GameChatBan.objects.filter(
            chat__game__game_id=game_id,
            disabled=False
        ).select_related(
            'user',
            'chat__game',
            'message'
        ).only(
            'user__id',
            'user__username',
            'chat__game__game_id',
            'message__message',
            'message__created_at',
            'message__updated_at',
            'reason',
            'created_at',
        )
    
    @staticmethod
    def get_muted_users(game_id: str) -> BaseManager[GameChatMute]:
        return GameChatMute.objects.filter(
            chat__game__game_id=game_id,
            disabled=False
        ).select_related(
            'user',
            'chat__game'
        ).only(
            'user__id',
            'user__username',
            'chat__game__game_id',
            'message__message',
            'message__created_at',
            'message__updated_at',
            'reason',
            'created_at',
            'mute_until'
        )