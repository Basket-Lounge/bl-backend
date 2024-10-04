from teams.views import TeamsPostViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'teams/posts', TeamsPostViewSet, basename='post')

urlpatterns = router.urls