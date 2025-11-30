"""
Text-to-Speech Service for Language Learning Platform.

Provides audio generation using OpenAI's TTS API with browser fallback
for client-side speech synthesis when server-side generation isn't available.

🤖 AI ASSISTANT: This service powers audio for listening lessons.
- Primary: OpenAI TTS API (server-side, high quality)
- Fallback: Browser Web Speech API (client-side, no cost)
- Language-specific voice selection for authentic pronunciation

RELATED FILES:
- home/views.py - TTS API endpoint
- home/templates/curriculum/lesson_listening.html - Audio player UI
- home/static/home/js/tts.js - Browser fallback implementation
"""

import base64
import hashlib
import logging
import os
from typing import Optional

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class TTSService:
    """
    Text-to-speech service using OpenAI audio API with browser fallback.
    
    Usage:
        service = TTSService()
        result = service.generate_audio("Hola, ¿cómo estás?", "Spanish")
        
        if result['type'] == 'audio':
            # Server-generated audio (base64 encoded)
            audio_data = result['audio_base64']
        else:
            # Use browser TTS with provided config
            browser_config = result['browser_config']
    """
    
    # OpenAI TTS voices mapped to languages for authentic pronunciation
    # See: https://platform.openai.com/docs/guides/text-to-speech
    VOICE_MAPPING = {
        'Spanish': 'nova',      # Female, warm tone
        'French': 'shimmer',    # Female, expressive
        'German': 'onyx',       # Male, authoritative
        'Italian': 'nova',      # Female, warm
        'Portuguese': 'shimmer', # Female, expressive
        'Japanese': 'nova',     # Female, clear
        'Korean': 'shimmer',    # Female, clear
        'Chinese': 'nova',      # Female, clear
        'Arabic': 'onyx',       # Male, clear
        'Russian': 'onyx',      # Male, authoritative
    }
    
    # Browser speech synthesis language codes
    BROWSER_LANG_CODES = {
        'Spanish': 'es-ES',
        'French': 'fr-FR',
        'German': 'de-DE',
        'Italian': 'it-IT',
        'Portuguese': 'pt-BR',
        'Japanese': 'ja-JP',
        'Korean': 'ko-KR',
        'Chinese': 'zh-CN',
        'Arabic': 'ar-SA',
        'Russian': 'ru-RU',
    }
    
    # Cache TTL for generated audio (1 hour)
    CACHE_TTL = 3600
    
    def __init__(self):
        """Initialize the TTS service."""
        self.api_key = getattr(settings, 'OPENAI_API_KEY', os.environ.get('OPENAI_API_KEY'))
        self.use_openai = bool(self.api_key)
        
        if not self.use_openai:
            logger.warning(
                'OpenAI API key not configured. TTS will use browser fallback only.'
            )
    
    def generate_audio(self, text: str, language: str, use_cache: bool = True) -> dict:
        """
        Generate audio for the given text in the specified language.
        
        Args:
            text: The text to convert to speech
            language: Target language (e.g., 'Spanish', 'French')
            use_cache: Whether to use cached audio if available
            
        Returns:
            dict: Either audio data or browser TTS configuration
                  {
                      'type': 'audio' | 'browser',
                      'audio_base64': str | None,  # Base64 encoded MP3
                      'content_type': str | None,  # 'audio/mpeg'
                      'browser_config': dict | None  # For Web Speech API
                  }
        """
        if not text or not text.strip():
            return self._browser_fallback(text, language)
        
        # Try server-side TTS if API key is available
        if self.use_openai:
            # Check cache first
            if use_cache:
                cache_key = self._get_cache_key(text, language)
                cached = cache.get(cache_key)
                if cached:
                    logger.debug('TTS cache hit for: %s...', text[:30])
                    return cached
            
            try:
                audio_data = self._call_openai_tts(text, language)
                if audio_data:
                    result = {
                        'type': 'audio',
                        'audio_base64': base64.b64encode(audio_data).decode('utf-8'),
                        'content_type': 'audio/mpeg',
                        'browser_config': None,
                    }
                    
                    # Cache the result
                    if use_cache:
                        cache.set(cache_key, result, self.CACHE_TTL)
                    
                    return result
            except Exception as e:
                logger.error('OpenAI TTS failed, falling back to browser: %s', str(e))
        
        # Fall back to browser TTS
        return self._browser_fallback(text, language)
    
    def _call_openai_tts(self, text: str, language: str) -> Optional[bytes]:
        """
        Call OpenAI's text-to-speech API.
        
        Args:
            text: Text to convert
            language: Target language
            
        Returns:
            bytes: MP3 audio data or None if failed
        """
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.api_key)
            voice = self._get_voice_for_language(language)
            
            response = client.audio.speech.create(
                model="tts-1",  # Standard quality, faster
                voice=voice,
                input=text,
                response_format="mp3",
            )
            
            # Read the audio content
            audio_data = response.content
            logger.info('Generated TTS audio for %d characters in %s', len(text), language)
            return audio_data
            
        except ImportError:
            logger.error('OpenAI package not installed. Run: pip install openai')
            return None
        except Exception as e:
            logger.error('OpenAI TTS API error: %s', str(e))
            raise
    
    def _get_voice_for_language(self, language: str) -> str:
        """
        Get the appropriate OpenAI voice for the language.
        
        Args:
            language: Target language name
            
        Returns:
            str: OpenAI voice identifier
        """
        return self.VOICE_MAPPING.get(language, 'nova')
    
    def _browser_fallback(self, text: str, language: str) -> dict:
        """
        Return configuration for browser-based TTS via Web Speech API.
        
        Args:
            text: Text to speak
            language: Target language
            
        Returns:
            dict: Browser TTS configuration
        """
        lang_code = self.BROWSER_LANG_CODES.get(language, 'en-US')
        
        return {
            'type': 'browser',
            'audio_base64': None,
            'content_type': None,
            'browser_config': {
                'text': text,
                'lang': lang_code,
                'rate': 0.9,  # Slightly slower for learning
                'pitch': 1.0,
            }
        }
    
    def _get_cache_key(self, text: str, language: str) -> str:
        """
        Generate a cache key for the text/language combination.
        
        Args:
            text: The text being converted
            language: Target language
            
        Returns:
            str: Cache key
        """
        content = f"{language}:{text}"
        hash_val = hashlib.md5(content.encode('utf-8'), usedforsecurity=False).hexdigest()
        return f"tts:{hash_val}"
    
    def get_supported_languages(self) -> list:
        """
        Get list of supported languages for TTS.
        
        Returns:
            list: Language names supported by the service
        """
        return list(self.VOICE_MAPPING.keys())
    
    def is_openai_available(self) -> bool:
        """
        Check if OpenAI TTS is available.
        
        Returns:
            bool: True if OpenAI API key is configured
        """
        return self.use_openai

