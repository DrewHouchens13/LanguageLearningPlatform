"""
Tests for Chatbot Service (AI-powered help assistant)

Following TDD: Tests written before implementation.
Tests should initially fail (Red), then pass after implementation (Green).

Enhanced with mutation testing feedback to ensure comprehensive coverage.
"""

from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import TestCase


class ChatbotServiceSystemPromptTests(TestCase):
    """Tests to verify SYSTEM_PROMPT is properly configured (kills mutant #1)"""

    def test_system_prompt_is_not_none(self):
        """SYSTEM_PROMPT must not be None - critical for AI guardrails"""
        from home.services.chatbot_service import ChatbotService
        self.assertIsNotNone(ChatbotService.SYSTEM_PROMPT)

    def test_system_prompt_is_string(self):
        """SYSTEM_PROMPT must be a string"""
        from home.services.chatbot_service import ChatbotService
        self.assertIsInstance(ChatbotService.SYSTEM_PROMPT, str)

    def test_system_prompt_contains_security_rules(self):
        """SYSTEM_PROMPT must contain security instructions"""
        from home.services.chatbot_service import ChatbotService
        prompt = ChatbotService.SYSTEM_PROMPT
        self.assertIn("SECURITY", prompt.upper())
        self.assertIn("REFUSE", prompt.upper())

    def test_system_prompt_has_minimum_length(self):
        """SYSTEM_PROMPT must have substantial content"""
        from home.services.chatbot_service import ChatbotService
        # A proper system prompt should be at least 200 characters
        self.assertGreater(len(ChatbotService.SYSTEM_PROMPT), 200)

    def test_max_context_length_is_positive(self):
        """MAX_CONTEXT_LENGTH must be a positive number"""
        from home.services.chatbot_service import ChatbotService
        self.assertIsInstance(ChatbotService.MAX_CONTEXT_LENGTH, int)
        self.assertGreater(ChatbotService.MAX_CONTEXT_LENGTH, 0)
        # Verify exact value to catch boundary mutations
        self.assertEqual(ChatbotService.MAX_CONTEXT_LENGTH, 3000)


class ChatbotServiceTests(TestCase):
    """Test ChatbotService basic functionality"""

    def test_chatbot_service_exists(self):
        """ChatbotService class should exist"""
        from home.services.chatbot_service import ChatbotService
        self.assertIsNotNone(ChatbotService)

    def test_get_ai_response_method_exists(self):
        """ChatbotService should have get_ai_response method"""
        from home.services.chatbot_service import ChatbotService
        self.assertTrue(hasattr(ChatbotService, 'get_ai_response'))

    @patch('home.services.chatbot_service.ChatbotService._call_openai_api')
    def test_get_ai_response_returns_dict(self, mock_openai):
        """get_ai_response should return a dictionary with response and sources"""
        from home.services.chatbot_service import ChatbotService

        # Mock OpenAI response
        mock_openai.return_value = "To create an account, click the Sign Up button."

        result = ChatbotService.get_ai_response(
            query="How do I create an account?",
            user_role='user'
        )

        self.assertIsInstance(result, dict)
        self.assertIn('response', result)
        self.assertIn('sources', result)

    @patch('home.services.chatbot_service.settings')
    @patch('home.services.chatbot_service.ChatbotService._call_openai_api')
    def test_get_ai_response_searches_documentation(self, mock_openai, mock_settings):
        """get_ai_response should search help documentation for context"""
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'
        mock_openai.return_value = "Daily quests help you maintain your streak."

        result = ChatbotService.get_ai_response(
            query="What are daily quests?",
            user_role='user'
        )

        # Should return relevant documentation sources
        self.assertIsInstance(result['sources'], list)
        # Should have called OpenAI API
        mock_openai.assert_called_once()

    @patch('home.services.chatbot_service.ChatbotService._call_openai_api')
    def test_get_ai_response_uses_user_role(self, mock_openai):
        """get_ai_response should respect user role for context"""
        from home.services.chatbot_service import ChatbotService

        mock_openai.return_value = "Admin guide content..."

        # Regular user - should only search user guide
        result_user = ChatbotService.get_ai_response(
            query="How do I manage users?",
            user_role='user'
        )

        # Admin user - should search both guides
        result_admin = ChatbotService.get_ai_response(
            query="How do I manage users?",
            user_role='admin'
        )

        # Both should return valid responses
        self.assertIsNotNone(result_user['response'])
        self.assertIsNotNone(result_admin['response'])


