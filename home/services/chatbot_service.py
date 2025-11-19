"""
Chatbot Service for AI-powered Help Assistant

Integrates with OpenAI API to provide intelligent, context-aware responses
based on platform documentation.

Follows SOFA principles: Single Responsibility, Function Extraction, DRY.
"""

from typing import Dict, List, Optional
from django.conf import settings
from home.services.help_service import HelpService


class ChatbotService:
    """
    Service for AI-powered chatbot assistant.

    Single Responsibility: Handle AI chatbot interactions and context building.
    """

    # System prompt template for AI assistant
    SYSTEM_PROMPT = """You are a helpful assistant for the Language Learning Platform.
Your role is to help users understand how to use the platform by answering questions
based on the provided documentation.

Guidelines:
- Answer questions clearly and concisely
- Use the documentation context provided to give accurate answers
- If you don't know something based on the documentation, say so
- Be friendly and encouraging
- Keep responses under 200 words unless more detail is specifically requested
- Format responses with markdown for better readability
"""

    # Maximum context length (in characters) to send to OpenAI
    MAX_CONTEXT_LENGTH = 3000

    @staticmethod
    def get_ai_response(query: str, user_role: str = 'user',
                       chat_history: Optional[List[Dict]] = None) -> Dict[str, any]:
        """
        Get AI-powered response to user query.

        Args:
            query: User's question
            user_role: 'user' or 'admin' - determines documentation access
            chat_history: Optional previous conversation messages

        Returns:
            dict: {
                'response': str (AI-generated response),
                'sources': list (relevant documentation sections)
            }
        """
        # Check if API key is configured
        if not settings.OPENAI_API_KEY:
            return {
                'response': "Error: The AI assistant is not configured properly. "
                           "Please contact support.",
                'sources': []
            }

        # Handle empty query
        if not query or not query.strip():
            return {
                'response': "Please provide a question and I'll do my best to help!",
                'sources': []
            }

        # Build documentation context
        context = ChatbotService._build_context(query, user_role)

        # Get relevant sources for response
        sources = HelpService.search_documentation(query, user_role)

        # Get AI response
        try:
            ai_response = ChatbotService._call_openai_api(
                query=query,
                context=context,
                chat_history=chat_history
            )

            return {
                'response': ai_response,
                'sources': sources[:3]  # Limit to top 3 sources
            }

        except Exception as e:
            # Log error in production
            print(f"ChatbotService error: {e}")

            return {
                'response': "I encountered an error while processing your question. "
                           "Please try again or contact support if the issue persists.",
                'sources': []
            }

    @staticmethod
    def _build_context(query: str, user_role: str) -> str:
        """
        Build documentation context for AI prompt.

        Function Extraction: Separate context building logic.

        Args:
            query: User's question
            user_role: 'user' or 'admin'

        Returns:
            str: Formatted context from documentation
        """
        # Search documentation for relevant sections
        search_results = HelpService.search_documentation(query, user_role)

        if not search_results:
            return "No relevant documentation found for this query."

        # Build context from top results
        context_parts = []
        total_length = 0

        for result in search_results:
            # Format: "Section: Title\nContent: snippet"
            section_context = f"Section: {result['section_title']}\n"
            section_context += f"Content: {result['snippet']}\n\n"

            # Check length limit
            if total_length + len(section_context) > ChatbotService.MAX_CONTEXT_LENGTH:
                break

            context_parts.append(section_context)
            total_length += len(section_context)

        return "".join(context_parts) if context_parts else "No relevant documentation found."

    @staticmethod
    def _call_openai_api(query: str, context: str,
                        chat_history: Optional[List[Dict]] = None) -> str:
        """
        Call OpenAI API to get AI response.

        Function Extraction: Separate OpenAI interaction logic.

        Args:
            query: User's question
            context: Documentation context
            chat_history: Optional previous messages

        Returns:
            str: AI-generated response
        """
        try:
            # Import OpenAI library
            try:
                from openai import OpenAI
            except ImportError:
                return ("The AI assistant requires the OpenAI library to be installed. "
                       "Please contact support.")

            # Initialize OpenAI client
            client = OpenAI(api_key=settings.OPENAI_API_KEY)

            # Build messages for API
            messages = [
                {
                    "role": "system",
                    "content": ChatbotService.SYSTEM_PROMPT
                },
                {
                    "role": "system",
                    "content": f"Documentation Context:\n\n{context}"
                }
            ]

            # Add chat history if provided
            if chat_history:
                for msg in chat_history[-5:]:  # Last 5 messages only
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })

            # Add current query
            messages.append({
                "role": "user",
                "content": query
            })

            # Call OpenAI API
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )

            return response.choices[0].message.content

        except Exception as e:
            # Log error in production
            print(f"OpenAI API error: {e}")
            return (f"I encountered an error while generating a response. "
                   f"Error details: {str(e)}")
