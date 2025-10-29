# Sprint 3 Implementation Plan

**Language Learning Platform**
**Sprint Start**: Wednesday, November 5, 2025
**Prepared**: October 29, 2025

---

## Sprint 3 Goals

1. **Integrate Pylint into CI Pipeline** - Automated code quality checking
2. **Add Security Scanning Tools** - Bandit, Safety, pip-audit
3. **Establish Team Standards** - Style Guide and Security Guide

---

## New Documentation

### Created This Sprint (Sprint 2)

1. **STYLE_GUIDE.md** - Comprehensive coding standards
   - Python/Django conventions
   - Naming conventions
   - Documentation requirements
   - Testing standards
   - Code review checklist

2. **SECURITY_GUIDE.md** - Security best practices
   - OWASP Top 10 coverage
   - Security scanning tools guide
   - Bug detection strategies
   - Incident response procedures
   - Sprint 3 implementation details

3. **Updated CLAUDE.md** - Added:
   - Single return statement guideline
   - Mutation testing guidance (mutmut)
   - Fuzz testing guidance (hypothesis)
   - Test independence requirements
   - Flaky test prevention

---

## CI Pipeline Changes

### Option A: Direct to Main (RECOMMENDED)

**Rationale**: CI pipeline changes affect everyone, pushing directly to main ensures:
- Everyone gets changes immediately
- No confusion about which branch to use
- Faster adoption
- Simpler workflow

**Process**:
```bash
# Pull latest main
git checkout main
git pull origin main

# Add new workflow files
git add .github/workflows/lint.yml
git add .github/workflows/security.yml
git add .pylintrc
git add .bandit
git add .semgrep.yml

# Commit
git commit -m "Sprint 3: Add CI linting and security scanning"

# Push directly to main
git push origin main
```

**Team Communication**:
- Announce in standup/team meeting
- Email team with changes
- Share new documentation
- Provide local setup instructions

### Option B: Feature Branch + PR

If team prefers review process:
```bash
git checkout -b sprint3/ci-improvements
# ... make changes ...
git push origin sprint3/ci-improvements
# Create PR, get quick team review, merge
```

---

## Implementation Timeline

### Week of November 5-9, 2025

#### Monday, November 5
**Morning**:
- [ ] Team kickoff meeting
- [ ] Review STYLE_GUIDE.md together
- [ ] Review SECURITY_GUIDE.md together
- [ ] Discuss CI pipeline approach (direct to main vs PR)

**Afternoon**:
- [ ] Create `.github/workflows/lint.yml`
- [ ] Create `.github/workflows/security.yml`
- [ ] Test lint workflow locally
- [ ] Test security scans locally

**Deliverable**: CI workflow files ready for deployment

#### Tuesday, November 6
**Morning**:
- [ ] Run full test suite
- [ ] Run pylint locally, fix any critical issues (target: maintain 9.9+/10)
- [ ] Run Bandit, fix any high-severity issues
- [ ] Run Safety/pip-audit, update vulnerable packages

**Afternoon**:
- [ ] Deploy workflows to main
- [ ] Monitor first CI runs
- [ ] Fix any issues
- [ ] Update documentation if needed

**Deliverable**: CI pipeline live and running

#### Wednesday, November 7
**Morning**:
- [ ] Team check-in: Review CI results
- [ ] Address any false positives
- [ ] Adjust thresholds if needed

**Afternoon**:
- [ ] Create team wiki/confluence page with:
  - How to run tools locally
  - How to interpret results
  - How to request exceptions
  - Who to contact for help

**Deliverable**: Team trained and documentation complete

#### Thursday-Friday, November 8-9
- [ ] Monitor CI pipeline
- [ ] Support team with any issues
- [ ] Make adjustments as needed
- [ ] Sprint review/demo on Friday

---

## CI Workflow Files

### 1. Lint Workflow (.github/workflows/lint.yml)

```yaml
name: Lint

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  pylint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pylint pylint-django

      - name: Run Pylint
        run: |
          pylint home/ config/ --rcfile=.pylintrc --fail-under=9.0
```

**Key Points**:
- Runs on pushes to main/develop and all PRs
- Requires score ≥9.0 (currently at 9.91)
- Uses project's `.pylintrc` configuration
- Fails build if score drops below threshold

### 2. Security Workflow (.github/workflows/security.yml)

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
        run: bandit -r home/ config/ -c .bandit

  safety:
    name: Dependency Security Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install safety

      - name: Run Safety
        run: safety check

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
```

**Key Points**:
- Runs on pushes, PRs, and weekly schedule
- Three security tools: Bandit, Safety, pip-audit
- Weekly scheduled scans catch new vulnerabilities
- Generates reports for review

---

## Configuration Files

### .pylintrc
Already created in Sprint 2:
- Django-optimized settings
- Max line length: 120
- Score target: ≥9.0
- Disabled false positives for Django

### .bandit
To be created:
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

skips:
  - B101  # assert_used (OK in tests)
```

