"""
Django settings for backend project.

Generated by 'django-admin startproject' using Django 5.1.1.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from datetime import timedelta
from pathlib import Path
from environs import Env
from corsheaders.defaults import default_headers
import sys
import os

from celery.schedules import crontab

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
env = Env()
env.read_env()

# Create a .logs directory if it doesn't exist
if not os.path.exists('.logs') and 'test' not in sys.argv:
    os.makedirs('.logs')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str('DJANGO_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

TESTING = 'test' in sys.argv
DEVELOPMENT = os.getenv('DEVELOPMENT', 'False') == 'True'

# Application definition

INSTALLED_APPS = [
    'players.apps.PlayersConfig',
    'teams.apps.TeamsConfig',
    'games.apps.GamesConfig',
    'management.apps.ManagementConfig',
    'api.apps.ApiConfig',
    'users.apps.UsersConfig',
    'notification.apps.NotificationConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django_extensions',
    "corsheaders",
    "debug_toolbar",
    'allauth',
    'allauth.account',
    # 'allauth.headless',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    # 'allauth.socialaccount.providers.microsoft',
    # 'allauth.socialaccount.providers.instagram',
    'rest_framework',
    'rest_framework.authtoken',
    'dj_rest_auth',
    'dj_rest_auth.registration',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = 'backend.urls'

INTERNAL_IPS = [
    "127.0.0.1",
    "localhost",
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'

# Logging settings
if 'test' in sys.argv:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': True,  # Disable all existing loggers
    }
else:
    # Logging settings
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "[{levelname}] - {asctime} {message}",
                "style": "{",
            },
            "verbose_error": {
                "()": "backend.logging.CustomFormatter",
            },
            "simple": {
                "format": "{levelname} {message}",
                "style": "{",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
            "file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": ".logs/debug.log",
                "formatter": "verbose_error",
                "level": "ERROR",
                "when": "midnight",
                "utc": True,
                "backupCount": 30,
            },
        },
        "loggers": {
            "django": {
                "handlers": ["console", "file"],
                "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
                "propagate": False,
            },
            "api": {
                "handlers": ["console", "file"],
                "level": os.getenv("DJANGO_LOG_LEVEL", "DEBUG"),
                "propagate": False,
            },
            "games": {
                "handlers": ["console", "file"],
                "level": os.getenv("DJANGO_LOG_LEVEL", "DEBUG"),
                "propagate": False,
            },
            "management": {
                "handlers": ["console", "file"],
                "level": os.getenv("DJANGO_LOG_LEVEL", "DEBUG"),
                "propagate": False,
            },
            "players": {
                "handlers": ["console", "file"],
                "level": os.getenv("DJANGO_LOG_LEVEL", "DEBUG"),
                "propagate": False,
            },
            "teams": {
                "handlers": ["console", "file"],
                "level": os.getenv("DJANGO_LOG_LEVEL", "DEBUG"),
                "propagate": False,
            },
            "users": {
                "handlers": ["console", "file"],
                "level": os.getenv("DJANGO_LOG_LEVEL", "DEBUG"),
                "propagate": False,
            },
        },
    }


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

if TESTING:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env.str('TEST_DB_NAME'),
            'USER': env.str('TEST_DB_USER'),
            'PASSWORD': env.str('TEST_DB_PASSWORD'),
            'HOST': env.str('TEST_DB_HOST'),
            'PORT': env.str('TEST_DB_PORT'),
        },
    }
elif DEVELOPMENT:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env.str('DB_NAME'),
            'USER': env.str('DB_USER'),
            'PASSWORD': env.str('DB_PASSWORD'),
            'HOST': env.str('DB_HOST'),
            'PORT': env.str('DB_PORT'),
        },
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env.str('DB_NAME'),
            'USER': env.str('DB_USER'),
            'PASSWORD': env.str('DB_PASSWORD'),
            'HOST': env.str('DB_HOST'),
            'PORT': env.str('DB_PORT'),
        },
        'replica1': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env.str('DB_NAME'),
            'USER': env.str('DB_USER'),
            'PASSWORD': env.str('DB_PASSWORD'),
            'HOST': env.str('DB_HOST_REPLICA1'),
            'PORT': env.str('DB_PORT_REPLICA1'),
        },
        'replica2': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env.str('DB_NAME'),
            'USER': env.str('DB_USER'),
            'PASSWORD': env.str('DB_PASSWORD'),
            'HOST': env.str('DB_HOST_REPLICA2'),
            'PORT': env.str('DB_PORT_REPLICA2'),
        }
    }

DATABASE_ROUTERS = [
    "api.database_routers.DBRouter" if not DEVELOPMENT and not TESTING else "api.database_routers.TestDBRouter"
]


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'


# Misc settings
SESSION_COOKIE_SAMESITE = 'None'
SEASON_YEAR = '2024-25'

# CORS settings
FRONTEND_URL = env.str('FRONTEND_URL')

CORS_ALLOWED_ORIGINS = [
    FRONTEND_URL,
]
CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_ALLOW_ALL = False

CORS_ALLOW_HEADERS = [
    *default_headers,
    "time-zone"
]

# Rest framework settings

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'users.authentication.CookieJWTAccessAuthentication',
        'dj_rest_auth.jwt_auth.JWTCookieAuthentication',
    ),
}

REST_AUTH = {
    'USE_JWT': True,
    'JWT_AUTH_COOKIE': 'access_token',
    'JWT_AUTH_REFRESH_COOKIE': 'refresh_token',
    'JWT_AUTH_SECURE': True,
    'JWT_AUTH_SAMESITE': 'None',
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    
    "AUTH_TOKEN_CLASSES": (
        "rest_framework_simplejwt.tokens.AccessToken",
        "rest_framework_simplejwt.tokens.RefreshToken",     
    ),

    'AUTH_ACCESS_TOKEN_COOKIE': 'access_token',  # Cookie name. Enables cookies if value is set.
    'AUTH_REFRESH_TOKEN_COOKIE': 'refresh_token',  # Cookie name. Enables cookies if value is set.
    'AUTH_COOKIE_DOMAIN': None,     # A string like "example.com", or None for standard domain cookie.
    'AUTH_COOKIE_SECURE': True,    # Whether the auth cookies should be secure (https:// only).
    'AUTH_COOKIE_HTTP_ONLY' : True, # Http only cookie flag.It's not fetch by javascript.
    'AUTH_COOKIE_PATH': '/',        # The path of the auth cookie.
    'AUTH_COOKIE_SAMESITE': 'None',  # Whether to set the flag restricting cookie leaks on cross-site requests.
}

SITE_ID = 1

# Allauth settings
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'EMAIL_AUTHENTICATION': True,
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
    },
}

SOCIAL_AUTH_GOOGLE_CALLBACK = FRONTEND_URL + '/login/google/callback/'

SESSION_COOKIE_SECURE = True

## Celery settings
CELERY_BROKER_URL = env.str('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env.str('CELERY_RESULT_BACKEND')

CELERY_BEAT_SCHEDULE = {
    "update_live_game_score": {
        "task": "games.tasks.update_game_score",
        "schedule": crontab(minute="*/1"),
        "options": {"queue": "today_game_update"},
    },
    "update_teams_roster": {
        "task": "teams.tasks.update_teams_roster",
        "schedule": crontab(minute=0, hour=5),
        "options": {"queue": "low_priority"},
    },
    "update_top_10_players": {
        "task": "players.tasks.update_top_10_players",
        "schedule": crontab(minute=0, hour=5),
        "options": {"queue": "low_priority"},
    },
    "update_player_career_stats": {
        "task": "players.tasks.update_player_career_stats",
        "schedule": crontab(minute=0, hour=5),
        "options": {"queue": "low_priority"},
    },
}

## Cache settings
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env.str('REDIS_URL'),
    }
}

## Websocket settings
CENTRIFUGO_URL = env.str('CENTRIFUGO_URL')
CENTRIFUGO_API_KEY = env.str('CENTRIFUGO_API_KEY')