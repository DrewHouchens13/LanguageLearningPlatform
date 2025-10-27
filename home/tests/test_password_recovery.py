"""
Password reset and username recovery tests.
Temporarily imports from root tests.py - to be fully migrated later.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import tests as root_tests
    
    # Re-export test classes
    ForgotPasswordTests = root_tests.ForgotPasswordTests
    ResetPasswordTests = root_tests.ResetPasswordTests
    ForgotUsernameTests = root_tests.ForgotUsernameTests
except (ImportError, AttributeError):
    pass

