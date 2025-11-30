"""
Unit tests for TTSService.

Tests text-to-speech audio generation:
- OpenAI TTS API integration
- Browser fallback configuration
- Language-specific voice mapping
- Caching behavior
"""

from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from home.services.tts_service import TTSService


class TestTTSService(TestCase):
    """Test TTSService."""

    def setUp(self):
        """Set up test data."""
        cache.clear()

    @patch('openai.OpenAI')
    @patch('home.services.tts_service.settings')
    def test_generate_audio_with_openai(self, mock_settings, mock_openai):
        """Test audio generation with OpenAI API."""
        # Mock settings to have OPENAI_API_KEY
        mock_settings.OPENAI_API_KEY = 'test-key'
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = b'fake_audio_data'
        mock_client.audio.speech.create.return_value = mock_response

        service = TTSService()
        result = service.generate_audio('Hola, ¿cómo estás?', 'Spanish')

        self.assertEqual(result['type'], 'audio')
        self.assertIsNotNone(result['audio_base64'])
        self.assertEqual(result['content_type'], 'audio/mpeg')
        self.assertIsNone(result['browser_config'])

        # Verify OpenAI was called
        mock_client.audio.speech.create.assert_called_once()
        call_kwargs = mock_client.audio.speech.create.call_args[1]
        self.assertEqual(call_kwargs['model'], 'tts-1')
        self.assertEqual(call_kwargs['voice'], 'nova')
        self.assertEqual(call_kwargs['input'], 'Hola, ¿cómo estás?')

    def test_generate_audio_browser_fallback(self):
        """Test browser fallback when OpenAI unavailable."""
        service = TTSService()
        service.use_openai = False

        result = service.generate_audio('Hello, how are you?', 'Spanish')

        self.assertEqual(result['type'], 'browser')
        self.assertIsNone(result['audio_base64'])
        self.assertIsNotNone(result['browser_config'])
        self.assertEqual(result['browser_config']['lang'], 'es-ES')
        self.assertEqual(result['browser_config']['text'], 'Hello, how are you?')

    def test_get_voice_for_language(self):
        """Test language to voice mapping."""
        service = TTSService()

        self.assertEqual(service._get_voice_for_language('Spanish'), 'nova')
        self.assertEqual(service._get_voice_for_language('French'), 'shimmer')
        self.assertEqual(service._get_voice_for_language('German'), 'onyx')
        self.assertEqual(service._get_voice_for_language('Unknown'), 'nova')  # Default

    def test_browser_fallback_language_codes(self):
        """Test browser language code mapping."""
        service = TTSService()

        result = service._browser_fallback('Test text', 'Spanish')
        self.assertEqual(result['browser_config']['lang'], 'es-ES')

        result = service._browser_fallback('Test text', 'French')
        self.assertEqual(result['browser_config']['lang'], 'fr-FR')

        result = service._browser_fallback('Test text', 'Japanese')
        self.assertEqual(result['browser_config']['lang'], 'ja-JP')

        # Unknown language defaults to en-US
        result = service._browser_fallback('Test text', 'Unknown')
        self.assertEqual(result['browser_config']['lang'], 'en-US')

    @patch('openai.OpenAI')
    @patch('home.services.tts_service.settings')
    def test_generate_audio_caching(self, mock_settings, mock_openai):
        """Test that generated audio is cached."""
        mock_settings.OPENAI_API_KEY = 'test-key'
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = b'cached_audio_data'
        mock_client.audio.speech.create.return_value = mock_response

        service = TTSService()
        text = 'Test caching'
        language = 'Spanish'

        # First call - should call OpenAI
        result1 = service.generate_audio(text, language, use_cache=True)
        self.assertEqual(mock_client.audio.speech.create.call_count, 1)

        # Second call - should use cache
        result2 = service.generate_audio(text, language, use_cache=True)
        self.assertEqual(mock_client.audio.speech.create.call_count, 1)  # No new call
        self.assertEqual(result1['audio_base64'], result2['audio_base64'])

    @patch('openai.OpenAI')
    @patch('home.services.tts_service.settings')
    def test_generate_audio_no_cache(self, mock_settings, mock_openai):
        """Test that cache can be bypassed."""
        mock_settings.OPENAI_API_KEY = 'test-key'
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = b'audio_data'
        mock_client.audio.speech.create.return_value = mock_response

        service = TTSService()
        text = 'Test no cache'
        language = 'Spanish'

        # Call with cache disabled
        service.generate_audio(text, language, use_cache=False)
        # Should still call OpenAI
        self.assertEqual(mock_client.audio.speech.create.call_count, 1)

    def test_generate_audio_empty_text(self):
        """Test handling of empty text."""
        service = TTSService()
        service.use_openai = False

        result = service.generate_audio('', 'Spanish')
        self.assertEqual(result['type'], 'browser')

        result = service.generate_audio('   ', 'Spanish')
        self.assertEqual(result['type'], 'browser')

    @patch('openai.OpenAI')
    def test_generate_audio_openai_error(self, mock_openai):
        """Test fallback to browser when OpenAI fails."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.audio.speech.create.side_effect = Exception('API Error')

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            service = TTSService()
            result = service.generate_audio('Test error', 'Spanish')

        # Should fall back to browser
        self.assertEqual(result['type'], 'browser')
        self.assertIsNotNone(result['browser_config'])

    def test_get_supported_languages(self):
        """Test getting list of supported languages."""
        service = TTSService()
        languages = service.get_supported_languages()

        self.assertIn('Spanish', languages)
        self.assertIn('French', languages)
        self.assertIn('German', languages)
        self.assertIn('Japanese', languages)
        self.assertGreater(len(languages), 0)

    @patch('home.services.tts_service.settings')
    def test_is_openai_available(self, mock_settings):
        """Test checking OpenAI availability."""
        # Test without API key
        mock_settings.OPENAI_API_KEY = None
        with patch.dict('os.environ', {}, clear=False):
            import os
            if 'OPENAI_API_KEY' in os.environ:
                del os.environ['OPENAI_API_KEY']
            service = TTSService()
            self.assertFalse(service.is_openai_available())

        # Test with API key in settings
        mock_settings.OPENAI_API_KEY = 'test-key'
        service = TTSService()
        self.assertTrue(service.is_openai_available())
        
        # Test with API key in environment
        mock_settings.OPENAI_API_KEY = None
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            service = TTSService()
            self.assertTrue(service.is_openai_available())

    def test_get_cache_key(self):
        """Test cache key generation."""
        service = TTSService()

        key1 = service._get_cache_key('Hello', 'Spanish')
        key2 = service._get_cache_key('Hello', 'Spanish')
        key3 = service._get_cache_key('Goodbye', 'Spanish')

        # Same text + language = same key
        self.assertEqual(key1, key2)
        # Different text = different key
        self.assertNotEqual(key1, key3)

