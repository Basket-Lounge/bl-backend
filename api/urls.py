from django.urls import include, path
from games.views import GameViewSet
from management.views import (
    GameManagementViewSet,
    InquiryModeratorViewSet, 
    InquiryViewSet, 
    JWTAdminSubscriptionViewSet, 
    PostManagementViewSet, 
    ReportAdminViewSet, 
    ReportViewSet, 
    UserManagementViewSet
)
from notification.views import NotificationViewSet
from players.views import PlayersViewSet
from rest_framework.routers import DefaultRouter

from teams.views import TeamViewSet, TeamsPostViewSet
from users.views import JWTViewSet, UserViewSet


router = DefaultRouter()
router.register(r'games', GameViewSet, basename='game')
router.register(r'inquiries', InquiryViewSet, basename='inquiry')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'players', PlayersViewSet, basename='player')
router.register(r'teams', TeamViewSet, basename='team')
router.register(r'teams/posts', TeamsPostViewSet, basename='post')
router.register(r'token', JWTViewSet, basename='token')
router.register(r'token/subscription/admin', JWTAdminSubscriptionViewSet, basename='admin_subscription')
router.register(r'users', UserViewSet, basename='user')
router.register(r'admin/inquiries', InquiryModeratorViewSet, basename='admin_inquiry')
router.register(r'admin/reports', ReportAdminViewSet, basename='admin_report')
router.register(r'admin/users', UserManagementViewSet, basename='admin_user')
router.register(r'admin/posts', PostManagementViewSet, basename='admin_post')
router.register(r'admin/games', GameManagementViewSet, basename='admin_game')

urlpatterns = [
    path('', include(router.urls)),
]