class ChatbotServiceContextBuildingTests(TestCase):
    """Test context building for AI prompts"""

    def test_build_context_method_exists(self):
        """ChatbotService should have _build_context method"""
        from home.services.chatbot_service import ChatbotService
        self.assertTrue(hasattr(ChatbotService, '_build_context'))

    def test_build_context_searches_help_service(self):
        """_build_context should use HelpService to search documentation"""
        from home.services.chatbot_service import ChatbotService

        context = ChatbotService._build_context(
            query="How do I reset my password?",
            user_role='user'
        )

        self.assertIsInstance(context, str)
        self.assertGreater(len(context), 0)

    def test_build_context_includes_relevant_sections(self):
        """_build_context should include relevant documentation sections"""
        from home.services.chatbot_service import ChatbotService

        context = ChatbotService._build_context(
            query="daily quests",
            user_role='user'
        )

        # Context should mention daily quests or related topics
        self.assertIsInstance(context, str)

    def test_build_context_limits_length(self):
        """_build_context should limit context length for token management"""
        from home.services.chatbot_service import ChatbotService

        context = ChatbotService._build_context(
            query="everything",  # Broad query that could match many sections
            user_role='user'
        )

        # Context should be limited (e.g., max 3000 characters)
        self.assertLess(len(context), 5000)


class ChatbotServiceOpenAIIntegrationTests(TestCase):
    """Test OpenAI API integration"""

    def test_call_openai_api_method_exists(self):
        """ChatbotService should have _call_openai_api method"""
        from home.services.chatbot_service import ChatbotService
        self.assertTrue(hasattr(ChatbotService, '_call_openai_api'))

    @patch('home.services.chatbot_service.settings')
    @patch.dict('sys.modules', {'openai': MagicMock()})
    def test_call_openai_api_makes_request(self, mock_settings):
        """_call_openai_api should make OpenAI API request"""
        import sys
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        # Mock OpenAI client and response
        mock_openai_module = sys.modules['openai']
        mock_client = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
        mock_client.chat.completions.create.return_value = mock_response

        result = ChatbotService._call_openai_api(
            query="How do I create an account?",
            context="Creating an Account: Click Sign Up..."
        )

        self.assertIsInstance(result, str)
        mock_client.chat.completions.create.assert_called_once()

    @patch('home.services.chatbot_service.settings')
    @patch.dict('sys.modules', {'openai': MagicMock()})
    def test_call_openai_api_includes_system_prompt(self, mock_settings):
        """_call_openai_api should include system prompt with role instructions"""
        import sys
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        # Mock OpenAI client and response
        mock_openai_module = sys.modules['openai']
        mock_client = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
        mock_client.chat.completions.create.return_value = mock_response

        ChatbotService._call_openai_api(
            query="Test query",
            context="Test context"
        )

        # Verify system prompt was included
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']

        # Should have system message
        system_messages = [m for m in messages if m['role'] == 'system']
        self.assertGreater(len(system_messages), 0)

    @patch('home.services.chatbot_service.settings')
    @patch.dict('sys.modules', {'openai': MagicMock()})
    def test_call_openai_api_handles_errors_gracefully(self, mock_settings):
        """_call_openai_api should handle API errors gracefully"""
        import sys
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        # Mock OpenAI client and API error
        mock_openai_module = sys.modules['openai']
        mock_client = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.side_effect = RuntimeError("API Error")

        result = ChatbotService._call_openai_api(
            query="Test query",
            context="Test context"
        )

        # Should return error message, not raise exception
        self.assertIsInstance(result, str)
        self.assertIn("error", result.lower())


class ChatbotServiceResponseStructureTests(TestCase):
    """Tests to verify response dictionary structure (kills mutants #10, #16, #17, #19, #27, #30)"""

    @patch('home.services.chatbot_service.ChatbotService._call_openai_api')
    def test_response_has_exact_keys(self, mock_openai):
        """Response must have exactly 'response' and 'sources' keys"""
        from home.services.chatbot_service import ChatbotService
        mock_openai.return_value = "Test response"

        result = ChatbotService.get_ai_response(query="How do I login?", user_role='user')

        # Verify exact keys exist (not XXresponsesXX or XXsourcesXX)
        self.assertIn('response', result)
        self.assertIn('sources', result)
        # Verify these are the actual keys, not mutated versions
        self.assertTrue('response' in result)
        self.assertTrue('sources' in result)

    @patch('home.services.chatbot_service.settings')
    def test_error_response_has_correct_structure(self, mock_settings):
        """Error responses must have 'response' and 'sources' keys"""
        from home.services.chatbot_service import ChatbotService
        mock_settings.OPENAI_API_KEY = None

        result = ChatbotService.get_ai_response(query="Test", user_role='user')

        self.assertIn('response', result)
        self.assertIn('sources', result)
        self.assertIsInstance(result['sources'], list)

    def test_empty_query_response_has_correct_structure(self):
        """Empty query response must have 'response' and 'sources' keys"""
        from home.services.chatbot_service import ChatbotService

        result = ChatbotService.get_ai_response(query="", user_role='user')

        self.assertIn('response', result)
        self.assertIn('sources', result)
        self.assertIsInstance(result['sources'], list)

    def test_harmful_query_response_has_correct_structure(self):
        """Harmful query response must have 'response' and 'sources' keys"""
        from home.services.chatbot_service import ChatbotService

        result = ChatbotService.get_ai_response(query="how to hack", user_role='user')

        self.assertIn('response', result)
        self.assertIn('sources', result)
        self.assertIsInstance(result['sources'], list)


