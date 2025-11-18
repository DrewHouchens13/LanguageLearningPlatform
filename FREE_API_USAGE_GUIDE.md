# Free API Usage Guide

This guide shows how to use the 4 free APIs configured in `config/settings.py`.

## Table of Contents
1. [Merriam-Webster Dictionary API](#1-merriam-webster-dictionary-api)
2. [YouTube Transcript API](#2-youtube-transcript-api)
3. [DeepL Translation API](#3-deepl-translation-api)
4. [Detect Language API](#4-detect-language-api)

---

## 1. Merriam-Webster Dictionary API

**Free Tier:** 1,000 requests/day
**Get API Key:** https://dictionaryapi.com/products/index

### Setup
```bash
# Set environment variable
set MERRIAM_WEBSTER_API_KEY=your-api-key-here
```

### Usage Example: Get Word Definition

```python
import requests
from django.conf import settings

def get_word_definition(word):
    """Get definition for a word from Merriam-Webster."""
    api_key = settings.MERRIAM_WEBSTER_API_KEY
    if not api_key:
        return {"error": "API key not configured"}

    # Use the Collegiate Dictionary API
    url = f"https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}"
    params = {"key": api_key}

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()

        # Extract first definition
        if data and isinstance(data[0], dict):
            entry = data[0]

            # Get definition
            definitions = []
            if 'shortdef' in entry:
                definitions = entry['shortdef']

            # Get pronunciation (if available)
            pronunciation = None
            if 'hwi' in entry and 'prs' in entry['hwi']:
                pronunciation = entry['hwi']['prs'][0].get('mw', '')

            return {
                "word": word,
                "definitions": definitions,
                "pronunciation": pronunciation,
                "part_of_speech": entry.get('fl', 'unknown')
            }

    return {"error": f"Word '{word}' not found"}

# Example usage in a view:
def vocabulary_definition(request, word):
    """View to show word definition."""
    definition_data = get_word_definition(word)
    return JsonResponse(definition_data)
```

### Use Cases
- Show definitions for vocabulary words in lessons
- Validate quiz words are real dictionary words
- Provide pronunciation guides for English learners
- Display example sentences and synonyms

---

## 2. YouTube Transcript API

**Free:** No API key required!
**Documentation:** https://pypi.org/project/youtube-transcript-api/

### Usage Example: Extract Spanish Video Transcript

```python
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

def get_youtube_transcript(video_id, language='es'):
    """
    Extract transcript from a YouTube video.

    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
        language: Language code ('es' for Spanish, 'en' for English)

    Returns:
        List of transcript entries with text and timestamps
    """
    try:
        # Get transcript in specified language
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])

        # Format: [{'text': 'Hola', 'start': 0.0, 'duration': 2.5}, ...]
        return {
            "video_id": video_id,
            "language": language,
            "transcript": transcript,
            "success": True
        }

    except TranscriptsDisabled:
        return {"error": "Transcripts are disabled for this video", "success": False}
    except NoTranscriptFound:
        return {"error": f"No {language} transcript found", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}

def get_bilingual_transcript(video_id):
    """Get both Spanish and English transcripts for comparison."""
    spanish = get_youtube_transcript(video_id, 'es')
    english = get_youtube_transcript(video_id, 'en')

    return {
        "spanish": spanish,
        "english": english
    }

# Example usage in a view:
def lesson_video_transcript(request, video_id):
    """View to show bilingual transcript for a lesson video."""
    transcripts = get_bilingual_transcript(video_id)
    return render(request, 'home/video_lesson.html', {
        'video_id': video_id,
        'transcripts': transcripts
    })
```

### Use Cases
- Extract Spanish video transcripts for lessons
- Create bilingual subtitle features (Spanish + English side-by-side)
- Build lesson content from educational YouTube videos
- Practice listening comprehension with auto-generated transcripts

---

## 3. DeepL Translation API

**Free Tier:** 500,000 characters/month
**Get API Key:** https://www.deepl.com/en/pro#developer

### Setup
```bash
# Set environment variable
set DEEPL_API_KEY=your-api-key-here
```

### Usage Example: Translate Spanish ↔ English

```python
import deepl
from django.conf import settings

def translate_text(text, target_lang='EN-US', source_lang=None):
    """
    Translate text using DeepL API.

    Args:
        text: Text to translate
        target_lang: Target language ('EN-US', 'ES')
        source_lang: Source language (optional, auto-detect if None)

    Returns:
        Translated text
    """
    api_key = settings.DEEPL_API_KEY
    if not api_key:
        return {"error": "DeepL API key not configured"}

    translator = deepl.Translator(api_key)

    try:
        result = translator.translate_text(
            text,
            target_lang=target_lang,
            source_lang=source_lang
        )

        return {
            "original": text,
            "translation": result.text,
            "detected_language": result.detected_source_lang,
            "success": True
        }

    except Exception as e:
        return {"error": str(e), "success": False}

def translate_spanish_to_english(text):
    """Helper: Translate Spanish to English."""
    return translate_text(text, target_lang='EN-US', source_lang='ES')

def translate_english_to_spanish(text):
    """Helper: Translate English to Spanish."""
    return translate_text(text, target_lang='ES', source_lang='EN')

# Example usage in a view:
@require_http_methods(["POST"])
def translate_lesson_text(request):
    """API endpoint to translate lesson text."""
    data = json.loads(request.body)
    text = data.get('text', '')
    direction = data.get('direction', 'es-to-en')  # 'es-to-en' or 'en-to-es'

    if direction == 'es-to-en':
        result = translate_spanish_to_english(text)
    else:
        result = translate_english_to_spanish(text)

    return JsonResponse(result)
```

### Use Cases
- High-quality Spanish ↔ English translation
- Translate lesson materials automatically
- Help users understand difficult Spanish phrases
- Support bilingual transcript feature

---

## 4. Detect Language API

**Free Tier:** 1,000 detections/day
**Get API Key:** https://detectlanguage.com/plans

### Setup
```bash
# Set environment variable
set DETECT_LANGUAGE_API_KEY=your-api-key-here
```

### Usage Example: Auto-Detect Language

```python
import detectlanguage
from django.conf import settings

# Configure API key (do this once at startup or in view)
def setup_language_detection():
    """Initialize language detection API."""
    api_key = settings.DETECT_LANGUAGE_API_KEY
    if api_key:
        detectlanguage.configuration.api_key = api_key

def detect_language(text):
    """
    Detect the language of text.

    Args:
        text: Text to analyze

    Returns:
        Language code ('es', 'en', etc.) with confidence score
    """
    setup_language_detection()

    try:
        results = detectlanguage.detect(text)

        if results:
            # Returns list of detected languages with confidence
            # [{'language': 'es', 'isReliable': True, 'confidence': 99.5}]
            primary = results[0]

            return {
                "language": primary['language'],
                "is_reliable": primary['isReliable'],
                "confidence": primary['confidence'],
                "success": True
            }

        return {"error": "Could not detect language", "success": False}

    except Exception as e:
        return {"error": str(e), "success": False}

def is_spanish(text):
    """Check if text is Spanish."""
    result = detect_language(text)
    return result.get('language') == 'es' if result.get('success') else False

def is_english(text):
    """Check if text is English."""
    result = detect_language(text)
    return result.get('language') == 'en' if result.get('success') else False

# Example usage in a view:
@require_http_methods(["POST"])
def validate_quiz_answer(request):
    """Validate that quiz answer is in the correct language."""
    data = json.loads(request.body)
    answer = data.get('answer', '')
    expected_lang = data.get('expected_lang', 'es')

    detection = detect_language(answer)

    if detection.get('success'):
        detected = detection['language']
        is_correct_language = (detected == expected_lang)

        return JsonResponse({
            "is_correct_language": is_correct_language,
            "detected_language": detected,
            "confidence": detection['confidence']
        })

    return JsonResponse({"error": "Could not detect language"}, status=400)
```

### Use Cases
- Auto-detect if user is typing Spanish or English
- Validate quiz answers are in correct language
- Support multi-language platform expansion
- Smart input switching for chat feature

---

## Integration Example: Complete Vocabulary Feature

Here's how to combine multiple APIs for a powerful vocabulary learning feature:

```python
def get_vocabulary_card(word, language='es'):
    """
    Create a complete vocabulary card with definition, translation, and detection.

    Combines:
    - Detect Language API: Verify it's Spanish
    - DeepL API: Get English translation
    - Merriam-Webster API: Get English definition
    """
    # 1. Detect language
    lang_detection = detect_language(word)
    detected_lang = lang_detection.get('language', 'unknown')

    result = {
        "word": word,
        "detected_language": detected_lang
    }

    # 2. If Spanish, translate to English
    if detected_lang == 'es':
        translation = translate_spanish_to_english(word)
        if translation.get('success'):
            result["english_translation"] = translation['translation']

            # 3. Get English definition
            english_word = translation['translation']
            definition = get_word_definition(english_word)
            result["definition"] = definition

    # If English, translate to Spanish
    elif detected_lang == 'en':
        translation = translate_english_to_spanish(word)
        if translation.get('success'):
            result["spanish_translation"] = translation['translation']

        # Get English definition
        definition = get_word_definition(word)
        result["definition"] = definition

    return result
```

---

## Rate Limits & Best Practices

### Rate Limits
- **Merriam-Webster:** 1,000 requests/day
- **YouTube Transcript:** No limit (no API key required)
- **DeepL:** 500,000 characters/month
- **Detect Language:** 1,000 detections/day

### Best Practices

1. **Cache results** - Don't make duplicate API calls
   ```python
   from django.core.cache import cache

   def get_cached_definition(word):
       cache_key = f'definition_{word}'
       cached = cache.get(cache_key)
       if cached:
           return cached

       definition = get_word_definition(word)
       cache.set(cache_key, definition, 60*60*24)  # Cache 24 hours
       return definition
   ```

2. **Handle errors gracefully** - Always check for API failures
3. **Check API key availability** - Fail gracefully if not configured
4. **Monitor usage** - Track API calls to avoid hitting limits
5. **Use environment variables** - Never hardcode API keys

---

## Installation

Install all required packages:

```bash
.\venv\Scripts\pip install youtube-transcript-api==0.6.2 deepl==1.18.0 detectlanguage==1.5.1
```

Or use requirements.txt:

```bash
.\venv\Scripts\pip install -r requirements.txt
```
