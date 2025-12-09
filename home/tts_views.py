"""
Text-to-Speech views for the Language Learning Platform.

Handles all TTS-related HTTP request processing including:
- Onboarding speech generation (OpenAI TTS with ElevenLabs fallback)
- API endpoint for TTS generation via TTSService

These views support language learning by providing audio pronunciation.
"""
import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods, require_POST

from .services.tts_service import TTSService

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def generate_onboarding_speech(request):
    """Generate speech using OpenAI TTS (primary) with ElevenLabs fallback"""
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        lang = data.get('lang', 'es-ES')

        if not text:
            return HttpResponse("No text provided", status=400)

        # Clean text - remove parentheses
        while '(' in text:
            start = text.find('(')
            end = text.find(')', start)
            if end == -1:
                break
            text = text[:start] + ' ' + text[end+1:]
        text = ' '.join(text.split()).strip()

        # Add buffer at beginning to prevent browser audio cutoff
        # The browser often cuts off first 100-200ms, so we add disposable content
        text = 'Okay. ' + text

        # Try OpenAI TTS first (primary)
        openai_key = settings.OPENAI_API_KEY
        if openai_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=openai_key)

                # Choose voice and speed based on language
                # For Spanish: use "alloy" (neutral, clearer) and slower speed
                # For English: use "alloy" at normal speed
                if 'es' in lang.lower():
                    voice = "alloy"
                    speed = 0.85  # Slower for Spanish pronunciation
                else:
                    voice = "alloy"
                    speed = 1.0  # Normal speed for English

                # Log the text being sent for debugging
                logger.info("OpenAI TTS: lang=%s, voice=%s, speed=%s, text='%s'", lang, voice, speed, text)

                response = client.audio.speech.create(
                    model="tts-1",
                    voice=voice,
                    input=text,
                    speed=speed
                )

                audio_bytes = response.content
                return HttpResponse(audio_bytes, content_type='audio/mpeg')

            except (RuntimeError, ValueError, ConnectionError, OSError) as e:
                logger.warning("OpenAI TTS failed, trying ElevenLabs fallback: %s", str(e))

        # Fallback to ElevenLabs
        elevenlabs_key = settings.ELEVENLABS_API_KEY
        if elevenlabs_key:
            try:
                from elevenlabs.client import ElevenLabs  # pylint: disable=import-error,import-outside-toplevel
                client = ElevenLabs(api_key=elevenlabs_key)

                # Choose voice based on language
                if 'es' in lang.lower():
                    voice_id = "pFZP5JQG7iQjIQuC4Bku"  # Lily - female Spanish
                else:
                    voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel - English female

                audio = client.text_to_speech.convert(
                    voice_id=voice_id,
                    text=text,
                    model_id="eleven_multilingual_v2"
                )

                audio_bytes = b''.join(audio)
                return HttpResponse(audio_bytes, content_type='audio/mpeg')

            except (RuntimeError, ValueError, ConnectionError, OSError) as e:
                logger.error("ElevenLabs TTS also failed: %s", str(e))

        # Both TTS services unavailable
        return HttpResponse("TTS not available", status=503)

    except (RuntimeError, ValueError, TypeError, ConnectionError, OSError) as e:
        # Log the detailed error for debugging (SOFA: DRY - logging already imported at module level)
        # Use lazy % formatting for performance (STYLE_GUIDE.md)
        logger.error("TTS Error: %s", str(e))

        # Return generic error to user (don't expose internal details)
        return HttpResponse("Text-to-speech generation failed", status=500)


@login_required
@require_POST
def generate_tts(request):
    """
    API endpoint for text-to-speech generation.
    
    Args:
        request: HTTP request with JSON body {text, language}
    
    Returns:
        JsonResponse: Audio data or browser TTS configuration
    """
    try:
        data = json.loads(request.body)
        text = data.get('text', '').strip()
        language = data.get('language', 'Spanish')
        
        if not text:
            return JsonResponse({'error': 'Text is required'}, status=400)
        
        tts_service = TTSService()
        result = tts_service.generate_audio(text, language)
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error('TTS generation error: %s', str(e))
        return JsonResponse({'error': 'TTS generation failed'}, status=500)