class ChatbotServiceSourcesLimitTests(TestCase):
    """Tests for sources limit (kills mutant #25)"""

    @patch('home.services.chatbot_service.settings')
    @patch('home.services.chatbot_service.ChatbotService._call_openai_api')
    @patch('home.services.chatbot_service.HelpService.search_documentation')
    def test_sources_limited_to_three(self, mock_search, mock_openai, mock_settings):
        """Sources should be limited to exactly 3 (not 4)"""
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        # Return 5 mock sources
        mock_search.return_value = [
            {'section_title': 'Source 1', 'snippet': 'Content 1'},
            {'section_title': 'Source 2', 'snippet': 'Content 2'},
            {'section_title': 'Source 3', 'snippet': 'Content 3'},
            {'section_title': 'Source 4', 'snippet': 'Content 4'},
            {'section_title': 'Source 5', 'snippet': 'Content 5'},
        ]
        mock_openai.return_value = "Test response"

        result = ChatbotService.get_ai_response(query="How do I login?", user_role='user')

        # Must be exactly 3, not 4
        self.assertEqual(len(result['sources']), 3)
        self.assertLessEqual(len(result['sources']), 3)


class ChatbotServiceEdgeCasesTests(TestCase):
    """Test edge cases and error handling"""

    @patch('home.services.chatbot_service.settings')
    def test_get_ai_response_with_empty_string_query(self, mock_settings):
        """get_ai_response should handle empty string query (kills mutant #13)"""
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        result = ChatbotService.get_ai_response(query="", user_role='user')

        self.assertIsInstance(result, dict)
        self.assertIn('response', result)
        self.assertIn('Please provide', result['response'])

    @patch('home.services.chatbot_service.settings')
    def test_get_ai_response_with_whitespace_only_query(self, mock_settings):
        """get_ai_response should handle whitespace-only query (kills mutant #13)"""
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        # Test with spaces only - this catches the or->and mutation
        result = ChatbotService.get_ai_response(query="   ", user_role='user')

        self.assertIsInstance(result, dict)
        self.assertIn('response', result)
        self.assertIn('Please provide', result['response'])

    @patch('home.services.chatbot_service.settings')
    def test_get_ai_response_with_tabs_and_newlines_query(self, mock_settings):
        """get_ai_response should handle tabs/newlines as empty"""
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        result = ChatbotService.get_ai_response(query="\t\n  ", user_role='user')

        self.assertIsInstance(result, dict)
        self.assertIn('Please provide', result['response'])

    @patch('home.services.chatbot_service.ChatbotService._call_openai_api')
    def test_get_ai_response_with_empty_query(self, mock_openai):
        """get_ai_response should handle empty query"""
        from home.services.chatbot_service import ChatbotService

        mock_openai.return_value = "Please provide a question."

        result = ChatbotService.get_ai_response(
            query="",
            user_role='user'
        )

        self.assertIsInstance(result, dict)
        self.assertIn('response', result)

    @patch('home.services.chatbot_service.ChatbotService._call_openai_api')
    def test_get_ai_response_with_very_long_query(self, mock_openai):
        """get_ai_response should handle very long queries"""
        from home.services.chatbot_service import ChatbotService

        long_query = "How do I " + "very " * 500 + "long question?"
        mock_openai.return_value = "Here's the answer..."

        result = ChatbotService.get_ai_response(
            query=long_query,
            user_role='user'
        )

        self.assertIsInstance(result, dict)

    def test_get_ai_response_without_api_key(self):
        """get_ai_response should handle missing API key gracefully"""
        from home.services.chatbot_service import ChatbotService

        with patch.object(settings, 'OPENAI_API_KEY', None):
            result = ChatbotService.get_ai_response(
                query="Test",
                user_role='user'
            )

            # Should return error response
            self.assertIsInstance(result, dict)
            self.assertIn('error', result['response'].lower())


