"""
Account management tests.
Temporarily imports from root tests.py - to be fully migrated later.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import tests as root_tests
    
    # Re-export test classes
    AccountAction = root_tests.AccountAction
    AccountViewTests = root_tests.AccountViewTests
    AccountManagementURLTests = root_tests.AccountManagementURLTests
except (ImportError, AttributeError):
    pass

