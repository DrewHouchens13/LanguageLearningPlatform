# AI Assistant Common Pitfalls - Language Learning Platform

**Date Created**: 2025-11-14
**Purpose**: Document common mistakes AI assistants make when working with this codebase

---

## 🚨 CRITICAL: Django URL Pattern Ordering

### The Problem
Django matches URL patterns **in order from top to bottom**. More general patterns will match before more specific patterns if placed first.

### The Bug We Fixed
**WRONG ORDER** (causes lesson detail pages to break):
```python
# home/urls.py - INCORRECT
path("lessons/<str:language>/", views.lessons_by_language, name="lessons_by_language"),
path("lessons/<int:lesson_id>/", views.lesson_detail, name="lesson_detail"),  # Never reached!
```

**What happens**:
- User clicks "Shapes in Spanish" (lesson ID=2)
- URL is `/lessons/2/`
- Django matches `<str:language>` pattern first
- Treats "2" as a language name
- Shows "No 2 Lessons Available Yet" error page

**CORRECT ORDER**:
```python
# home/urls.py - CORRECT
path("lessons/<int:lesson_id>/", views.lesson_detail, name="lesson_detail"),      # First (specific)
path("lessons/<str:language>/", views.lessons_by_language, name="lessons_by_language"),  # Second (general)
```

**Rule**: Always put more specific patterns (`<int:...>`, `<slug:...>`) before general patterns (`<str:...>`).

---

## 🎨 Django Template Syntax in HTML Comments

### The Problem
Django parses template tags (`{% if %}`, `{% elif %}`, `{% for %}`) even inside HTML comments (`<!-- -->`).

### The Bug We Fixed
**WRONG**:
```html
<!--
Example code for adding icons:
{% elif 'clothing' in lesson.slug %}👕
-->
```

**Error**: `TemplateSyntaxError: Invalid block tag on line 66: 'elif'`

**Why**: Django sees `{% elif %}` and tries to parse it as actual template code, not documentation.

**CORRECT**:
```html
<!--
Example code for adding icons:
Add new condition in _get_lesson_icon() function in views.py
-->
```

**Rule**: Never put Django template syntax in HTML comments. Use plain text descriptions instead.

---

## 🔍 Template Variable Caching

### The Problem
Django caches compiled templates. After making template changes, the old version may still be served.

### The Fix
1. **Restart the dev server**: Kill and restart `run_dev_server.bat`
2. **Clear browser cache**: Hard refresh with `Ctrl+F5` (Windows) or `Cmd+Shift+R` (Mac)
3. **Check server logs**: Verify Django says "changed, reloading"

**Rule**: Always restart server and clear browser cache after template changes.

---

## 📦 Business Logic in Templates vs Views

### The Problem (Anti-Pattern)
**WRONG** - Complex logic in templates:
```html
{% if 'color' in lesson.slug or 'color' in lesson.title|lower %}🎨
{% elif 'shape' in lesson.slug or 'shape' in lesson.title|lower %}🔷
...
{% endif %}
```

**Issues**:
- Hard to test
- Hard to debug
- Violates Single Responsibility Principle (SOFA)
- Template errors are cryptic

### The Fix (SOFA Pattern)
**CORRECT** - Logic in views, data in templates:

**views.py**:
```python
def _get_lesson_icon(lesson):
    """Helper function - single source of truth for icons"""
    slug = (lesson.slug or '').lower()
    if 'color' in slug:
        return '🎨'
    elif 'shape' in slug:
        return '🔷'
    # ...
```

**Template**:
```html
<div>{{ item.icon }}</div>
```

**Rule**: Move complex logic to helper functions in views. Templates should only display data.

---

## 🔄 SOFA Principles Checklist

Before committing code, verify:

### ✅ Single Responsibility
- [ ] Each function does ONE thing
- [ ] Views handle HTTP, services handle business logic
- [ ] Templates only display data (no complex logic)

### ✅ Open/Closed
- [ ] Can extend without modifying existing code
- [ ] Used dictionaries/helpers for extensibility (e.g., LANGUAGE_METADATA)

