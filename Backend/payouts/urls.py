from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PayoutSubmissionViewSet,
    PayoutSubmissionDetailViewSet,
    PayoutReviewLogViewSet
)
from .prop_firm_views import PropFirmViewSet

router = DefaultRouter()
router.register(r'submissions', PayoutSubmissionViewSet, basename='payout-submission')
router.register(r'details', PayoutSubmissionDetailViewSet, basename='payout-detail')
router.register(r'review-logs', PayoutReviewLogViewSet, basename='review-log')
router.register(r'prop-firms', PropFirmViewSet, basename='prop-firm')

urlpatterns = [
    path('', include(router.urls)),
]
