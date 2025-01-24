from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework.status import HTTP_403_FORBIDDEN

from django.utils.translation import gettext_lazy as _


class CustomError(Exception):
    def __init__(self, message, code):
        self.message = message
        self.code = code
    
    def __str__(self):
        return self.message
    
    def __repr__(self):
        return self.message
    
    def __unicode__(self):
        return self.message
    
    def __dict__(self):
        return {
            'message': self.message,
            'code': self.code
        }
    
    def __json__(self):
        return self.__dict__()

class Error400(CustomError):
    def __init__(self, message):
        super().__init__(message, 400)

class Error401(CustomError):
    def __init__(self, message):
        super().__init__(message, 401)

class Error403(CustomError):
    def __init__(self, message):
        super().__init__(message, 403)

class Error404(CustomError):
    def __init__(self, message):
        super().__init__(message, 404)

class Error405(CustomError):
    def __init__(self, message):
        super().__init__(message, 405)

class Error500(CustomError):
    def __init__(self, message):
        super().__init__(message, 500)

# Subclass 400, 401, 403, 404, 405, 500

class BadRequestError(Error400):
    def __init__(self, message = None):
        if message:
            super().__init__(message)
        else:
            super().__init__('Bad request. Please check your request and try again.')

class UnauthorizedError(Error401):
    def __init__(self):
        super().__init__('User is not authorized to access this resource. Please login to access this resource.')

class AnonymousUserError(Error401):
    def __init__(self):
        super().__init__('User is not authenticated. Please login to access this resource.')
    
class ForbiddenError(Error403):
    def __init__(self):
        super().__init__('User does not have permission to access this resource.')

class PrivilegeError(Error403):
    def __init__(self):
        super().__init__('User does not have the required privilege to access this resource.')

class NotFoundError(Error404):
    def __init__(self):
        super().__init__('Resource not found.')

class MethodNotAllowedError(Error405):
    def __init__(self):
        super().__init__('Method not allowed.')

class InternalServerError(Error500):
    def __init__(self):
        super().__init__('Internal server error. Please try again later.')


class ForbiddenResource(AuthenticationFailed):
    status_code = HTTP_403_FORBIDDEN 
    default_detail = _("User does not have permission to access this resource.")
    default_code = "permission_denied"