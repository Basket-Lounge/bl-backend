from base64 import b64decode, b64encode
from django.core.paginator import Paginator
from django.db import connection, transaction
from django.db.utils import OperationalError
from django.utils.functional import cached_property

from django.db.models.manager import BaseManager

from rest_framework.pagination import PageNumberPagination, CursorPagination
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.utils.urls import replace_query_param

from api.exceptions import BadRequestError
from management.models import InquiryMessage
from users.services import InquiryService


class LargeTablePaginator(Paginator):
    """
    Combination of ideas from:
     - https://gist.github.com/safar/3bbf96678f3e479b6cb683083d35cb4d
     - https://medium.com/@hakibenita/optimizing-django-admin-paginator-53c4eb6bfca3
    Overrides the count method of QuerySet objects to avoid timeouts.
    - Try to get the real count limiting the queryset execution time to 150 ms.
    - If count takes longer than 150 ms the database kills the query and raises OperationError. In that case,
    get an estimate instead of actual count when not filtered (this estimate can be stale and hence not fit for
    situations where the count of objects actually matter).
    - If any other exception occured fall back to default behaviour.
    """

    @cached_property
    def count(self):
        """
        Returns an estimated number of objects, across all pages.
        """
        try:
            with transaction.atomic(), connection.cursor() as cursor:
                # Limit to 500 ms
                cursor.execute('SET LOCAL statement_timeout TO 500;')
                return super().count
        except OperationalError:
            pass

        if not self.object_list.query.where:
            try:
                with transaction.atomic(), connection.cursor() as cursor:
                    # Obtain estimated values (only valid with PostgreSQL)
                    cursor.execute(
                        "SELECT reltuples FROM pg_class WHERE relname = %s",
                        [self.object_list.query.model._meta.db_table]
                    )
                    estimate = int(cursor.fetchone()[0])
                    return estimate
            except Exception:
                # If any other exception occurred fall back to default behaviour
                pass
        return super().count
    

class CustomPageNumberPagination(PageNumberPagination):
    django_paginator_class = LargeTablePaginator
    page_size = 10
    page_query_param = 'page'

    def get_paginated_response(self, data):
        # Calculate the first and last page numbers
        first_page = 1
        last_page = self.page.paginator.num_pages

        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'current_page': self.page.number,
            'first_page': first_page,
            'last_page': last_page,
            'results': data
        })


class NotificationHeaderPageNumberPagination(CustomPageNumberPagination):
    page_size = 3
    page_query_param = 'page'
    max_page_size = 3


class CustomCursorPagination(CursorPagination):
    ordering = '-created_at'


class ChatMessageCursorPagination(CustomCursorPagination):
    cursor_query_param = 'cursor'
    page_size = 25


class InquiryMessageCursorPagination:
    cursor_query_param = 'cursor'
    page_size = 25

    def paginate_querysets(
        self, 
        inquiry_id: str,
        request: Request
    ):
        """
        Returns a paginated list of inquiry messages.

        Args:
            inquiry_id (str): The id of the inquiry.
            request (Request): The request object.
        
        Returns:
            list: The paginated list of inquiry messages
        
        Raises:
            BadRequestError: If the cursor is invalid.
        """

        cursor = request.query_params.get(self.cursor_query_param)
        self.base_url = request.build_absolute_uri()
        cursor = self.decode_cursor(request)

        inquiry_messages, inquiry_moderator_messages = InquiryService.get_inquiry_messages(
            inquiry_id, 
            cursor
        )

        inquiry_messages = inquiry_messages[:self.page_size + 1]
        inquiry_moderator_messages = inquiry_moderator_messages[:self.page_size + 1]

        # Sort the messages based on the field 'created_at'
        new_inquiry_messages = []
        for message in inquiry_messages:
            new_inquiry_messages.append(message)
        
        for message in inquiry_moderator_messages:
            new_inquiry_messages.append(message)

        new_inquiry_messages.sort(key=lambda x: x['created_at'], reverse=True)
        new_inquiry_messages = new_inquiry_messages[:self.page_size + 1]
        new_inquiry_messages.reverse()

        # Set the next cursor if there are more results
        self.next_cursor = None
        if len(new_inquiry_messages) > self.page_size:
            next_cursor = new_inquiry_messages[1]['created_at'].strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            new_inquiry_messages = new_inquiry_messages[1:]
            self.next_cursor = self.encode_cursor(next_cursor)

        return new_inquiry_messages
    
    def get_paginated_response(self, data):
        return Response({
            'next': self.next_cursor,
            'results': data
        })

    def decode_cursor(self, request: Request):
        # Determine if we have a cursor, and if so then decode it.
        encoded = request.query_params.get(self.cursor_query_param)
        if encoded is None:
            return None

        try:
            querystring = b64decode(encoded.encode('ascii')).decode('ascii')
        except:
            raise BadRequestError('Invalid cursor.')

        return querystring

    def encode_cursor(self, cursor: str):
        encoded = b64encode(cursor.encode('ascii')).decode('ascii')
        return replace_query_param(self.base_url, self.cursor_query_param, encoded)