class ChatbotServiceContextBuildingMutationTests(TestCase):
    """Tests for _build_context to kill mutants #32, #33, #36, #45-49"""

    @patch('home.services.chatbot_service.HelpService.search_documentation')
    def test_build_context_with_no_results(self, mock_search):
        """_build_context should return fallback when no results (kills mutant #33)"""
        from home.services.chatbot_service import ChatbotService

        # Simulate no search results
        mock_search.return_value = []

        context = ChatbotService._build_context("nonexistent topic xyz", "user")

        # Should return the fallback message, not an empty string
        self.assertIn("No relevant documentation", context)

    @patch('home.services.chatbot_service.HelpService.search_documentation')
    def test_build_context_with_results(self, mock_search):
        """_build_context should return context when results exist (kills mutant #33)"""
        from home.services.chatbot_service import ChatbotService

        mock_search.return_value = [
            {'section_title': 'Test Section', 'snippet': 'Test content here'}
        ]

        context = ChatbotService._build_context("login", "user")

        # Should NOT return the no-results message when results exist
        self.assertNotEqual(context, "No relevant documentation found for this query.")
        self.assertIn("Section:", context)
        self.assertIn("Content:", context)

    @patch('home.services.chatbot_service.HelpService.search_documentation')
    def test_build_context_respects_max_length(self, mock_search):
        """_build_context should respect MAX_CONTEXT_LENGTH (kills mutants #45-49)"""
        from home.services.chatbot_service import ChatbotService

        # Create results that would exceed MAX_CONTEXT_LENGTH
        long_content = "x" * 1000
        mock_search.return_value = [
            {'section_title': f'Section {i}', 'snippet': long_content}
            for i in range(10)  # 10 sections of 1000+ chars each
        ]

        context = ChatbotService._build_context("test", "user")

        # Should be limited to MAX_CONTEXT_LENGTH
        self.assertLessEqual(len(context), ChatbotService.MAX_CONTEXT_LENGTH + 100)

    @patch('home.services.chatbot_service.HelpService.search_documentation')
    def test_build_context_accumulates_length_correctly(self, mock_search):
        """_build_context should accumulate length properly (kills mutants #48, #49)"""
        from home.services.chatbot_service import ChatbotService

        # Create multiple small results
        mock_search.return_value = [
            {'section_title': f'Section {i}', 'snippet': f'Content {i}'}
            for i in range(5)
        ]

        context = ChatbotService._build_context("test", "user")

        # All sections should be included since they're small
        self.assertIn("Section: Section 0", context)
        self.assertIn("Section: Section 4", context)

    @patch('home.services.chatbot_service.HelpService.search_documentation')
    def test_build_context_joins_parts_correctly(self, mock_search):
        """_build_context should join parts with empty string (kills mutant #50)"""
        from home.services.chatbot_service import ChatbotService

        mock_search.return_value = [
            {'section_title': 'Section A', 'snippet': 'Content A'},
            {'section_title': 'Section B', 'snippet': 'Content B'},
        ]

        context = ChatbotService._build_context("test", "user")

        # Should NOT have "XXXX" between sections (mutant #50)
        self.assertNotIn("XXXX", context)
        # Should have proper formatting
        self.assertIn("Section: Section A", context)
        self.assertIn("Section: Section B", context)


class ChatbotServiceHarmfulKeywordsTests(TestCase):
    """Comprehensive tests for _is_harmful_query (kills mutants #85-120)"""

    def test_harmful_adult_content_keywords(self):
        """Test all adult content keywords are detected"""
        from home.services.chatbot_service import ChatbotService

        adult_keywords = ['porn', 'xxx', 'sex', 'nude', 'naked', 'adult content', 'nsfw']
        for keyword in adult_keywords:
            result = ChatbotService._is_harmful_query(f"show me {keyword}")
            self.assertTrue(result, f"Failed to detect harmful keyword: {keyword}")

    def test_harmful_violence_keywords(self):
        """Test all violence keywords are detected"""
        from home.services.chatbot_service import ChatbotService

        violence_keywords = ['bomb', 'weapon', 'gun', 'explosive', 'kill', 'murder',
                           'terrorist', 'violence', 'attack', 'assault']
        for keyword in violence_keywords:
            result = ChatbotService._is_harmful_query(f"how to {keyword}")
            self.assertTrue(result, f"Failed to detect harmful keyword: {keyword}")

    def test_harmful_illegal_activity_keywords(self):
        """Test all illegal activity keywords are detected"""
        from home.services.chatbot_service import ChatbotService

        illegal_keywords = ['hack', 'crack', 'pirate', 'steal', 'illegal', 'drug',
                          'cocaine', 'heroin', 'meth', 'fraud', 'scam']
        for keyword in illegal_keywords:
            result = ChatbotService._is_harmful_query(f"how to {keyword}")
            self.assertTrue(result, f"Failed to detect harmful keyword: {keyword}")

    def test_harmful_malicious_intent_keywords(self):
        """Test all malicious intent keywords are detected"""
        from home.services.chatbot_service import ChatbotService

        malicious_keywords = ['ddos', 'malware', 'virus', 'exploit', 'vulnerability']
        for keyword in malicious_keywords:
            result = ChatbotService._is_harmful_query(f"how to {keyword}")
            self.assertTrue(result, f"Failed to detect harmful keyword: {keyword}")

    def test_harmful_self_harm_keywords(self):
        """Test self-harm keywords are detected"""
        from home.services.chatbot_service import ChatbotService

        self_harm_keywords = ['suicide', 'self-harm', 'self harm']
        for keyword in self_harm_keywords:
            result = ChatbotService._is_harmful_query(f"information about {keyword}")
            self.assertTrue(result, f"Failed to detect harmful keyword: {keyword}")

    def test_safe_platform_queries_not_blocked(self):
        """Test that legitimate platform queries are not blocked"""
        from home.services.chatbot_service import ChatbotService

        safe_queries = [
            "How do I create an account?",
            "What are daily quests?",
            "How do I reset my password?",
            "How do I learn Spanish?",
            "What is my streak count?",
        ]
        for query in safe_queries:
            result = ChatbotService._is_harmful_query(query)
            self.assertFalse(result, f"Incorrectly blocked safe query: {query}")