---

## Local Development Setup

### For Team Members

#### Install Tools
```bash
# Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Install development dependencies
pip install pylint pylint-django bandit safety pip-audit

# Or add to requirements-dev.txt:
# pylint==3.3.9
# pylint-django==2.6.1
# bandit==1.7.10
# safety==3.2.10
# pip-audit==2.8.0
```

#### Run Locally Before Committing
```bash
# Run pylint
pylint home/ config/

# Run security scans
bandit -r home/ config/
safety check
pip-audit

# Run tests
pytest

# All-in-one check
pylint home/ config/ && bandit -r home/ config/ && pytest
```

---

## Team Communication

### Announcement Template

**Subject**: Sprint 3: CI Pipeline Updates - Pylint & Security Scanning

**Team**,

Starting Sprint 3 (Nov 5), we're adding automated code quality and security checks to our CI pipeline.

**What's New**:
1. **Pylint** - Automated code quality checking (must maintain ≥9.0/10)
2. **Security Scans** - Bandit, Safety, and pip-audit running automatically
3. **Style Guide** - See STYLE_GUIDE.md for coding standards
4. **Security Guide** - See SECURITY_GUIDE.md for security practices

**What This Means For You**:
- PRs must pass all checks before merging
- Run tools locally before pushing (see instructions below)
- CI will catch issues automatically
- We'll maintain high code quality standards

**Local Setup**:
```bash
pip install pylint pylint-django bandit safety pip-audit
```

**Run Before Committing**:
```bash
pylint home/ config/
pytest
```

**Questions**: Ask in #dev-team or during standup

**Documentation**:
- STYLE_GUIDE.md - Coding standards
- SECURITY_GUIDE.md - Security practices
- CLAUDE.md - Development guide (updated)

Let's keep our code quality high! 🚀

---

## Expected Outcomes

### Sprint 3 Success Metrics

#### Code Quality
- [x] Pylint score maintained ≥9.0/10
- [x] All tests passing (167 tests, 93% coverage)
- [ ] Zero high-severity security issues
- [ ] Team using tools locally

#### CI/CD
- [ ] Lint workflow running on all PRs
- [ ] Security workflow running on all PRs
- [ ] Build time < 10 minutes total
- [ ] No false positive blocks

#### Team
- [ ] 100% team trained on new tools
- [ ] Documentation reviewed by all
- [ ] Style guide adopted
- [ ] Security best practices understood

#### Process
- [ ] Clear escalation path for security issues
- [ ] Code review process updated
- [ ] Development workflow streamlined
- [ ] Sprint successfully completed

---

## Potential Issues & Solutions

### Issue: "Pylint is too strict"
**Solution**:
- `.pylintrc` already configured with reasonable settings
- Can disable specific checks with comments: `# pylint: disable=rule-name`
- Discuss as team if threshold should be adjusted

### Issue: "Security scans find vulnerabilities"
**Solution**:
- High/Critical: Fix immediately before merge
- Medium: Create issue, fix in same sprint
- Low: Add to backlog
- See SECURITY_GUIDE.md for severity levels

### Issue: "CI is slow"
**Solution**:
- Optimize workflow (cache dependencies)
- Run security scans in parallel
- Consider reducing frequency of some checks

### Issue: "Too many false positives"
**Solution**:
- Add to exclusion config
- Document why it's safe
- Report to tool maintainers

---

## Post-Sprint 3

### Ongoing Maintenance

#### Weekly
- [ ] Review security scan results
- [ ] Update vulnerable dependencies
- [ ] Check for new security advisories

#### Monthly
- [ ] Review and update STYLE_GUIDE.md
- [ ] Review and update SECURITY_GUIDE.md
- [ ] Check for new versions of security tools
- [ ] Review CI pipeline performance

#### Quarterly
- [ ] Security audit
- [ ] Penetration testing (if applicable)
- [ ] Team security training refresh

---

## Resources

### Quick Links
- [STYLE_GUIDE.md](./STYLE_GUIDE.md) - Coding standards
- [SECURITY_GUIDE.md](./SECURITY_GUIDE.md) - Security practices
- [CLAUDE.md](./CLAUDE.md) - Development guide
- [.pylintrc](./.pylintrc) - Pylint configuration

### External Resources
- [Pylint Documentation](https://pylint.readthedocs.io/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Django Security](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

---

## Questions & Support

### During Sprint 3
- **Standup**: Daily check-ins on progress
- **Slack/Teams**: #dev-team channel for questions
- **Pair Programming**: Available for setup help
- **Documentation**: Refer to guides first

### After Sprint 3
- **Code Reviews**: Reference style guide
- **Security Issues**: Follow SECURITY_GUIDE.md
- **CI Issues**: Check workflow logs, ask team

---

**Prepared by**: Development Team
**Date**: October 29, 2025
**Sprint**: Sprint 3 (Nov 5-9, 2025)

**Ready for Sprint 3! Let's build secure, high-quality code together.** 🎯
