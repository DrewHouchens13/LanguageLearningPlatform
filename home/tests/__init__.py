"""
Home app test suite - Organized structure.

Test modules:
- test_utils: Shared test helpers and utilities
- test_models: Core model tests (UserProgress, LessonCompletion, QuizResult)
- test_views: Authentication and core page view tests
- test_admin: Admin interface tests
- test_urls: URL routing tests
- test_account: Account management tests
- test_password_recovery: Password/username recovery tests
- test_progress: Progress tracking tests
- test_services: Service layer tests
- test_integration: End-to-end user flow tests
- test_onboarding_models: Onboarding model tests
- test_onboarding_views: Onboarding view tests
- test_onboarding_service: Onboarding service/algorithm tests
- test_onboarding_integration: Onboarding integration tests

Total: ~260+ tests with comprehensive coverage of core features and onboarding
"""

from .test_account import *  # noqa: F401, F403
from .test_admin import *  # noqa: F401, F403
from .test_integration import *  # noqa: F401, F403
from .test_models import *  # noqa: F401, F403
from .test_onboarding_integration import *  # noqa: F401, F403
# Onboarding test modules
from .test_onboarding_models import *  # noqa: F401, F403
from .test_onboarding_service import *  # noqa: F401, F403
from .test_onboarding_views import *  # noqa: F401, F403
from .test_password_recovery import *  # noqa: F401, F403
from .test_progress import *  # noqa: F401, F403
from .test_services import *  # noqa: F401, F403
from .test_urls import *  # noqa: F401, F403
# Core test modules
from .test_utils import *  # noqa: F401, F403
from .test_views import *  # noqa: F401, F403