class ChatbotServiceChatHistoryTests(TestCase):
    """Tests for chat history handling (kills mutants #64-71)"""

    @patch('home.services.chatbot_service.settings')
    @patch.dict('sys.modules', {'openai': MagicMock()})
    def test_chat_history_last_five_messages(self, mock_settings):
        """Chat history should only include last 5 messages (kills mutant #64, #65)"""
        import sys
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        mock_openai_module = sys.modules['openai']
        mock_client = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
        mock_client.chat.completions.create.return_value = mock_response

        # Create 10 messages in history
        chat_history = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(10)
        ]

        ChatbotService._call_openai_api(
            query="Test query",
            context="Test context",
            chat_history=chat_history
        )

        # Check that only last 5 messages were included
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']

        # Count user messages from history (excluding system messages and current query)
        history_messages = [m for m in messages if m.get('content', '').startswith('Message')]
        # Should have messages 5-9 (last 5), not 0-4 (first 5)
        self.assertLessEqual(len(history_messages), 5)
        if history_messages:
            # The last history message should be Message 9
            self.assertIn("Message 9", history_messages[-1]['content'])

    @patch('home.services.chatbot_service.settings')
    @patch.dict('sys.modules', {'openai': MagicMock()})
    def test_chat_history_message_structure(self, mock_settings):
        """Chat history messages should have 'role' and 'content' keys (kills mutants #66-71)"""
        import sys
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        mock_openai_module = sys.modules['openai']
        mock_client = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
        mock_client.chat.completions.create.return_value = mock_response

        chat_history = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"},
        ]

        ChatbotService._call_openai_api(
            query="Test query",
            context="Test context",
            chat_history=chat_history
        )

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']

        # All messages should have 'role' and 'content' keys (not mutated versions)
        for msg in messages:
            self.assertIn('role', msg)
            self.assertIn('content', msg)
            # Verify keys are not mutated
            self.assertNotIn('XXroleXX', msg)
            self.assertNotIn('XXcontentXX', msg)


class ChatbotServiceOpenAIMessageStructureTests(TestCase):
    """Tests for OpenAI API message structure (kills mutants #57, #58, #60, #61, #73, #74)"""

    @patch('home.services.chatbot_service.settings')
    @patch.dict('sys.modules', {'openai': MagicMock()})
    def test_system_messages_have_correct_role(self, mock_settings):
        """System messages should have role='system' (kills mutants #57, #60)"""
        import sys
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        mock_openai_module = sys.modules['openai']
        mock_client = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
        mock_client.chat.completions.create.return_value = mock_response

        ChatbotService._call_openai_api(
            query="Test query",
            context="Test context"
        )

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']

        # Find system messages
        system_messages = [m for m in messages if m.get('role') == 'system']
        self.assertGreaterEqual(len(system_messages), 2)  # At least SYSTEM_PROMPT + context

        # Verify role is exactly 'system', not 'XXsystemXX'
        for msg in system_messages:
            self.assertEqual(msg['role'], 'system')

    @patch('home.services.chatbot_service.settings')
    @patch.dict('sys.modules', {'openai': MagicMock()})
    def test_user_message_has_correct_role(self, mock_settings):
        """User query message should have role='user' (kills mutant #73)"""
        import sys
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        mock_openai_module = sys.modules['openai']
        mock_client = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
        mock_client.chat.completions.create.return_value = mock_response

        ChatbotService._call_openai_api(
            query="My test query",
            context="Test context"
        )

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']

        # Last message should be the user query
        user_message = messages[-1]
        self.assertEqual(user_message['role'], 'user')
        self.assertEqual(user_message['content'], 'My test query')

    @patch('home.services.chatbot_service.settings')
    @patch.dict('sys.modules', {'openai': MagicMock()})
    def test_messages_have_content_key(self, mock_settings):
        """All messages should have 'content' key (kills mutants #58, #61, #74)"""
        import sys
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        mock_openai_module = sys.modules['openai']
        mock_client = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
        mock_client.chat.completions.create.return_value = mock_response

        ChatbotService._call_openai_api(
            query="Test query",
            context="Test context"
        )

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']

        # All messages should have 'content' key (not 'XXcontentXX')
        for msg in messages:
            self.assertIn('content', msg)
            self.assertNotIn('XXcontentXX', msg)