### ✅ Function Extraction
- [ ] No functions over 30-40 lines
- [ ] Complex logic extracted to helpers (e.g., `_get_lesson_icon`)
- [ ] Each function has clear, single purpose

### ✅ Avoid Repetition (DRY)
- [ ] No copy-pasted code
- [ ] Magic numbers replaced with constants
- [ ] Common patterns extracted to utilities

---

## 🌐 Multi-Language System Architecture

### How It Works
1. **Database**: Lessons have `language='Spanish'` field
2. **Backend Auto-Detection**: Views query distinct languages from database
3. **Metadata Mapping**: `LANGUAGE_METADATA` dict maps English → Native name + flag
4. **Dynamic Display**: Templates loop through detected languages

### Adding New Language (No Template Changes!)
```python
# 1. Add metadata to home/views.py:lessons_list
LANGUAGE_METADATA = {
    'Portuguese': {'native_name': 'Português', 'flag': '🇵🇹'},  # Add this
}

# 2. Create lessons in database
Lesson.objects.create(
    title='Colors in Portuguese',
    language='Portuguese',  # Must match metadata key
    slug='colors',
    is_published=True
)

# 3. That's it! Page automatically shows "🇵🇹 Português" button
```

### Common Mistake
**DON'T** hardcode languages in templates:
```html
{% if language == 'Spanish' %}Español
{% elif language == 'French' %}Français
...
{% endif %}
```

**DO** use dynamic data from backend:
```html
{{ language.native_name }}  <!-- Populated by backend -->
```

---

## 🧪 Testing After Changes

### Checklist
1. [ ] Run full test suite: `pytest`
2. [ ] Check Pylint: `pylint home/ config/`
3. [ ] Security scan: `bandit -r home/ config/`
4. [ ] Manual test in browser with hard refresh (Ctrl+F5)
5. [ ] Test in different browsers (Chrome, Firefox, Edge)
6. [ ] Check server logs for errors
7. [ ] Test with real user account, not test data

---

## 📝 Documentation Standards

### AI-Friendly Preambles
Every major function/template should have:

1. **Purpose**: What it does
2. **How It Works**: Step-by-step
3. **Example Usage**: Concrete examples
4. **Related Files**: Cross-references
5. **Common Mistakes**: What to avoid
6. **How to Extend**: Adding new features

### Format
```python
"""
Brief description.

🤖 AI ASSISTANT INSTRUCTIONS:
Detailed explanation for AI tools...

⚠️ CRITICAL: Important warnings...

EXAMPLE:
Code examples...

RELATED FILES:
- file1.py
- file2.html
"""
```

---

## 🔗 File Cross-Reference

### Lessons System
- `home/views.py` (lines 1631-1818): Lesson views + helper functions
- `home/urls.py` (lines 32-52): URL routing (ORDER MATTERS!)
- `home/templates/lessons_list.html`: Main language selection page
- `home/templates/lessons/lessons_by_language.html`: Language-specific page
- `home/templates/lessons/lesson_detail.html`: Individual lesson page

### Daily Quest System
- `home/services/daily_quest_service.py`: Quest generation logic
- `home/templates/home/daily_quest.html`: Quest display
- `home/views.py` (daily_quest_view, daily_quest_submit): Request handlers
- `home/models.py`: DailyQuest, DailyQuestQuestion, UserDailyQuestAttempt

---

## 🆘 When Things Break

### Symptom: "No {number} Lessons Available"
**Cause**: URL pattern ordering in home/urls.py
**Fix**: Ensure `<int:lesson_id>` comes before `<str:language>`

### Symptom: TemplateSyntaxError with "elif"
**Cause**: Django template tags in HTML comments
**Fix**: Remove template syntax from comments

### Symptom: Template not updating
**Cause**: Django template cache or browser cache
**Fix**: Restart server + hard refresh browser (Ctrl+F5)

### Symptom: "NONE" or empty data in template
**Cause**: View not passing correct context variable
**Fix**: Check view's `context = {...}` matches template's `{{ variable }}`

---

**End of Common Pitfalls Guide**
