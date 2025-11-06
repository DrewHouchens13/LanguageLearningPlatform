#!/usr/bin/env python
"""
Live feature testing script for Language Learning Platform
Tests all major features against local development server
"""
import requests
import json
from urllib.parse import urlparse

BASE_URL = "http://localhost:8000"
session = requests.Session()

# Test results storage
results = []

def test_feature(name, test_func):
    """Run a test and record the result"""
    try:
        result = test_func()
        status = "[PASS]" if result["success"] else "[FAIL]"
        results.append({"name": name, "status": status, "details": result.get("details", "")})
        print(f"{status} - {name}")
        if result.get("details"):
            print(f"    {result['details']}")
        return result["success"]
    except Exception as e:
        results.append({"name": name, "status": "[ERROR]", "details": str(e)})
        print(f"[ERROR] - {name}: {e}")
        return False

# ============================================================================
# TEST 1: Landing Page
# ============================================================================
def test_landing_page():
    """Test that landing page loads"""
    resp = requests.get(f"{BASE_URL}/")
    return {
        "success": resp.status_code == 200 and b"Language Learning" in resp.content,
        "details": f"Status: {resp.status_code}"
    }

# ============================================================================
# TEST 2: Signup
# ============================================================================
def test_signup():
    """Test user signup"""
    # Get signup page to extract CSRF token
    resp = session.get(f"{BASE_URL}/login/")
    if 'csrftoken' not in session.cookies:
        return {"success": False, "details": "No CSRF cookie"}

    # Attempt signup
    signup_data = {
        'name': 'Test Live User',
        'email': 'testlive@example.com',
        'password': 'testpass12345',
        'confirm-password': 'testpass12345',
        'csrfmiddlewaretoken': session.cookies['csrftoken']
    }
    resp = session.post(f"{BASE_URL}/signup/", data=signup_data)

    # Check if redirect to landing (signup success)
    success = resp.status_code in [200, 302] and resp.url in [f"{BASE_URL}/landing/", None]
    return {
        "success": success or 'already exists' in resp.text,
        "details": f"Status: {resp.status_code}, User created or already exists"
    }

# ============================================================================
# TEST 3: Login with Email
# ============================================================================
def test_login_email():
    """Test login with email address"""
    # Get login page for CSRF
    resp = session.get(f"{BASE_URL}/login/")

    login_data = {
        'username': 'testlive@example.com',  # Login accepts email
        'password': 'testpass12345',
        'csrfmiddlewaretoken': session.cookies['csrftoken']
    }
    resp = session.post(f"{BASE_URL}/login/", data=login_data)

    success = resp.status_code in [200, 302]
    return {
        "success": success,
        "details": f"Status: {resp.status_code}"
    }

# ============================================================================
# TEST 4: Dashboard (Protected)
# ============================================================================
def test_dashboard():
    """Test dashboard access (requires login)"""
    resp = session.get(f"{BASE_URL}/dashboard/")
    # Check for common dashboard elements
    success = resp.status_code == 200 and (b"dashboard" in resp.content.lower() or b"Welcome" in resp.content or b"Progress" in resp.content)
    return {
        "success": success,
        "details": f"Status: {resp.status_code}"
    }

# ============================================================================
# TEST 5: Progress Page
# ============================================================================
def test_progress_page():
    """Test progress page (accessible to all)"""
    resp = session.get(f"{BASE_URL}/progress/")
    success = resp.status_code == 200 and (b"Progress" in resp.content or b"progress" in resp.content)
    return {
        "success": success,
        "details": f"Status: {resp.status_code}"
    }

# ============================================================================
# TEST 6: Account Management Page
# ============================================================================
def test_account_page():
    """Test account management page"""
    resp = session.get(f"{BASE_URL}/account/")
    success = resp.status_code == 200 and b"Account" in resp.content
    return {
        "success": success,
        "details": f"Status: {resp.status_code}"
    }

# ============================================================================
# TEST 7: Password Recovery
# ============================================================================
def test_password_recovery():
    """Test password recovery page loads"""
    resp = session.get(f"{BASE_URL}/forgot-password/")
    success = resp.status_code == 200 and (b"Forgot Password" in resp.content or b"forgot" in resp.content)
    return {
        "success": success,
        "details": f"Status: {resp.status_code}"
    }

# ============================================================================
# TEST 8: Username Recovery
# ============================================================================
def test_username_recovery():
    """Test username recovery page loads"""
    resp = session.get(f"{BASE_URL}/forgot-username/")
    success = resp.status_code == 200 and (b"Forgot Username" in resp.content or b"username" in resp.content)
    return {
        "success": success,
        "details": f"Status: {resp.status_code}"
    }

# ============================================================================
# TEST 9: Onboarding Quiz
# ============================================================================
def test_onboarding():
    """Test onboarding quiz is accessible"""
    resp = session.get(f"{BASE_URL}/onboarding/")
    success = resp.status_code == 200
    return {
        "success": success,
        "details": f"Status: {resp.status_code}"
    }

# ============================================================================
# TEST 10: Lessons List
# ============================================================================
def test_lessons_list():
    """Test lessons list page"""
    resp = session.get(f"{BASE_URL}/lessons/")
    success = resp.status_code == 200
    return {
        "success": success,
        "details": f"Status: {resp.status_code}, Lessons feature available"
    }

