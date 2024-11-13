from django.urls import include, path
from games.views import GameViewSet
from management.views import InquiryModeratorViewSet, InquiryViewSet, JWTAdminSubscriptionViewSet
from players.views import PlayersViewSet
from rest_framework.routers import DefaultRouter

from teams.views import TeamViewSet, TeamsPostViewSet
from users.views import JWTViewSet, UserViewSet


router = DefaultRouter()
router.register(r'games', GameViewSet, basename='game')
router.register(r'inquiries', InquiryViewSet, basename='inquiry')
router.register(r'players', PlayersViewSet, basename='player')
router.register(r'teams', TeamViewSet, basename='team')
router.register(r'teams/posts', TeamsPostViewSet, basename='post')
router.register(r'token', JWTViewSet, basename='token')
router.register(r'token/subscription/admin', JWTAdminSubscriptionViewSet, basename='admin_subscription')
router.register(r'users', UserViewSet, basename='user')
router.register(r'admin/inquiries', InquiryModeratorViewSet, basename='admin_inquiry')

urlpatterns = [
    path('', include(router.urls)),
]