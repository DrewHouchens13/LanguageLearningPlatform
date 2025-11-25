# Production Security Checklist

**CRITICAL**: This document outlines security measures for production deployment.

## Test File Exclusion from Production

### ⚠️ Security Risk
Test files contain:
- Hardcoded test credentials (usernames, passwords)
- Test data that exposes internal system behavior
- Testing endpoints and debug code
- Sensitive configuration details
- BDD scenarios that document system vulnerabilities

**Test files must NEVER reach production.**

---

## Current Security Measures

### 1. Defense in Depth - Multiple Layers

#### Layer 1: .gitignore (Partial Protection)
**File**: `.gitignore`

**What's Excluded**:
- ✅ `local_testing/` - Manual testing files (HTML, scripts)
- ✅ `AI_code_reviews/` - Code review files
- ✅ `*.pyc`, `__pycache__/` - Python bytecode
- ✅ `.pytest_cache/` - Pytest cache
- ✅ Test output files (coverage.xml, htmlcov/, etc.)

**What's NOT Excluded** (Intentionally in repo for development):
- ❌ `home/tests/` - Unit tests (needed for CI/CD)
- ❌ `features/` - BDD tests (needed for CI/CD)
- ❌ `pytest.ini`, `.coveragerc` - Test configuration

**Why**: Test files are needed in the repository for:
- Continuous Integration (CI) pipelines
- Other developers to run tests
- Code review processes
- Team collaboration

#### Layer 2: build.sh Cleanup (PRIMARY PROTECTION)
**File**: `build.sh`

**Status**: ✅ **ACTIVE**

**What Gets Removed During Deployment**:
```bash
# Test directories
- home/tests/
- features/
- AI_code_reviews/
- local_testing/
- step_defs/

# Individual test files
- test_*.py
- *_test.py
- *.feature

# Test configuration
- pytest.ini
- .coveragerc
- .coverage
- coverage.xml
- .bandit
- pylint_output.txt
- tox.ini

# Test artifacts
- .pytest_cache/
- htmlcov/
- __pycache__/

# Documentation files (security risk in production)
- *.md (all markdown files)
- README.md, CLAUDE.md, SESSION_PROGRESS.md
- PRODUCTION_SECURITY.md, SPRINT*.md
- STYLE_GUIDE.md, AI_CODE_REVIEW_LOG.md

# Configuration files (not needed in production)
- .gitignore
- .pylintrc
- .bandit
- .coveragerc
- .github/ (entire directory)
```

**Verification**: Script outputs count of remaining test files after cleanup.

#### Layer 3: Manual Verification (Deployment Checklist)

**Before Each Production Deployment**:
1. [ ] Review `build.sh` logs for "SUCCESS: All test files removed"
2. [ ] Check Render deployment logs for security warnings
3. [ ] Verify no test files in production using SSH (if available)

---

## Render.com Deployment Configuration

### render.yaml
**File**: `render.yaml`

**Current Configuration**:
```yaml
buildCommand: "./build.sh"  # Executes test cleanup
autoDeploy: true            # Automatic deployment from main branch
branch: main                # Production branch
```

**Security Notes**:
- ✅ build.sh runs automatically on every deployment
- ✅ Test cleanup happens BEFORE Django collectstatic and migrations
- ⚠️ No native file exclusion support in Render (relies on build.sh)

---

## GitHub Actions (CI/CD)

### CI/CD Pipeline Optimization

**Rationale**: Test files won't exist in production (removed by build.sh), so scanning them in CI/CD pipelines wastes resources and provides no value. Linting and security scanning should focus on production code only.

### deploy.yml
**File**: `.github/workflows/deploy.yml`

**Current Configuration**:
```yaml
on:
  push:
    branches:
      - main  # Only deploys from main branch
```

**Security Notes**:
- ✅ Deployment only triggered from protected main branch
- ✅ Requires branch protection rules (review approval)
- ✅ build.sh cleanup runs during Render deployment

### lint.yml (Pylint Code Quality)
**File**: `.github/workflows/lint.yml`

**Optimization Applied**: Excludes test files from Pylint scanning

**Configuration**:
```yaml
pylint home/ config/ \
  --ignore=tests,test_*.py \
  --ignore-patterns=.*_test\.py,test_.*\.py,.*\.feature \
  --rcfile=.pylintrc \
  --fail-under=9.0
```

**Benefits**:
- ⚡ Faster CI/CD pipeline execution
- 🎯 Focuses on production code quality only
- 💰 Reduced compute resource usage
- ✅ Tests validated separately via pytest

**Notes**: Test files are still validated via pytest in CI/CD but not subjected to Pylint style checks since they won't be deployed to production.

### security.yml (Bandit Security Scanning)
**File**: `.github/workflows/security.yml`

**Optimization Applied**: Excludes test files from Bandit CWE/OWASP security scanning

**Configuration**:
```yaml
bandit -r ./home/ ./config/ \
  --exclude ./home/tests,./features,./local_testing \
  --skip B101 \
  -c .bandit
```

**Benefits**:
- ⚡ Faster security scan execution
- 🎯 Focuses on production code security only
- 💰 Reduced CI/CD resource consumption
- 🔒 Test file credentials never reach production anyway

