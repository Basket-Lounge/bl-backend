from django.core.paginator import Paginator
from django.db import connection, transaction
from django.db.utils import OperationalError
from django.utils.functional import cached_property

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


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