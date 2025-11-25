"""
Tests for Chatbot API Views

Following TDD: Tests written before implementation.
"""

import json
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


class ChatbotAPITests(TestCase):
    """Test chatbot API endpoint"""

    def setUp(self):
        """Set up test client and users"""
        self.client = Client()

        self.regular_user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

        self.admin_user = User.objects.create_user(
            username='admin',
            password='adminpass123',
            is_staff=True
        )

    def test_chatbot_query_url_exists(self):
        """URL for chatbot query should exist"""
        url = reverse('chatbot_query')
        self.assertIsNotNone(url)

    @patch('home.services.chatbot_service.ChatbotService.get_ai_response')
    def test_chatbot_query_accepts_post(self, mock_service):
        """Chatbot query endpoint should accept POST requests"""
        mock_service.return_value = {
            'response': 'Test response',
            'sources': []
        }

        response = self.client.post(
            reverse('chatbot_query'),
            data=json.dumps({'query': 'How do I create an account?'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)

    @patch('home.services.chatbot_service.ChatbotService.get_ai_response')
    def test_chatbot_query_rejects_get(self, mock_service):
        """Chatbot query endpoint should reject GET requests"""
        response = self.client.get(reverse('chatbot_query'))
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    @patch('home.services.chatbot_service.ChatbotService.get_ai_response')
    def test_chatbot_query_returns_json(self, mock_service):
        """Chatbot query should return JSON response"""
        mock_service.return_value = {
            'response': 'To create an account, click Sign Up.',
            'sources': [{'title': 'Creating an Account', 'section_id': 'creating-account'}]
        }

        response = self.client.post(
            reverse('chatbot_query'),
            data=json.dumps({'query': 'How do I create an account?'}),
            content_type='application/json'
        )

        self.assertEqual(response['Content-Type'], 'application/json')

        data = json.loads(response.content)
        self.assertIn('response', data)
        self.assertIn('sources', data)

    @patch('home.services.chatbot_service.ChatbotService.get_ai_response')
    def test_chatbot_query_for_guest_user(self, mock_service):
        """Guest users should be able to query chatbot"""
        mock_service.return_value = {
            'response': 'Test response',
            'sources': []
        }

        response = self.client.post(
            reverse('chatbot_query'),
            data=json.dumps({'query': 'Test query'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        # Should pass user_role='user' to service
        mock_service.assert_called_once()
        call_kwargs = mock_service.call_args.kwargs
        self.assertEqual(call_kwargs['user_role'], 'user')

    @patch('home.services.chatbot_service.ChatbotService.get_ai_response')
    def test_chatbot_query_for_logged_in_user(self, mock_service):
        """Logged-in users should be able to query chatbot"""
        self.client.login(username='testuser', password='testpass123')

        mock_service.return_value = {
            'response': 'Test response',
            'sources': []
        }

        response = self.client.post(
            reverse('chatbot_query'),
            data=json.dumps({'query': 'Test query'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)

    @patch('home.services.chatbot_service.ChatbotService.get_ai_response')
    def test_chatbot_query_for_admin_user(self, mock_service):
        """Admin users should get admin role for queries"""
        self.client.login(username='admin', password='adminpass123')

        mock_service.return_value = {
            'response': 'Admin response',
            'sources': []
        }

        response = self.client.post(
            reverse('chatbot_query'),
            data=json.dumps({'query': 'How do I manage users?'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        # Should pass user_role='admin' to service
        call_kwargs = mock_service.call_args.kwargs
        self.assertEqual(call_kwargs['user_role'], 'admin')

    @patch('home.services.chatbot_service.ChatbotService.get_ai_response')
    def test_chatbot_query_requires_query_param(self, mock_service):
        """Chatbot query should require 'query' parameter"""
        response = self.client.post(
            reverse('chatbot_query'),
            data=json.dumps({}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)  # Bad Request

    @patch('home.services.chatbot_service.ChatbotService.get_ai_response')
    def test_chatbot_query_handles_invalid_json(self, mock_service):
        """Chatbot query should handle invalid JSON gracefully"""
        response = self.client.post(
            reverse('chatbot_query'),
            data='invalid json',
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)

    @patch('home.services.chatbot_service.ChatbotService.get_ai_response')
    def test_chatbot_query_handles_service_error(self, mock_service):
        """Chatbot query should handle service errors gracefully"""
        mock_service.side_effect = RuntimeError("Service error")

        response = self.client.post(
            reverse('chatbot_query'),
            data=json.dumps({'query': 'Test query'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertIn('error', data)

    @patch('home.services.chatbot_service.ChatbotService.get_ai_response')
    def test_chatbot_query_with_chat_history(self, mock_service):
        """Chatbot query should accept optional chat history"""
        mock_service.return_value = {
            'response': 'Follow-up response',
            'sources': []
        }

        chat_history = [
            {'role': 'user', 'content': 'How do I login?'},
            {'role': 'assistant', 'content': 'Click the Login button.'}
        ]

        response = self.client.post(
            reverse('chatbot_query'),
            data=json.dumps({
                'query': 'Where is it?',
                'chat_history': chat_history
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)

    @patch('home.services.chatbot_service.ChatbotService.get_ai_response')
    def test_chatbot_query_response_structure(self, mock_service):
        """Chatbot query response should have correct structure"""
        mock_service.return_value = {
            'response': 'Test response',
            'sources': [
                {
                    'section_id': 'daily-quests',
                    'section_title': 'Daily Quests',
                    'guide_type': 'user',
                    'snippet': 'Complete daily quests...'
                }
            ]
        }

        response = self.client.post(
            reverse('chatbot_query'),
            data=json.dumps({'query': 'What are daily quests?'}),
            content_type='application/json'
        )

        data = json.loads(response.content)
        self.assertIn('response', data)
        self.assertIn('sources', data)
        self.assertIsInstance(data['sources'], list)

        if data['sources']:
            source = data['sources'][0]
            self.assertIn('section_id', source)
            self.assertIn('section_title', source)