**Notes**:
- Semgrep, pip-audit, and Safety scans remain unchanged (dependency scanning still covers all packages)
- Test files may contain hardcoded test credentials (intentionally), but these are irrelevant since tests are removed before deployment

---

## Verification Commands

### Local Verification (Before Pushing to Main)
```bash
# Check which test files are tracked in git
git ls-files | grep -E "(test_|_test\.py|/tests/|features/)"

# Verify .gitignore is working
git status --ignored

# Test build.sh locally (dry run)
bash build.sh 2>&1 | grep "SECURITY"
```

### Production Verification (After Deployment)
```bash
# Check Render deployment logs
# Look for: "SUCCESS: All test files removed from production deployment."
# Look for: "SUCCESS: All documentation files removed from production deployment."

# If SSH access available to production:
find /opt/render/project/src -name "test_*.py" -o -name "*.feature"
# Should return: (empty - no results)

find /opt/render/project/src -name "*.md"
# Should return: (empty - no results)
```

### CI/CD Workflow Verification
```bash
# Verify Pylint excludes test files
grep -A 5 "Run Pylint" .github/workflows/lint.yml | grep ignore

# Verify Bandit excludes test files
grep -A 5 "Run Bandit" .github/workflows/security.yml | grep exclude

# Check which files Pylint/Bandit would scan
pylint home/ config/ --ignore=tests,test_*.py --ignore-patterns=.*_test\.py,test_.*\.py,.*\.feature --list-only
```

---

## Known Limitations & Risks

### Current Approach
- ✅ **Secure**: build.sh removes all test files before Django starts
- ✅ **Verified**: Script checks for remaining test files
- ⚠️ **Manual**: Relies on build.sh being correctly configured

### Theoretical Risks (Mitigated)
1. **Risk**: build.sh accidentally removed or modified
   - **Mitigation**: File tracked in git, changes reviewed via PR

2. **Risk**: New test file pattern not covered by build.sh
   - **Mitigation**: Comprehensive patterns + verification step

3. **Risk**: Test files exposed between build.sh and Django startup
   - **Mitigation**: Very short window (<1 second), files deleted before collectstatic

---

## Best Practices for Developers

### When Adding New Tests
1. ✅ Use standard naming conventions:
   - `test_*.py` for unit tests
   - `*.feature` for BDD tests
   - Place in `home/tests/` or `features/` directories

2. ✅ Verify test files are removed by build.sh:
   ```bash
   # Check if your test file pattern is covered
   grep "test_" build.sh
   ```

3. ✅ Never hardcode production credentials in test files

### When Modifying build.sh
1. ⚠️ **CRITICAL**: Never remove the security cleanup section
2. ✅ Test changes locally before pushing
3. ✅ Add new test file patterns if needed
4. ✅ Always include verification step

---

## Emergency Response

### If Test Files Found in Production
1. **Immediate Action**: Trigger manual redeployment to force build.sh cleanup
2. **Verify**: Check deployment logs for "SUCCESS: All test files removed"
3. **Investigate**: Review recent changes to build.sh or render.yaml
4. **Update**: Add missing patterns to build.sh if new test file type found

### Triggering Manual Redeployment
```bash
# Option 1: Via Render Dashboard
# Go to: Render Dashboard → Your Service → Manual Deploy → Deploy latest commit

# Option 2: Via GitHub Actions (if available)
# Go to: Actions → Deploy to Render → Run workflow

# Option 3: Via Render API
curl -X POST $RENDER_DEPLOY_HOOK_URL
```

---

## Audit Log

### 2025-11-14: CI/CD Pipeline Optimization & Documentation Removal
- **Change**: Excluded test files from CI/CD pipeline scanning (Pylint, Bandit)
- **Rationale**: Test files won't exist in production, so scanning them wastes resources
- **Added**: Documentation file removal from production deployment in build.sh
- **Security**: Documentation files expose internal system details and are a security risk
- **Impact**:
  - Faster CI/CD execution (reduced scan time)
  - Reduced resource consumption
  - Improved production security posture
- **Files Modified**:
  - `.github/workflows/lint.yml` (added test exclusions)
  - `.github/workflows/security.yml` (added test exclusions)
  - `build.sh` (added documentation removal with verification)
  - `PRODUCTION_SECURITY.md` (updated documentation)
- **Verification Added**:
  - Documentation file count check in build.sh
  - Logs show "SUCCESS: All documentation files removed"

### 2025-11-14: Enhanced build.sh Security
- **Change**: Comprehensive test file removal with verification
- **Added**: Security headers and verification output
- **Impact**: All test directories and files now removed before production starts
- **Files Modified**: `build.sh`, `PRODUCTION_SECURITY.md` (created)

### Future Improvements
- [ ] Add pre-commit hook to warn if test files are being committed
- [ ] Add GitHub Action to verify build.sh hasn't been modified
- [ ] Consider separate CI and production branches
- [ ] Add automated security scanning for test credentials in code
- [ ] Monitor CI/CD execution time improvements from test file exclusion

---

## Contact & Escalation

**If you discover test files in production**:
1. Report immediately to team lead
2. Document findings in this file
3. Trigger emergency redeployment
4. Review and update build.sh patterns

**This is a critical security issue - treat with highest priority.**