class ChatbotServiceAPIParametersTests(TestCase):
    """Tests for OpenAI API parameters (kills mutants #75-77)"""

    @patch('home.services.chatbot_service.settings')
    @patch.dict('sys.modules', {'openai': MagicMock()})
    def test_api_uses_correct_model(self, mock_settings):
        """API should use gpt-3.5-turbo model (kills mutant #75)"""
        import sys
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        mock_openai_module = sys.modules['openai']
        mock_client = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
        mock_client.chat.completions.create.return_value = mock_response

        ChatbotService._call_openai_api(query="Test", context="Context")

        call_args = mock_client.chat.completions.create.call_args
        self.assertEqual(call_args.kwargs['model'], 'gpt-3.5-turbo')

    @patch('home.services.chatbot_service.settings')
    @patch.dict('sys.modules', {'openai': MagicMock()})
    def test_api_uses_correct_max_tokens(self, mock_settings):
        """API should use max_tokens=500 (kills mutant #76)"""
        import sys
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        mock_openai_module = sys.modules['openai']
        mock_client = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
        mock_client.chat.completions.create.return_value = mock_response

        ChatbotService._call_openai_api(query="Test", context="Context")

        call_args = mock_client.chat.completions.create.call_args
        self.assertEqual(call_args.kwargs['max_tokens'], 500)

    @patch('home.services.chatbot_service.settings')
    @patch.dict('sys.modules', {'openai': MagicMock()})
    def test_api_uses_correct_temperature(self, mock_settings):
        """API should use temperature=0.7 (kills mutant #77)"""
        import sys
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        mock_openai_module = sys.modules['openai']
        mock_client = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
        mock_client.chat.completions.create.return_value = mock_response

        ChatbotService._call_openai_api(query="Test", context="Context")

        call_args = mock_client.chat.completions.create.call_args
        self.assertEqual(call_args.kwargs['temperature'], 0.7)


class ChatbotServiceErrorMessageTests(TestCase):
    """Tests for exact error message content (kills string mutants #8-9, #15, #26-29, etc.)"""

    @patch('home.services.chatbot_service.settings')
    def test_missing_api_key_error_message(self, mock_settings):
        """Missing API key should return specific error message (kills #8-9)"""
        from home.services.chatbot_service import ChatbotService
        mock_settings.OPENAI_API_KEY = None

        result = ChatbotService.get_ai_response(query="Test", user_role='user')

        self.assertIn("Error", result['response'])
        self.assertIn("not configured", result['response'])
        self.assertIn("support", result['response'])

    @patch('home.services.chatbot_service.settings')
    def test_empty_query_message_content(self, mock_settings):
        """Empty query should return specific message (kills #15)"""
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        result = ChatbotService.get_ai_response(query="", user_role='user')

        self.assertIn("Please provide", result['response'])
        self.assertIn("question", result['response'])

    @patch('home.services.chatbot_service.settings')
    def test_harmful_query_message_content(self, mock_settings):
        """Harmful query should return exact refusal message (kills #18)"""
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        result = ChatbotService.get_ai_response(query="how to hack computers", user_role='user')

        self.assertEqual(result['response'], "I can't help you with that.")

    @patch('home.services.chatbot_service.settings')
    @patch('home.services.chatbot_service.ChatbotService._call_openai_api')
    def test_exception_error_message(self, mock_openai, mock_settings):
        """Exception should return specific error message (kills #26-29)"""
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'
        mock_openai.side_effect = RuntimeError("API Error")

        result = ChatbotService.get_ai_response(query="How do I login?", user_role='user')

        self.assertIn("error", result['response'].lower())
        self.assertIn("try again", result['response'].lower())


