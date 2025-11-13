#!/usr/bin/env python
"""
Style Guide Compliance Audit Script

Checks all Python files and templates for compliance with STYLE_GUIDE.md.
"""
import os
import re
from pathlib import Path


def check_python_file(filepath):
    """Check a Python file for style guide compliance."""
    issues = []

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')

    # Check for module docstring (first non-blank, non-comment line should be docstring)
    first_code_line_idx = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            first_code_line_idx = idx
            break

    if first_code_line_idx is not None:
        first_line = lines[first_code_line_idx].strip()
        filepath_str = str(filepath)
        if not (first_line.startswith('"""') or first_line.startswith("'''")):
            # Skip __init__.py, migrations, and test files from module docstring requirement
            if not ('__init__.py' in filepath_str or 'migrations' in filepath_str or 'test_' in filepath_str):
                issues.append("Missing module docstring")

    # Check for class docstrings
    class_pattern = re.compile(r'^class\s+(\w+).*:')
    for idx, line in enumerate(lines):
        match = class_pattern.match(line.strip())
        if match:
            # Check next few lines for docstring
            has_docstring = False
            for check_idx in range(idx + 1, min(idx + 5, len(lines))):
                if '"""' in lines[check_idx] or "'''" in lines[check_idx]:
                    has_docstring = True
                    break
            if not has_docstring:
                issues.append(f"Class '{match.group(1)}' missing docstring at line {idx + 1}")

    # Check for function docstrings (only public functions)
    func_pattern = re.compile(r'^def\s+([a-zA-Z]\w+)\(')
    for idx, line in enumerate(lines):
        # Skip private methods (_method) and test methods (test_)
        match = func_pattern.match(line.strip())
        if match:
            func_name = match.group(1)
            if not func_name.startswith('_') and not func_name.startswith('test_'):
                # Check next few lines for docstring
                has_docstring = False
                for check_idx in range(idx + 1, min(idx + 5, len(lines))):
                    if '"""' in lines[check_idx] or "'''" in lines[check_idx]:
                        has_docstring = True
                        break
                if not has_docstring:
                    issues.append(f"Function '{func_name}' missing docstring at line {idx + 1}")

    return issues


def check_template_file(filepath):
    """Check a template file for DevEDU compatibility."""
    issues = []
    filepath_str = str(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Skip partial templates (_nav.html, etc.)
    if os.path.basename(filepath_str).startswith('_'):
        return issues

    # Skip admin templates
    if 'admin' in filepath_str:
        return issues

    # Check for {% load static %}
    if '{% static' in content and '{% load static %}' not in content:
        issues.append("Using {% static %} without {% load static %}")

    # Check for IS_DEVEDU base href (skip lesson-specific templates for now)
    if 'lessons/' not in filepath_str and 'onboarding/' not in filepath_str:
        if '<!DOCTYPE html>' in content and 'IS_DEVEDU' not in content:
            issues.append("Missing IS_DEVEDU base href tag for DevEDU compatibility")

    # Check for proper HTML structure
    if '<!DOCTYPE html>' in content:
        if '<html' not in content:
            issues.append("Has DOCTYPE but missing <html> tag")

    return issues


def audit_project():
    """Run full project audit."""
    project_root = Path(__file__).parent

    # Track all issues
    python_issues = {}
    template_issues = {}

    # Check Python files
    for py_file in project_root.rglob('*.py'):
        # Skip venv and __pycache__
        if 'venv' in str(py_file) or '__pycache__' in str(py_file):
            continue

        # Skip this audit script
        if 'audit_style_compliance' in str(py_file):
            continue

        # Skip test files and migrations from strict docstring checks
        rel_path = py_file.relative_to(project_root)

        issues = check_python_file(py_file)
        if issues:
            python_issues[str(rel_path)] = issues

    # Check template files
    templates_dir = project_root / 'home' / 'templates'
    if templates_dir.exists():
        for template in templates_dir.rglob('*.html'):
            rel_path = template.relative_to(project_root)
            issues = check_template_file(template)
            if issues:
                template_issues[str(rel_path)] = issues

    # Print report
    print("=" * 80)
    print("STYLE GUIDE COMPLIANCE AUDIT")
    print("=" * 80)
    print()

    if python_issues:
        print(f"PYTHON FILES WITH ISSUES ({len(python_issues)} files)")
        print("-" * 80)
        for filepath, issues in sorted(python_issues.items()):
            print(f"\n{filepath}:")
            for issue in issues:
                print(f"  - {issue}")
        print()
    else:
        print("✓ All Python files compliant!")
        print()

    if template_issues:
        print(f"TEMPLATE FILES WITH ISSUES ({len(template_issues)} files)")
        print("-" * 80)
        for filepath, issues in sorted(template_issues.items()):
            print(f"\n{filepath}:")
            for issue in issues:
                print(f"  - {issue}")
        print()
    else:
        print("✓ All template files compliant!")
        print()

    # Summary
    total_issues = len(python_issues) + len(template_issues)
    if total_issues == 0:
        print("=" * 80)
        print("✓ PROJECT FULLY COMPLIANT WITH STYLE GUIDE!")
        print("=" * 80)
    else:
        print("=" * 80)
        print(f"TOTAL: {total_issues} files need attention")
        print("=" * 80)

    return total_issues


if __name__ == '__main__':
    exit_code = audit_project()
    exit(0 if exit_code == 0 else 1)
