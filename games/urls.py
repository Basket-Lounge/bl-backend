from games.views import GameViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'games', GameViewSet, basename='game')
urlpatterns = router.urls