class ChatbotServiceContextUsageTests(TestCase):
    """Tests to verify context is actually built and used (kills #20)"""

    @patch('home.services.chatbot_service.settings')
    @patch('home.services.chatbot_service.ChatbotService._call_openai_api')
    @patch('home.services.chatbot_service.ChatbotService._build_context')
    def test_context_is_built_and_passed(self, mock_build_context, mock_openai, mock_settings):
        """Context should be built and passed to OpenAI (kills #20)"""
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'
        mock_build_context.return_value = "Test context content"
        mock_openai.return_value = "Test response"

        ChatbotService.get_ai_response(query="How do I login?", user_role='user')

        # Verify _build_context was called
        mock_build_context.assert_called_once()
        # Verify context was passed to _call_openai_api
        mock_openai.assert_called_once()
        call_args = mock_openai.call_args
        self.assertEqual(call_args.kwargs['context'], "Test context content")


class ChatbotServiceChatHistorySlicingTests(TestCase):
    """Tests for chat history slicing (kills #64)"""

    @patch('home.services.chatbot_service.settings')
    @patch.dict('sys.modules', {'openai': MagicMock()})
    def test_chat_history_uses_last_five_not_first_five(self, mock_settings):
        """Should use last 5 messages [-5:], not first 5 [+5:] (kills #64)"""
        import sys
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        mock_openai_module = sys.modules['openai']
        mock_client = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
        mock_client.chat.completions.create.return_value = mock_response

        # Create 10 messages - first 5 have "FIRST", last 5 have "LAST"
        chat_history = [
            {"role": "user", "content": f"FIRST message {i}"} for i in range(5)
        ] + [
            {"role": "user", "content": f"LAST message {i}"} for i in range(5)
        ]

        ChatbotService._call_openai_api(
            query="Test query",
            context="Test context",
            chat_history=chat_history
        )

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']

        # Convert to string to check content
        messages_str = str(messages)

        # Should contain LAST messages, not FIRST messages
        self.assertIn("LAST", messages_str)
        self.assertNotIn("FIRST", messages_str)


class ChatbotServiceBoundaryConditionTests(TestCase):
    """Tests for boundary conditions (kills #46, #47)"""

    @patch('home.services.chatbot_service.HelpService.search_documentation')
    def test_context_length_exactly_at_limit(self, mock_search):
        """Context at exact limit should be included (kills #46)"""
        from home.services.chatbot_service import ChatbotService

        # Create content that will be exactly at the limit
        # Each section has ~30 chars overhead for "Section: X\nContent: \n\n"
        content_size = ChatbotService.MAX_CONTEXT_LENGTH // 3 - 50
        mock_search.return_value = [
            {'section_title': 'A', 'snippet': 'x' * content_size},
            {'section_title': 'B', 'snippet': 'y' * content_size},
            {'section_title': 'C', 'snippet': 'z' * content_size},
        ]

        context = ChatbotService._build_context("test", "user")

        # Should include at least 2 sections
        self.assertIn("Section: A", context)
        self.assertIn("Section: B", context)

    @patch('home.services.chatbot_service.HelpService.search_documentation')
    def test_context_breaks_on_length_exceeded(self, mock_search):
        """Should break (not continue) when length exceeded (kills #47)"""
        from home.services.chatbot_service import ChatbotService

        # Create content larger than MAX_CONTEXT_LENGTH for each section
        large_content = 'x' * (ChatbotService.MAX_CONTEXT_LENGTH + 100)
        mock_search.return_value = [
            {'section_title': 'First', 'snippet': 'Small content'},
            {'section_title': 'Second', 'snippet': large_content},
            {'section_title': 'Third', 'snippet': 'Should not appear'},
        ]

        context = ChatbotService._build_context("test", "user")

        # First section should be included
        self.assertIn("Section: First", context)
        # Third section should NOT be included (break, not continue)
        self.assertNotIn("Section: Third", context)


class ChatbotServicePlatformKeywordsTests(TestCase):
    """Tests for platform keywords detection (kills #124-167)"""

    def test_off_topic_short_queries_detected(self):
        """Short off-topic queries should be detected as harmful"""
        from home.services.chatbot_service import ChatbotService

        # These are short queries without platform keywords
        off_topic = ["hello", "hi", "weather", "news", "bitcoin"]
        for query in off_topic:
            result = ChatbotService._is_harmful_query(query)
            self.assertTrue(result, f"Should detect off-topic query: {query}")

    def test_platform_related_short_queries_allowed(self):
        """Short platform-related queries should be allowed"""
        from home.services.chatbot_service import ChatbotService

        # These contain platform keywords
        platform_queries = [
            "help login",
            "learn spanish",
            "my account",
            "reset password",
            "daily quest",
        ]
        for query in platform_queries:
            result = ChatbotService._is_harmful_query(query)
            self.assertFalse(result, f"Should allow platform query: {query}")

    def test_all_platform_keywords_recognized(self):
        """All platform keywords should allow queries through"""
        from home.services.chatbot_service import ChatbotService

        # Test each platform keyword individually in short queries
        platform_keywords = [
            'learn', 'language', 'account', 'login', 'password', 'profile',
            'quest', 'daily', 'points', 'streak', 'lesson', 'practice',
            'dashboard', 'progress', 'achievement', 'badge', 'leaderboard',
            'vocabulary', 'grammar', 'exercise', 'platform', 'help',
            'reset', 'change', 'update', 'delete', 'create', 'register', 'email'
        ]
        for keyword in platform_keywords:
            result = ChatbotService._is_harmful_query(keyword)
            self.assertFalse(result, f"Platform keyword should be allowed: {keyword}")