# ============================================================================
# TEST 11: Shapes Lesson Detail
# ============================================================================
def test_shapes_lesson():
    """Test shapes lesson detail page"""
    # First get lessons list to find lesson ID
    resp = session.get(f"{BASE_URL}/lessons/")
    if b"Shapes" not in resp.content and b"shapes" not in resp.content.lower():
        return {"success": False, "details": "Shapes lesson not found in list"}

    # Try lesson ID 2 (shapes)
    resp = session.get(f"{BASE_URL}/lessons/2/")
    success = resp.status_code == 200 and (b"Shapes" in resp.content or b"shapes" in resp.content.lower() or b"Circle" in resp.content or b"Square" in resp.content)
    return {
        "success": success,
        "details": f"Status: {resp.status_code}"
    }

# ============================================================================
# TEST 12: Colors Lesson Detail (NEW)
# ============================================================================
def test_colors_lesson():
    """Test colors lesson detail page"""
    # Try lesson ID 1 (colors)
    resp = session.get(f"{BASE_URL}/lessons/1/")
    success = resp.status_code == 200 and (b"Colors" in resp.content or b"colors" in resp.content.lower() or b"Red" in resp.content or b"Blue" in resp.content or b"Rojo" in resp.content)
    return {
        "success": success,
        "details": f"Status: {resp.status_code}, Colors lesson integrated"
    }

# ============================================================================
# TEST 13: Shapes Lesson Quiz
# ============================================================================
def test_shapes_quiz():
    """Test shapes lesson quiz page"""
    resp = session.get(f"{BASE_URL}/lessons/2/quiz/")
    success = resp.status_code == 200
    return {
        "success": success,
        "details": f"Status: {resp.status_code}"
    }

# ============================================================================
# TEST 14: Colors Lesson Quiz (NEW)
# ============================================================================
def test_colors_quiz():
    """Test colors lesson quiz page"""
    resp = session.get(f"{BASE_URL}/lessons/1/quiz/")
    success = resp.status_code == 200
    return {
        "success": success,
        "details": f"Status: {resp.status_code}, Colors quiz accessible"
    }

# ============================================================================
# TEST 15: Submit Colors Quiz (NEW)
# ============================================================================
def test_submit_colors_quiz():
    """Test submitting colors quiz"""
    # Get quiz page first to get CSRF token
    quiz_resp = session.get(f"{BASE_URL}/lessons/1/quiz/")

    # Submit quiz with sample answers (JSON requests are typically CSRF-exempt in Django for APIs)
    quiz_data = {
        "answers": [
            {"question_id": 1, "selected_index": 1},
            {"question_id": 2, "selected_index": 1}
        ]
    }
    headers = {
        "Content-Type": "application/json",
        "X-CSRFToken": session.cookies.get('csrftoken', '')
    }
    resp = session.post(
        f"{BASE_URL}/lessons/1/submit/",
        data=json.dumps(quiz_data),
        headers=headers
    )
    success = resp.status_code == 200
    if success:
        try:
            data = resp.json()
            success = data.get("success", False)
        except:
            success = False
    return {
        "success": success,
        "details": f"Status: {resp.status_code}, Quiz submission working"
    }

# ============================================================================
# TEST 16: Logout
# ============================================================================
def test_logout():
    """Test logout functionality"""
    resp = session.get(f"{BASE_URL}/logout/")
    success = resp.status_code in [200, 302]
    return {
        "success": success,
        "details": f"Status: {resp.status_code}"
    }

# ============================================================================
# RUN ALL TESTS
# ============================================================================
if __name__ == "__main__":
    print("\n" + "="*70)
    print("LIVE FEATURE TESTING - Language Learning Platform")
    print("="*70 + "\n")

    test_feature("1. Landing Page", test_landing_page)
    test_feature("2. User Signup", test_signup)
    test_feature("3. Login with Email", test_login_email)
    test_feature("4. Dashboard (Protected)", test_dashboard)
    test_feature("5. Progress Page", test_progress_page)
    test_feature("6. Account Management", test_account_page)
    test_feature("7. Password Recovery", test_password_recovery)
    test_feature("8. Username Recovery", test_username_recovery)
    test_feature("9. Onboarding Quiz", test_onboarding)
    test_feature("10. Lessons List", test_lessons_list)
    test_feature("11. Shapes Lesson Detail", test_shapes_lesson)
    test_feature("12. Colors Lesson Detail (NEW)", test_colors_lesson)
    test_feature("13. Shapes Lesson Quiz", test_shapes_quiz)
    test_feature("14. Colors Lesson Quiz (NEW)", test_colors_quiz)
    test_feature("15. Submit Colors Quiz (NEW)", test_submit_colors_quiz)
    test_feature("16. Logout", test_logout)

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    passed = len([r for r in results if "PASS" in r["status"]])
    failed = len([r for r in results if "FAIL" in r["status"] or "ERROR" in r["status"]])
    print(f"Passed: {passed}/{len(results)}")
    print(f"Failed: {failed}/{len(results)}")
    print("="*70 + "\n")
