from datetime import datetime, timezone
from typing import List
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

from django.db.models import Prefetch, Q, Count
from django.db.models.manager import BaseManager

from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from teams.models import (
    Post, 
    PostComment, 
    PostLike, 
    PostStatusDisplayName, 
    Team, 
    TeamLike
)
from users.models import User, UserChat, UserChatParticipant, UserLike
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