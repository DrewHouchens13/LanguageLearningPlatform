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
    SYSTEM_PROMPT = """You are the AI Help Assistant for the Language Learning Platform.

CRITICAL SECURITY RULES - YOU MUST FOLLOW THESE:
1. ONLY answer questions about the Language Learning Platform
2. ONLY use information from the documentation context provided below
3. REFUSE all requests unrelated to this platform (harmful content, general advice, other topics)
4. If asked about anything not in the documentation, respond: "I can't help you with that"
5. Never provide information about: illegal activities, adult content, violence, hacking, or any topic outside language learning

Your role:
- Answer questions using ONLY the documentation provided below
- Speak confidently as "our platform's" help assistant
- Give specific, actionable steps from the documentation
- You can mention specific URLs like /login/, /dashboard/, etc.

Response Guidelines:
- REFUSE off-topic requests immediately with: "I can't help you with that"
- REFUSE harmful requests immediately with: "I can't help you with that"
- Stay strictly within the documentation context
- If documentation doesn't cover it, say: "I don't have information about that in our help documentation"
- Keep responses clear, concise, under 150 words
- Use bullet points for steps and lists
- Be friendly and encouraging for valid platform questions

REMEMBER: You are a help assistant for a language learning platform. Nothing else.
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

        # Security: Check for harmful or off-topic queries
        if ChatbotService._is_harmful_query(query):
            return {
                'response': "I can't help you with that.",
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

        except (RuntimeError, ValueError, TypeError, ConnectionError) as e:
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

        except (RuntimeError, ValueError, TypeError, ConnectionError, OSError) as e:
            # Log error in production
            print(f"OpenAI API error: {e}")
            return "I encountered an error while generating a response. Please try again later or contact support."

    @staticmethod
    def _is_harmful_query(query: str) -> bool:
        """
        Check if query contains harmful or off-topic content.

        Security guardrail to prevent misuse of the chatbot.

        Args:
            query: User's question

        Returns:
            bool: True if query is harmful/off-topic, False if safe
        """
        query_lower = query.lower()

        # Harmful content patterns
        harmful_keywords = [
            # Adult/sexual content
            'porn', 'xxx', 'sex', 'nude', 'naked', 'adult content', 'nsfw',
            # Violence/weapons
            'bomb', 'weapon', 'gun', 'explosive', 'kill', 'murder', 'terrorist',
            'violence', 'attack', 'assault',
            # Illegal activities
            'hack', 'crack', 'pirate', 'steal', 'illegal', 'drug', 'cocaine',
            'heroin', 'meth', 'fraud', 'scam',
            # Malicious intent
            'ddos', 'malware', 'virus', 'exploit', 'vulnerability',
            # Other inappropriate
            'suicide', 'self-harm', 'self harm'
        ]

        # Check for harmful keywords
        for keyword in harmful_keywords:
            if keyword in query_lower:
                return True

        # Check if query is clearly off-topic (no platform-related keywords)
        # If query doesn't mention anything related to language learning or the platform
        platform_keywords = [
            'learn', 'language', 'account', 'login', 'password', 'profile',
            'quest', 'daily', 'points', 'streak', 'lesson', 'practice',
            'dashboard', 'progress', 'achievement', 'badge', 'leaderboard',
            'vocabulary', 'grammar', 'exercise', 'platform', 'help', 'how',
            'what', 'where', 'when', 'can i', 'do i', 'reset', 'change',
            'update', 'delete', 'create', 'sign up', 'register', 'email'
        ]

        # If query is very short (1-2 words) and contains no platform keywords, it's suspicious
        words = query_lower.split()
        if len(words) <= 2:
            has_platform_keyword = any(keyword in query_lower for keyword in platform_keywords)
            if not has_platform_keyword:
                return True  # Likely off-topic or probing

        return False
