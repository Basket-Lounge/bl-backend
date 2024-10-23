import uuid

from rest_framework_simplejwt.tokens import RefreshToken

from django.conf import settings


def next_level(level):
    return round(0.04 * (level ** 3) + 0.8 * (level ** 2) + 2 * level)

def calculate_level(experience):
    '''
    Calculate the level of a user based on their experience
    '''

    level = 0

    while experience >= next_level(level):
        level += 1

    return level - 1

def generate_random_username():
    return str(uuid.uuid4())

def generate_random_email():
    return f"{uuid.uuid4()}@example.com"

def generate_access_token_for_user(user):
    refresh = RefreshToken.for_user(user)
    
    return {
        settings.SIMPLE_JWT.get('AUTH_ACCESS_TOKEN_COOKIE', 'access'): str(refresh.access_token),
        settings.SIMPLE_JWT.get('AUTH_REFRESH_TOKEN_COOKIE', 'refresh'): str(refresh)
    }

def verify_refresh_token_in_str(token):
    try:
        return RefreshToken(token)
    except Exception as e:
        return None