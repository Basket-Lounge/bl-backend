from api.paginators import CustomPageNumberPagination, NotificationHeaderPageNumberPagination


CONTEXT_HEADER = "header"

def get_notification_pagination_class(context: str = None) -> type[CustomPageNumberPagination]:
    """
    Get the appropriate pagination class based on the context.

    Args:
        context (str): The context of the pagination, either 'notification' or 'default'.

    Returns:
        Pagination class (type): The corresponding pagination class for the given context.

    """
    if context == CONTEXT_HEADER:
        return NotificationHeaderPageNumberPagination

    return CustomPageNumberPagination