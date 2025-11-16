"""
Centralized language metadata and helper utilities.

This module avoids circular imports by serving as the single source of truth
for supported languages, their display labels, flags, and Web Speech codes.
"""

from typing import Dict, List, Optional

DEFAULT_LANGUAGE = 'Spanish'

LANGUAGE_METADATA: Dict[str, Dict[str, str]] = {
    'Spanish': {'native_name': 'Español', 'flag': '🇪🇸', 'speech_code': 'es-ES'},
    'French': {'native_name': 'Français', 'flag': '🇫🇷', 'speech_code': 'fr-FR'},
    'German': {'native_name': 'Deutsch', 'flag': '🇩🇪', 'speech_code': 'de-DE'},
    'Italian': {'native_name': 'Italiano', 'flag': '🇮🇹', 'speech_code': 'it-IT'},
    'Japanese': {'native_name': '日本語', 'flag': '🇯🇵', 'speech_code': 'ja-JP'},
    'Chinese': {'native_name': '中文', 'flag': '🇨🇳', 'speech_code': 'zh-CN'},
    'Portuguese': {'native_name': 'Português', 'flag': '🇵🇹', 'speech_code': 'pt-PT'},
    'Russian': {'native_name': 'Русский', 'flag': '🇷🇺', 'speech_code': 'ru-RU'},
    'Korean': {'native_name': '한국어', 'flag': '🇰🇷', 'speech_code': 'ko-KR'},
    'Arabic': {'native_name': 'العربية', 'flag': '🇸🇦', 'speech_code': 'ar-SA'},
}


def normalize_language_name(language: Optional[str]) -> str:
    """Normalize arbitrary language input to match metadata keys."""
    if not language:
        return DEFAULT_LANGUAGE
    return language.strip().title()


def get_language_metadata(language: str) -> Dict[str, str]:
    """Return metadata for a given language (case-insensitive)."""
    normalized = normalize_language_name(language)
    return LANGUAGE_METADATA.get(normalized, {
        'native_name': normalized,
        'flag': '🌐',
        'speech_code': 'en-US',
    })


def get_supported_languages(include_flags: bool = True) -> List[Dict[str, str]]:
    """
    Return a list of supported languages formatted for template rendering.

    Args:
        include_flags: Whether to include flag emojis in the label
    """
    languages: List[Dict[str, str]] = []
    for english_name, entry in LANGUAGE_METADATA.items():
        label = entry['native_name']
        if include_flags:
            label = f"{entry['flag']} {label}"
        languages.append({
            'name': english_name,
            'native_name': entry['native_name'],
            'flag': entry['flag'],
            'speech_code': entry['speech_code'],
            'slug': english_name.lower(),
            'display_label': label,
        })

    languages.sort(key=lambda item: item['name'])
    return languages

