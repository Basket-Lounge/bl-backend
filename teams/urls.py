from teams.views import TeamViewSet, TeamsPostViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'teams', TeamViewSet, basename='team')
router.register(r'teams/posts', TeamsPostViewSet, basename='post')

urlpatterns = router.urls