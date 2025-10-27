"""
Home app test suite - Organized structure.

Test modules:
- test_utils: Shared test helpers and utilities
- test_models: All model tests (core + onboarding)
- test_views: All view tests (authentication, core pages, onboarding)
- test_admin: Admin interface tests
- test_services: Service layer tests (onboarding algorithm)
- test_integration: End-to-end user flow tests

Total: ~110-120 tests with comprehensive coverage
"""

from .test_utils import *  # noqa: F401, F403
from .test_models import *  # noqa: F401, F403
from .test_views import *  # noqa: F401, F403
from .test_admin import *  # noqa: F401, F403
from .test_services import *  # noqa: F401, F403
from .test_integration import *  # noqa: F401, F403
