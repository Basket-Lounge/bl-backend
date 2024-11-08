from typing import Tuple

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import Token, AuthUser
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed

from users.models import User


class CookieJWTAccessAuthentication(JWTAuthentication):
    def authenticate(self, request: Request) -> Tuple[AuthUser, Token] | None:
        access_token = request.COOKIES.get(
            settings.SIMPLE_JWT['AUTH_ACCESS_TOKEN_COOKIE'], 
            None
        )
        if not access_token:
            return None

        validated_token = self.get_validated_token(access_token)

        user = self.get_user(validated_token)
        return user, validated_token
    
    def get_user(self, validated_token: Token) -> AuthUser:
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError:
            raise InvalidToken(_("Token contained no recognizable user identification"))
        
        try:
            user = User.objects.select_related('role').get(id=user_id)
        except User.DoesNotExist:
            raise AuthenticationFailed(_("User not found"), code='user_not_found')
        
        if user.role.name in ['deactivated', 'banned']:
            raise AuthenticationFailed(_("User is not active"), code='user_inactive')
        
        return user
    

class CookieJWTAdminAccessAuthentication(JWTAuthentication):
    def authenticate(self, request: Request) -> Tuple[AuthUser, Token] | None:
        access_token = request.COOKIES.get(
            settings.SIMPLE_JWT['AUTH_ACCESS_TOKEN_COOKIE'], 
            None
        )
        if not access_token:
            return None

        validated_token = self.get_validated_token(access_token)

        user = self.get_user(validated_token)
        return user, validated_token
    
    def get_user(self, validated_token: Token) -> AuthUser:
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError:
            raise InvalidToken(_("Token contained no recognizable user identification"))
        
        try:
            user = User.objects.select_related('role').get(id=user_id)
        except User.DoesNotExist:
            raise AuthenticationFailed(_("User not found"), code='user_not_found')
        
        if user.role.weight >= 3:
            raise AuthenticationFailed(_("User is not an admin"), code='user_not_admin')
        
        return user


class CookieJWTRefreshAuthentication(JWTAuthentication):
    def authenticate(self, request: Request) -> Tuple[AuthUser, Token] | None:
        refresh_token = request.COOKIES.get(
            settings.SIMPLE_JWT['AUTH_REFRESH_TOKEN_COOKIE'], 
            None
        )
        if not refresh_token:
            return None

        validated_token = self.get_validated_token(refresh_token)

        user = self.get_user(validated_token)
        return user, validated_token

    def get_user(self, validated_token: Token) -> AuthUser:
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError:
            raise InvalidToken(_("Token contained no recognizable user identification"))
        
        try:
            user = User.objects.select_related('role').get(id=user_id)
        except User.DoesNotExist:
            raise AuthenticationFailed(_("User not found"), code='user_not_found')
        
        if user.role.name in ['deactivated', 'banned']:
            raise AuthenticationFailed(_("User is not active"), code='user_inactive')
        
        return user