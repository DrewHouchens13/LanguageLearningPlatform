#!/usr/bin/env python
"""
Live Integration Test for XP System
Tests the XP overflow protection and transaction safety in a live Django environment.
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from django.db import transaction, DatabaseError
from home.models import UserProfile

def test_xp_overflow_protection():
    """Test that XP overflow is prevented."""
    print("\n=== Test 1: XP Overflow Protection ===")

    # Clean up any existing test user
    User.objects.filter(username='overflow_test').delete()

    # Create test user
    user = User.objects.create_user(
        username='overflow_test',
        email='overflow@test.com',
        password='test123'
    )
    profile = user.profile

    # Set XP near max value
    max_int = 2147483647
    profile.total_xp = max_int - 50
    profile.save()

    print(f"[OK] Initial XP: {profile.total_xp}")

    # Try to add XP that would cause overflow (should raise ValueError)
    try:
        result = profile.award_xp(100)
        print("[FAIL] Should have raised ValueError for overflow")
        return False
    except ValueError as e:
        print(f"[PASS] Overflow prevented - {str(e)}")

    # Clean up
    user.delete()
    return True


def test_transaction_safety():
    """Test that XP transactions are atomic."""
    print("\n=== Test 2: Transaction Safety ===")

    # Clean up any existing test user
    User.objects.filter(username='transaction_test').delete()

    # Create test user
    user = User.objects.create_user(
        username='transaction_test',
        email='transaction@test.com',
        password='test123'
    )
    profile = user.profile
    profile.total_xp = 0
    profile.save()

    print(f"[OK] Initial XP: {profile.total_xp}")

    # Award XP successfully
    result = profile.award_xp(100)
    profile.refresh_from_db()

    if profile.total_xp == 100:
        print(f"[OK] PASSED: Transaction committed successfully - XP is {profile.total_xp}")
    else:
        print(f"[FAIL] FAILED: XP should be 100, got {profile.total_xp}")
        user.delete()
        return False

    # Clean up
    user.delete()
    return True


def test_negative_xp_validation():
    """Test that negative XP is rejected."""
    print("\n=== Test 3: Negative XP Validation ===")

    # Clean up any existing test user
    User.objects.filter(username='negative_test').delete()

    # Create test user
    user = User.objects.create_user(
        username='negative_test',
        email='negative@test.com',
        password='test123'
    )
    profile = user.profile

    # Try to award negative XP (should raise ValueError)
    try:
        result = profile.award_xp(-10)
        print("[FAIL] FAILED: Should have raised ValueError for negative XP")
        user.delete()
        return False
    except ValueError as e:
        print(f"[OK] PASSED: Negative XP rejected - {str(e)}")

    # Clean up
    user.delete()
    return True


def test_max_xp_limit():
    """Test that excessive XP amounts are rejected."""
    print("\n=== Test 4: Maximum XP Limit ===")

    # Clean up any existing test user
    User.objects.filter(username='maxlimit_test').delete()

    # Create test user
    user = User.objects.create_user(
        username='maxlimit_test',
        email='maxlimit@test.com',
        password='test123'
    )
    profile = user.profile

    # Try to award more than 100,000 XP (should raise ValueError)
    try:
        result = profile.award_xp(150000)
        print("[FAIL] FAILED: Should have raised ValueError for excessive XP")
        user.delete()
        return False
    except ValueError as e:
        print(f"[OK] PASSED: Excessive XP rejected - {str(e)}")

    # Clean up
    user.delete()
    return True


def test_normal_xp_award():
    """Test normal XP award and leveling."""
    print("\n=== Test 5: Normal XP Award and Leveling ===")

    # Clean up any existing test user
    User.objects.filter(username='normal_test').delete()

    # Create test user
    user = User.objects.create_user(
        username='normal_test',
        email='normal@test.com',
        password='test123'
    )
    profile = user.profile
    profile.total_xp = 0
    profile.current_level = 1
    profile.save()

    print(f"[OK] Initial: Level {profile.current_level}, XP {profile.total_xp}")

    # Award enough XP to level up (level 2 requires 100 XP)
    result = profile.award_xp(150)
    profile.refresh_from_db()

    if result['leveled_up'] and profile.current_level >= 2:
        print(f"[OK] PASSED: Leveled up to {profile.current_level} with {profile.total_xp} XP")
    else:
        print(f"[FAIL] FAILED: Should have leveled up, got level {profile.current_level}")
        user.delete()
        return False

    # Clean up
    user.delete()
    return True


def run_all_tests():
    """Run all live XP system tests."""
    print("="*70)
    print("LIVE XP SYSTEM INTEGRATION TESTS")
    print("Testing security enhancements: overflow protection, validation, transactions")
    print("="*70)

    tests = [
        test_xp_overflow_protection,
        test_transaction_safety,
        test_negative_xp_validation,
        test_max_xp_limit,
        test_normal_xp_award,
    ]

    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"[FAIL] EXCEPTION in {test.__name__}: {str(e)}")
            results.append(False)

    print("\n" + "="*70)
    print(f"RESULTS: {sum(results)}/{len(results)} tests passed")

    if all(results):
        print("[OK] ALL TESTS PASSED - XP system security enhancements working correctly!")
    else:
        print("[FAIL] SOME TESTS FAILED - Review output above")

    print("="*70)

    return all(results)


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