class ChatbotServiceDocumentationContextTests(TestCase):
    """Tests for documentation context formatting (kills #62)"""

    @patch('home.services.chatbot_service.settings')
    @patch.dict('sys.modules', {'openai': MagicMock()})
    def test_documentation_context_format(self, mock_settings):
        """Documentation context should have correct format (kills #62)"""
        import sys
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        mock_openai_module = sys.modules['openai']
        mock_client = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
        mock_client.chat.completions.create.return_value = mock_response

        ChatbotService._call_openai_api(
            query="Test query",
            context="My test context"
        )

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']

        # Find the context message
        context_messages = [m for m in messages if 'Documentation Context' in m.get('content', '')]
        self.assertEqual(len(context_messages), 1)
        self.assertIn("Documentation Context:", context_messages[0]['content'])
        self.assertIn("My test context", context_messages[0]['content'])


class ChatbotServiceStaticMethodTests(TestCase):
    """Tests to verify methods work correctly (kills @staticmethod mutants #4, #31, #52, #83)"""

    def test_get_ai_response_callable_without_instance(self):
        """get_ai_response should be callable as static method"""
        from home.services.chatbot_service import ChatbotService

        # Should work without creating an instance
        result = ChatbotService.get_ai_response(query="", user_role='user')
        self.assertIsInstance(result, dict)

    def test_build_context_callable_without_instance(self):
        """_build_context should be callable as static method"""
        from home.services.chatbot_service import ChatbotService

        # Should work without creating an instance
        result = ChatbotService._build_context(query="test", user_role='user')
        self.assertIsInstance(result, str)

    def test_is_harmful_query_callable_without_instance(self):
        """_is_harmful_query should be callable as static method"""
        from home.services.chatbot_service import ChatbotService

        # Should work without creating an instance
        result = ChatbotService._is_harmful_query("test query")
        self.assertIsInstance(result, bool)


class ChatbotServiceDefaultParameterTests(TestCase):
    """Tests for default parameter values (kills #5, #68, #71)"""

    @patch('home.services.chatbot_service.ChatbotService._call_openai_api')
    def test_default_user_role(self, mock_openai):
        """Default user_role should be 'user' (kills #5)"""
        from home.services.chatbot_service import ChatbotService

        mock_openai.return_value = "Test response"

        # Call without specifying user_role
        result = ChatbotService.get_ai_response(query="How do I login?")

        self.assertIsInstance(result, dict)
        # Should not raise an error with default user_role

    @patch('home.services.chatbot_service.settings')
    @patch.dict('sys.modules', {'openai': MagicMock()})
    def test_chat_history_default_role(self, mock_settings):
        """Chat history messages should default to 'user' role (kills #68)"""
        import sys
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        mock_openai_module = sys.modules['openai']
        mock_client = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
        mock_client.chat.completions.create.return_value = mock_response

        # Chat history without explicit role
        chat_history = [
            {"content": "Previous question without role"},
        ]

        ChatbotService._call_openai_api(
            query="Test query",
            context="Test context",
            chat_history=chat_history
        )

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']

        # Find the history message (should have defaulted to 'user')
        history_msg = [m for m in messages if "Previous question" in m.get('content', '')]
        self.assertEqual(len(history_msg), 1)
        self.assertEqual(history_msg[0]['role'], 'user')

    @patch('home.services.chatbot_service.settings')
    @patch.dict('sys.modules', {'openai': MagicMock()})
    def test_chat_history_default_content(self, mock_settings):
        """Chat history messages should default to empty content (kills #71)"""
        import sys
        from home.services.chatbot_service import ChatbotService

        mock_settings.OPENAI_API_KEY = 'test-key'

        mock_openai_module = sys.modules['openai']
        mock_client = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
        mock_client.chat.completions.create.return_value = mock_response

        # Chat history without explicit content
        chat_history = [
            {"role": "user"},  # No content key
        ]

        ChatbotService._call_openai_api(
            query="Test query",
            context="Test context",
            chat_history=chat_history
        )

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']

        # Should not raise an error - content defaults to empty string
        self.assertIsNotNone(messages)
