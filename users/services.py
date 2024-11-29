from typing import List
from management.models import Inquiry
from teams.models import Post, PostComment
from users.models import User, UserChat

from django.db.models import Q


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