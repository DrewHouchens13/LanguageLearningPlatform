# Security & Bug Detection Guide

**Language Learning Platform - Security Best Practices**

**Version**: 1.0
**Last Updated**: October 29, 2025
**Status**: Active as of Sprint 3

This document outlines security best practices, vulnerability scanning tools, and bug detection strategies for the Language Learning Platform. All team members must follow these guidelines to ensure application security and reliability.

---

## Table of Contents

1. [Security Principles](#security-principles)
2. [Current Security Implementation](#current-security-implementation)
3. [Security Scanning Tools](#security-scanning-tools)
4. [Common Vulnerabilities](#common-vulnerabilities)
5. [Input Validation](#input-validation)
6. [Authentication & Authorization](#authentication--authorization)
7. [Data Protection](#data-protection)
8. [Logging & Monitoring](#logging--monitoring)
9. [Dependencies & Supply Chain](#dependencies--supply-chain)
10. [Security Testing](#security-testing)
11. [Bug Detection Strategies](#bug-detection-strategies)
12. [Incident Response](#incident-response)
13. [Security Checklist](#security-checklist)
14. [Sprint 3 Implementation Plan](#sprint-3-implementation-plan)

---

## Security Principles

### Core Security Values
1. **Defense in Depth**: Multiple layers of security
2. **Least Privilege**: Minimal necessary access only
3. **Fail Securely**: Errors should not expose sensitive data
4. **Security by Design**: Build security in from the start
5. **Never Trust User Input**: Validate everything
6. **Keep It Simple**: Complex code has more vulnerabilities

### Security Mindset
- **Assume Breach**: Plan for when (not if) security fails
- **Think Like an Attacker**: Consider abuse cases
- **Document Security Decisions**: Explain why you chose certain approaches
- **Stay Updated**: Security landscape constantly evolves

---

## Current Security Implementation

### Implemented Protections (As of October 2025)

#### Authentication Security
- **Rate Limiting**: 5 login attempts per 5 minutes per IP
- **Password Requirements**: Minimum 8 characters, complexity validation
- **Secure Password Reset**: Token-based with 20-minute expiration
- **Session Management**: Automatic re-authentication after password change
- **Generic Error Messages**: Prevents user enumeration

#### Input Validation
- **Character Whitelisting**: Alphanumeric + safe characters only (@._+-)
- **Length Limits**: Max 254 characters for username/email (RFC 5321)
- **Email Validation**: Format checking before account creation
- **Empty Field Validation**: All required inputs checked

#### Network Security
- **IP Address Validation**: Format validation using Python's `ipaddress` module
- **IP Logging**: All authentication events logged with validated IPs
- **Open Redirect Prevention**: `url_has_allowed_host_and_scheme()` validation
- **X-Forwarded-For Handling**: Secure proxy header processing

#### Data Protection
- **HTTPS Only**: Required in production (Render provides automatically)
- **CSRF Protection**: Django's built-in CSRF tokens on all forms
- **SQL Injection Protection**: Django ORM parameterized queries
- **XSS Protection**: Django's automatic HTML escaping + input validation

#### Infrastructure Security
- **Production Cache Validation**: Runtime warning if local memory cache used
- **Email Configuration Validation**: Validates DEFAULT_FROM_EMAIL before sending
- **Email Retry Mechanism**: 3 retries with exponential backoff for reliability
- **Environment Variable Usage**: No secrets in code

#### Testing
- **Security Test Suite**: XSS, SQL injection, unauthorized access tests
- **167 Tests Total**: 93% code coverage
- **CI/CD**: Automated testing on all pushes/PRs

**See CLAUDE.md** for detailed security feature documentation.

---

## Security Scanning Tools

### Recommended Tools for Django/Python

#### 1. Bandit - Python Security Linter
**Purpose**: Static analysis for common security issues in Python code

```bash
# Installation
pip install bandit

# Basic usage
bandit -r home/ config/

# With configuration file
bandit -r home/ config/ -c .bandit

# Generate HTML report
bandit -r home/ config/ -f html -o bandit-report.html

# CI-friendly format
bandit -r home/ config/ -f json -o bandit-report.json
```

**What it detects**:
- Hardcoded passwords or API keys
- Use of insecure functions (e.g., `eval()`, `exec()`)
- SQL injection vulnerabilities
- Weak cryptographic practices
- Shell injection risks
- Insecure deserialization

**Configuration** (.bandit):
```yaml
tests:
  - B201  # flask_debug_true
  - B501  # request_with_no_cert_validation
  - B502  # ssl_with_bad_version
  - B503  # ssl_with_bad_defaults
  - B506  # yaml_load
  - B601  # paramiko_calls
  - B602  # shell_with_shell_equals_true

exclude_dirs:
  - /venv/
  - /migrations/
  - /staticfiles/
```

#### 2. Safety - Dependency Vulnerability Scanner
**Purpose**: Check dependencies for known security vulnerabilities

```bash
# Installation
pip install safety

# Check installed packages
safety check

# Check requirements file
safety check -r requirements.txt

# Generate JSON report
safety check --json > safety-report.json

# Only show vulnerabilities (ignore warnings)
safety check --output bare
```

**What it detects**:
- Known vulnerabilities in dependencies (CVE database)
- Outdated packages with security patches
- Dependencies with security advisories

**Best Practices**:
- Run weekly or on dependency updates
- Integrate into CI pipeline
- Update vulnerable packages immediately
- Use `pip-audit` as alternative/complement

#### 3. pip-audit - Official Python Vulnerability Scanner
**Purpose**: Scan Python dependencies for known vulnerabilities

```bash
# Installation
pip install pip-audit

# Scan current environment
pip-audit

# Scan requirements file
pip-audit -r requirements.txt

# Generate detailed report
pip-audit --desc

# Fix issues automatically
pip-audit --fix
```

**Advantages over Safety**:
- Official Python Packaging Authority tool
- Uses PyPI's vulnerability database
- More up-to-date vulnerability data
- Can suggest fixes

#### 4. Semgrep - Advanced Static Analysis
**Purpose**: Find bugs and enforce code standards

```bash
# Installation
pip install semgrep

# Run with Python ruleset
semgrep --config=p/python

# Django-specific rules
semgrep --config=p/django

# Security-focused scan
semgrep --config=p/security-audit

# Custom rules
semgrep --config=.semgrep.yml home/
```

**What it detects**:
- Security vulnerabilities
- Bug patterns
- Code quality issues
- Framework-specific problems (Django, Flask, etc.)

**Rulesets**:
- `p/python`: General Python issues
- `p/django`: Django-specific vulnerabilities
- `p/security-audit`: Security-focused checks
- `p/owasp-top-ten`: OWASP Top 10 vulnerabilities

#### 5. Django Security Checklist Tool
**Purpose**: Check Django settings against security best practices

```bash
# Installation
pip install django-security-check

# Run checks
python manage.py check --deploy

# Django's built-in security checks
python manage.py check --tag security
```

**What it checks**:
- DEBUG mode in production
- SECRET_KEY configuration
- ALLOWED_HOSTS settings
- HTTPS/SSL configuration
- Session/cookie security
- CSRF settings

#### 6. Trivy - Container & Dependency Scanner
**Purpose**: Comprehensive security scanning for containers and dependencies

```bash
# Installation (if using Docker)
# Download from: https://github.com/aquasecurity/trivy

# Scan filesystem
trivy fs .

# Scan requirements file
trivy fs --security-checks vuln requirements.txt

# Generate report
trivy fs --format json --output trivy-report.json .
```

**What it detects**:
- Dependency vulnerabilities
- Container image vulnerabilities
- Configuration issues
- License compliance issues

#### 7. SQLMap - SQL Injection Testing
**Purpose**: Automated SQL injection detection and exploitation

```bash
# Installation
pip install sqlmap

# Test a URL for SQL injection
sqlmap -u "http://example.com/article?id=1"

# Test with authenticated session
sqlmap -u "http://example.com/article?id=1" --cookie="sessionid=..."
```

**⚠️ WARNING**: Only use on your own applications or with explicit permission!

#### 8. Detect-Secrets - Secret Detection
**Purpose**: Prevent secrets from being committed to Git

```bash
# Installation
pip install detect-secrets

# Scan for secrets
detect-secrets scan

# Create baseline
detect-secrets scan > .secrets.baseline

# Audit found secrets
detect-secrets audit .secrets.baseline
```

**What it detects**:
- API keys
- Passwords
- Private keys
- AWS credentials
- GitHub tokens

---

## Common Vulnerabilities

### OWASP Top 10 (2021) - Django Context

#### 1. Broken Access Control
**Risk**: Users accessing resources they shouldn't

**Prevention**:
```python
# Use Django's permission system
from django.contrib.auth.decorators import login_required, permission_required

@login_required
@permission_required('articles.can_edit', raise_exception=True)
def edit_article(request, article_id):
    article = get_object_or_404(Article, id=article_id)

    # Additional check: user owns the article
    if article.author != request.user and not request.user.is_staff:
        raise PermissionDenied

    # ... edit logic
```

**Testing**:
- Test unauthorized access attempts
- Verify permission checks
- Test horizontal privilege escalation (user A accessing user B's data)

#### 2. Cryptographic Failures
**Risk**: Sensitive data exposed due to weak encryption

**Prevention**:
```python
# Use Django's password hashers (PBKDF2 by default)
from django.contrib.auth.hashers import make_password, check_password

# NEVER store plain text passwords
password_hash = make_password('user_password')

# For sensitive data at rest, use cryptography library
from cryptography.fernet import Fernet

key = Fernet.generate_key()
cipher = Fernet(key)
encrypted = cipher.encrypt(b"sensitive data")
```

**Requirements**:
- Always use HTTPS in production
- Use strong password hashing (Django's default is good)
- Encrypt sensitive data at rest
- Use TLS 1.2+ for connections

#### 3. Injection
**Risk**: Malicious code executed via untrusted input

**Prevention**:
```python
# Django ORM prevents SQL injection
# GOOD
users = User.objects.filter(username=untrusted_input)

# BAD - Never use raw SQL with user input
cursor.execute(f"SELECT * FROM users WHERE username = '{untrusted_input}'")

# If raw SQL necessary, use parameterization
cursor.execute(
    "SELECT * FROM users WHERE username = %s",
    [untrusted_input]
)

# Command injection prevention
# BAD
os.system(f"ls {user_input}")

# GOOD
import subprocess
subprocess.run(['ls', user_input], check=True)  # Shell=False by default
```

**Testing**:
- Test with SQL injection payloads (`' OR '1'='1`)
- Test with command injection (`; rm -rf /`)
- Test with XSS payloads (`<script>alert('XSS')</script>`)

#### 4. Insecure Design
**Risk**: Architectural flaws in security design

**Prevention**:
- Threat modeling during design phase
- Security requirements from start
- Principle of least privilege
- Defense in depth
- Secure defaults

**Example - Rate Limiting**:
```python
# Prevent brute force attacks at design level
def check_rate_limit(request, action, limit=5, period=300):
    """
    Rate limit security control.

    Design decision: Fail closed (deny access when unsure)
    rather than fail open (allow access when unsure).
    """
    cache_key = f"rate_limit:{action}:{get_client_ip(request)}"
    attempts = cache.get(cache_key, 0)

    if attempts >= limit:
        # Fail securely: deny access
        return False, 0, period

    return True, limit - attempts - 1, 0
```

#### 5. Security Misconfiguration
**Risk**: Insecure default configurations

**Prevention**:
```python
# settings.py - Production configuration

# NEVER leave DEBUG=True in production
DEBUG = False

# Use strong SECRET_KEY from environment
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('SECRET_KEY must be set')

# Restrict ALLOWED_HOSTS
ALLOWED_HOSTS = [
    'your-domain.com',
    'www.your-domain.com',
]

# Security headers
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
```

**Check**:
```bash
python manage.py check --deploy
```

#### 6. Vulnerable and Outdated Components
**Risk**: Using libraries with known vulnerabilities

**Prevention**:
```bash
# Regularly update dependencies
pip list --outdated

# Check for vulnerabilities
safety check
pip-audit

# Update vulnerable packages
pip install --upgrade package-name

# Use dependabot or renovate bot for automated updates
```

**Requirements**:
- Update dependencies monthly minimum
- Security patches immediately
- Test after updates
- Pin versions in requirements.txt

#### 7. Identification and Authentication Failures
**Risk**: Weak authentication mechanisms

**Prevention**:
```python
# Implement comprehensive authentication security

# 1. Rate limiting (already implemented)
@ratelimit(key='ip', rate='5/5m', method='POST')
def login_view(request):
    pass

# 2. Strong password requirements
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# 3. Multi-factor authentication (future implementation)
# from django_otp.decorators import otp_required

# 4. Secure password reset
# - Use token-based reset
# - Time-limited tokens (20 minutes)
# - Single use tokens
```

#### 8. Software and Data Integrity Failures
**Risk**: Insecure CI/CD, updates, or deserialization

**Prevention**:
```python
# Never use pickle with untrusted data
# BAD
import pickle
data = pickle.loads(untrusted_data)

# GOOD
import json
data = json.loads(untrusted_data)

# Verify signatures on updates
# Check integrity of dependencies
pip install --require-hashes -r requirements.txt

# Use hash verification in requirements.txt
# package==1.0.0 --hash=sha256:abcd1234...
```

#### 9. Security Logging and Monitoring Failures
**Risk**: Attacks go undetected

**Prevention**:
```python
# Comprehensive security logging (already implemented)
import logging
logger = logging.getLogger(__name__)

# Log all authentication events
logger.info('Successful login: %s from IP: %s', username, ip_address)
logger.warning('Failed login attempt from IP: %s', ip_address)

# Log security-relevant changes
logger.info('Password changed for user: %s from IP: %s', username, ip_address)
logger.warning('Suspicious activity: %s from IP: %s', activity, ip_address)

# Centralized logging (future)
# - Use ELK stack or similar
# - Set up alerts for suspicious patterns
# - Regular log review
```

**Requirements**:
- Log all authentication events (success and failure)
- Log authorization failures
- Log input validation failures
- Log application errors
- Protect logs from tampering
- Regular log review

#### 10. Server-Side Request Forgery (SSRF)
**Risk**: Server makes requests to unintended destinations

**Prevention**:
```python
# Validate URLs before making requests
from urllib.parse import urlparse
import requests

ALLOWED_DOMAINS = ['api.example.com', 'data.example.com']

def fetch_external_data(url):
    """Fetch data from external source with SSRF protection."""
    parsed = urlparse(url)

    # Check protocol
    if parsed.scheme not in ['http', 'https']:
        raise ValueError("Only HTTP/HTTPS allowed")

    # Check domain whitelist
    if parsed.netloc not in ALLOWED_DOMAINS:
        raise ValueError("Domain not in whitelist")

    # Make request
    response = requests.get(url, timeout=5)
    return response.content
```

---

## Input Validation

### Validation Principles
1. **Validate on Server Side**: Never trust client-side validation
2. **Whitelist, Don't Blacklist**: Define what IS allowed
3. **Validate Early**: Check input before processing
4. **Fail Securely**: Reject invalid input
5. **Sanitize Output**: Encode for context (HTML, SQL, etc.)

### Django Form Validation
```python
from django import forms
from django.core.validators import EmailValidator, RegexValidator

class SignupForm(forms.Form):
    """Secure signup form with comprehensive validation."""

    username = forms.CharField(
        max_length=150,
        min_length=3,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9_]+$',
                message='Username can only contain letters, numbers, and underscores'
            )
        ]
    )

    email = forms.EmailField(
        validators=[EmailValidator()]
    )

    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput
    )

    def clean_username(self):
        """Additional validation for username."""
        username = self.cleaned_data['username']

        # Check for reserved names
        reserved = ['admin', 'root', 'system']
        if username.lower() in reserved:
            raise forms.ValidationError('This username is reserved')

        return username
```

### Input Validation Best Practices
```python
def validate_user_input(user_input, field_name):
    """
    Validate and sanitize user input.

    Args:
        user_input: Raw user input string
        field_name: Name of field for error messages

    Returns:
        Cleaned input string

    Raises:
        ValidationError: If input is invalid
    """
    # 1. Strip whitespace
    user_input = user_input.strip()

    # 2. Check if empty
    if not user_input:
        raise ValidationError(f'{field_name} cannot be empty')

    # 3. Check length
    if len(user_input) > 254:
        raise ValidationError(f'{field_name} is too long (max 254 characters)')

    # 4. Whitelist characters
    import re
    if not re.match(r'^[a-zA-Z0-9@._+\-]+$', user_input):
        raise ValidationError(f'{field_name} contains invalid characters')

    return user_input
```

---

## Authentication & Authorization

### Authentication Best Practices
```python
# 1. Use Django's built-in authentication
from django.contrib.auth import authenticate, login, logout

# 2. Implement rate limiting (already done)
# See home/views.py:check_rate_limit()

# 3. Log all authentication events (already done)
logger.info('Successful login: %s from IP: %s', username, ip_address)

# 4. Use secure sessions
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
SESSION_COOKIE_SAMESITE = 'Strict'  # CSRF protection

# 5. Implement password requirements (already done)
AUTH_PASSWORD_VALIDATORS = [...]
```

### Authorization Patterns
```python
# Method 1: Decorator-based
from django.contrib.auth.decorators import login_required, permission_required

@login_required
def protected_view(request):
    pass

@permission_required('app.can_edit', raise_exception=True)
def editor_view(request):
    pass

# Method 2: Object-level permissions
def edit_article(request, article_id):
    article = get_object_or_404(Article, id=article_id)

    # Check ownership
    if article.author != request.user:
        raise PermissionDenied("You can only edit your own articles")

    # ... edit logic

# Method 3: Class-based views
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

class ArticleUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Article
    permission_required = 'articles.change_article'

    def get_queryset(self):
        # Users can only edit their own articles
        return Article.objects.filter(author=self.request.user)
```

---

## Data Protection

### Sensitive Data Handling
```python
# 1. Identify sensitive data
# - Passwords
# - API keys
# - Tokens
# - Personal information (PII)
# - Financial data

# 2. Never log sensitive data
# BAD
logger.info(f'User password: {password}')

# GOOD
logger.info('Password changed for user: %s', username)

# 3. Use environment variables
import os
API_KEY = os.environ.get('API_KEY')

# 4. Encrypt at rest if needed
from cryptography.fernet import Fernet

key = os.environ.get('ENCRYPTION_KEY').encode()
cipher = Fernet(key)
encrypted_data = cipher.encrypt(sensitive_data.encode())

# 5. Use HTTPS for data in transit (always in production)
```

### Database Security
```python
# 1. Use parameterized queries (Django ORM does this)
User.objects.filter(username=user_input)  # Safe

# 2. Limit database permissions
# - Application user should not be database superuser
# - Grant only necessary permissions (SELECT, INSERT, UPDATE, DELETE)
# - No CREATE, DROP, ALTER in production

# 3. Enable database audit logging
# - Track who accessed what data
# - Monitor for suspicious queries
```

---

## Logging & Monitoring

### What to Log
```python
import logging
logger = logging.getLogger(__name__)

# Security Events (MUST LOG)
logger.warning('Failed login attempt from IP: %s', ip_address)
logger.info('Successful login: %s from IP: %s', username, ip_address)
logger.warning('Password reset attempted for email: %s', email)
logger.info('Password changed for user: %s from IP: %s', username, ip_address)
logger.error('Permission denied: %s attempted %s', username, action)

# Application Errors (SHOULD LOG)
logger.error('Database error: %s', exception_type)
logger.warning('Rate limit exceeded from IP: %s', ip_address)
logger.error('Email send failed: %s', exception_type)

# Debug Information (development only)
if settings.DEBUG:
    logger.debug('Processing request from %s', ip_address)
```

### What NOT to Log
```python
# NEVER LOG:
# - Passwords (plaintext or hashed)
# - API keys or tokens
# - Credit card numbers
# - Social security numbers
# - Session IDs
# - CSRF tokens

# BAD
logger.info(f'User {username} logged in with password {password}')

# GOOD
logger.info('User %s logged in from IP %s', username, ip_address)
```

### Log Analysis
- Review logs weekly minimum
- Set up alerts for:
  - Multiple failed login attempts from same IP
  - Login attempts from unusual locations
  - Privilege escalation attempts
  - Unusual access patterns
- Use log aggregation tools (ELK stack, Splunk, etc.)

---

## Dependencies & Supply Chain

### Dependency Management
```bash
# 1. Pin exact versions in requirements.txt
Django==5.2.7
psycopg2-binary==2.9.10

# 2. Regular updates
pip list --outdated

# 3. Security audits
safety check
pip-audit

# 4. Update immediately for security patches
pip install --upgrade package-name

# 5. Review dependency tree
pip install pipdeptree
pipdeptree
```

### Supply Chain Security
```bash
# 1. Verify package integrity
pip install --require-hashes -r requirements.txt

# 2. Use trusted sources only
# - PyPI official repository
# - Verify package authors
# - Check download statistics
# - Review GitHub stars/activity

# 3. Automated dependency updates
# - Use Dependabot (GitHub)
# - Use Renovate Bot
# - Review updates before merging

# 4. License compliance
pip-licenses
```

---

## Security Testing

### Automated Security Tests
```python
# tests/test_security.py

class SecurityTestCase(TestCase):
    """Security-focused test cases."""

    def test_xss_attack_blocked(self):
        """Test XSS payload is escaped."""
        xss_payload = '<script>alert("XSS")</script>'
        response = self.client.post('/comment/', {
            'content': xss_payload
        })
        # Django should escape the script tags
        self.assertNotContains(response, '<script>')
        self.assertContains(response, '&lt;script&gt;')

    def test_sql_injection_blocked(self):
        """Test SQL injection is prevented."""
        sql_payload = "' OR '1'='1"
        # Should not cause error or bypass authentication
        response = self.client.post('/login/', {
            'username': sql_payload,
            'password': 'test'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_unauthorized_access_denied(self):
        """Test non-logged-in user cannot access protected page."""
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_csrf_protection_enforced(self):
        """Test CSRF token required for POST requests."""
        response = self.client.post('/account/', {
            'email': 'new@example.com'
        })
        # Should fail without CSRF token
        self.assertEqual(response.status_code, 403)
```

### Manual Security Testing
```bash
# 1. Use OWASP ZAP for automated scanning
# Download from: https://www.zaproxy.org/

# 2. Test common vulnerabilities
# - SQL injection
# - XSS (reflected, stored, DOM-based)
# - CSRF
# - Authentication bypass
# - Authorization bypass
# - Session management

# 3. Fuzz testing
# Use hypothesis for property-based testing
pip install hypothesis
```

### Penetration Testing
- Conduct annual penetration tests
- Use professional security firms
- Test in staging environment
- Fix vulnerabilities before production deployment

---

## Bug Detection Strategies

### Static Analysis Tools

#### Pylint (already implemented)
```bash
pylint home/ config/ --rcfile=.pylintrc
```
**Catches**: Code quality issues, potential bugs, bad practices

#### Mypy - Type Checking
```bash
pip install mypy
mypy home/ config/
```
**Catches**: Type errors, inconsistent return types, incorrect function calls

#### Pyflakes - Lightweight Static Analysis
```bash
pip install pyflakes
pyflakes home/
```
**Catches**: Unused imports, undefined names, syntax errors

### Dynamic Analysis

#### Coverage.py - Code Coverage
```bash
pytest --cov=. --cov-report=html
```
**Purpose**: Find untested code paths

#### Hypothesis - Property-Based Testing
```python
from hypothesis import given
from hypothesis.strategies import text, integers

@given(text(), integers())
def test_function_with_random_inputs(string_input, int_input):
    # Test with randomly generated inputs
    result = my_function(string_input, int_input)
    assert isinstance(result, expected_type)
```
**Purpose**: Find edge cases through fuzzing

#### Mutmut - Mutation Testing
```bash
pip install mutmut
mutmut run
mutmut results
```
**Purpose**: Verify tests actually catch bugs

### Runtime Monitoring

#### Django Debug Toolbar (development only)
```bash
pip install django-debug-toolbar
```
**Shows**: SQL queries, templates, cache hits, signals

#### Sentry - Error Tracking
```bash
pip install sentry-sdk
```
**Tracks**: Production errors, performance issues, user impact

### Code Review
- All code must be reviewed before merge
- Use security checklist
- Look for common vulnerabilities
- Verify input validation
- Check error handling

---

## Incident Response

### Preparation
1. **Security Contacts**: Designate security response team
2. **Communication Plan**: How to report and escalate issues
3. **Documentation**: Keep this guide updated
4. **Backups**: Regular backups of database and code

### Detection
1. **Monitor Logs**: Regular log review
2. **Alerts**: Set up automated alerts
3. **User Reports**: Provide security reporting mechanism
4. **Vulnerability Scans**: Regular automated scans

### Response Procedure
1. **Assess**: Determine severity and scope
2. **Contain**: Isolate affected systems
3. **Eradicate**: Remove the threat
4. **Recover**: Restore normal operations
5. **Document**: Record timeline and actions
6. **Learn**: Post-incident review

### Security Incident Severity

#### Critical (P0) - Immediate Response
- Data breach
- Remote code execution
- Authentication bypass
- Database compromise

**Action**: Page security team immediately, take system offline if needed

#### High (P1) - 24 Hour Response
- SQL injection vulnerability
- XSS vulnerability
- Privilege escalation
- Sensitive data exposure

**Action**: Create emergency patch, deploy ASAP

#### Medium (P2) - 1 Week Response
- Information disclosure
- CSRF vulnerability
- Outdated dependencies with known issues

**Action**: Schedule fix in next sprint

#### Low (P3) - Next Sprint
- Security misconfiguration
- Missing security headers
- Deprecated functionality

**Action**: Add to backlog

---

## Security Checklist

### Before Deployment
- [ ] DEBUG = False in production
- [ ] SECRET_KEY from environment variable
- [ ] ALLOWED_HOSTS configured
- [ ] HTTPS enforced (SECURE_SSL_REDIRECT = True)
- [ ] Secure cookies enabled
- [ ] CSRF protection enabled
- [ ] XSS protection enabled
- [ ] SQL injection protection verified
- [ ] Input validation on all user inputs
- [ ] Authentication rate limiting enabled
- [ ] Password requirements enforced
- [ ] Security headers configured
- [ ] Error pages don't expose sensitive info
- [ ] Logging configured and working
- [ ] Dependencies up to date
- [ ] Security scan passed (Bandit, Safety)
- [ ] All tests passing
- [ ] Code review completed

### Regular Maintenance (Monthly)
- [ ] Review security logs
- [ ] Update dependencies
- [ ] Run security scans (Bandit, Safety, pip-audit)
- [ ] Review access controls
- [ ] Test backup restoration
- [ ] Review incident response plan
- [ ] Update security documentation

### After Security Incident
- [ ] Patch vulnerability
- [ ] Update tests to prevent regression
- [ ] Review related code for similar issues
- [ ] Update security documentation
- [ ] Communicate to team
- [ ] Post-incident review meeting

---

## Sprint 3 Implementation Plan

### Week of November 5, 2025

#### CI Pipeline Security Integration

**Tools to Add**:
1. **Bandit** - Python security linting
2. **Safety** or **pip-audit** - Dependency vulnerability scanning
3. **Semgrep** (optional) - Advanced static analysis

**Implementation Steps**:

#### Step 1: Install Tools Locally (Day 1)
```bash
# Add to requirements.txt or requirements-dev.txt
bandit==1.7.10
safety==3.2.10
pip-audit==2.8.0
semgrep==1.104.0

# Install
pip install -r requirements-dev.txt

# Test locally
bandit -r home/ config/
safety check
pip-audit
semgrep --config=p/django home/
```

#### Step 2: Create Configuration Files (Day 1-2)

**.bandit** (in project root):
```yaml
tests:
  - B201  # flask_debug_true
  - B501  # request_with_no_cert_validation
  - B502  # ssl_with_bad_version
  - B503  # ssl_with_bad_defaults
  - B506  # yaml_load
  - B601  # paramiko_calls
  - B602  # shell_with_shell_equals_true
  - B608  # hardcoded_sql_expressions

exclude_dirs:
  - /venv/
  - /env/
  - /.venv/
  - /migrations/
  - /staticfiles/
  - /static/
  - /.pytest_cache/

skips:
  - B101  # assert_used (OK in tests)
  - B110  # try_except_pass (sometimes necessary)
```

**.semgrep.yml** (in project root):
```yaml
rules:
  - id: django-sql-injection
    pattern: cursor.execute(..., $USER_INPUT, ...)
    message: Possible SQL injection - use parameterized queries
    languages: [python]
    severity: ERROR

  - id: hardcoded-secret
    pattern: password = "..."
    message: Hardcoded password detected
    languages: [python]
    severity: ERROR
```

#### Step 3: Create CI Workflow (Day 2-3)

**.github/workflows/security.yml**:
```yaml
name: Security Scans

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    # Run weekly on Mondays at 9am
    - cron: '0 9 * * 1'

jobs:
  bandit:
    name: Bandit Security Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Bandit
        run: pip install bandit

      - name: Run Bandit
        run: |
          bandit -r home/ config/ -f json -o bandit-report.json
          bandit -r home/ config/ -f screen

      - name: Upload Bandit Report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: bandit-report
          path: bandit-report.json

  safety:
    name: Safety Dependency Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Safety
        run: pip install safety

      - name: Run Safety Check
        run: |
          pip install -r requirements.txt
          safety check --json > safety-report.json || true
          safety check

      - name: Upload Safety Report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: safety-report
          path: safety-report.json

  pip-audit:
    name: Pip Audit
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install pip-audit
        run: pip install pip-audit

      - name: Run pip-audit
        run: pip-audit -r requirements.txt

  semgrep:
    name: Semgrep Security Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/security-audit
            p/django
            p/python
```

#### Step 4: Test in Development (Day 3-4)
1. Run all security scans locally
2. Fix any high/critical issues found
3. Document any intentional exceptions
4. Verify scans complete in reasonable time

#### Step 5: Deploy to Main (Day 4-5)
**Option A: Direct to Main** (Recommended for CI changes)
```bash
# Since this affects everyone, deploy directly to main
git checkout main
git pull origin main

# Add security workflow
git add .github/workflows/security.yml
git add .bandit
git add .semgrep.yml
git add requirements-dev.txt

# Commit
git commit -m "Add security scanning to CI pipeline

- Add Bandit for Python security linting
- Add Safety for dependency vulnerability checking
- Add pip-audit for Python package security
- Add Semgrep for advanced static analysis
- Configure exclusions and rules
- Run weekly and on all PRs

Sprint 3 - Security Implementation"

# Push directly to main
git push origin main
```

**Option B: Feature Branch** (If team prefers review)
```bash
git checkout -b sprint3/security-ci
# ... make changes ...
git push origin sprint3/security-ci
# Create PR, get review, merge
```

#### Step 6: Team Communication (Day 5)
- [ ] Announce CI changes in team meeting
- [ ] Share SECURITY_GUIDE.md
- [ ] Share STYLE_GUIDE.md
- [ ] Explain how to run scans locally
- [ ] Explain how to interpret results
- [ ] Set expectations for security issues

### Success Criteria
- [ ] All security scans run on every PR
- [ ] Scans complete in < 5 minutes
- [ ] Team can run scans locally
- [ ] No false positive blocking deployments
- [ ] Security issues are tracked and fixed

### Timeline
- **Monday (Nov 5)**: Install tools, create configs
- **Tuesday (Nov 6)**: Create CI workflow, test locally
- **Wednesday (Nov 7)**: Fix any found issues, finalize configs
- **Thursday (Nov 8)**: Deploy to main, team communication
- **Friday (Nov 9)**: Monitor, adjust as needed

---

## Resources

### Documentation
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Django Security](https://docs.djangoproject.com/en/stable/topics/security/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

### Tools
- [Bandit](https://bandit.readthedocs.io/)
- [Safety](https://pyup.io/safety/)
- [pip-audit](https://github.com/pypa/pip-audit)
- [Semgrep](https://semgrep.dev/)
- [OWASP ZAP](https://www.zaproxy.org/)
- [Snyk](https://snyk.io/)

### Training
- [OWASP WebGoat](https://owasp.org/www-project-webgoat/)
- [Hack The Box](https://www.hackthebox.com/)
- [PentesterLab](https://pentesterlab.com/)

---

## Changelog

### Version 1.0 (October 29, 2025)
- Initial security guide creation
- Documented current security implementations
- Added security scanning tool recommendations
- Created Sprint 3 implementation plan
- Integrated with STYLE_GUIDE.md and CLAUDE.md

---

**Security Questions or Concerns?**
Report security issues privately to the security team. Do not create public issues for security vulnerabilities.

**Emergency Security Contact**: [To Be Defined]
