"""
Help/Wiki System Service

Handles loading and parsing of help documentation from markdown files.
Follows SOFA principles: Single Responsibility, Function Extraction, DRY.
"""

import os
import re
from typing import Dict, List, Optional


class HelpService:
    """
    Service for managing help documentation.

    Single Responsibility: Load and parse help documentation files.
    """

    # File paths for documentation
    USER_GUIDE_PATH = os.path.join('USER_GUIDE.md')
    ADMIN_GUIDE_PATH = os.path.join('ADMIN_GUIDE.md')

    @staticmethod
    def load_user_guide() -> Dict[str, any]:
        """
        Load and parse USER_GUIDE.md into structured data.

        Returns:
            dict: {
                'sections': [list of section dicts],
                'toc': [list of table of contents items],
                'raw_content': str
            }
        """
        guide_data = HelpService._load_guide(HelpService.USER_GUIDE_PATH)

        # User guide always returns a dict (empty if file doesn't exist)
        if guide_data is None:
            return {
                'sections': [],
                'toc': [],
                'raw_content': ''
            }

        return guide_data

    @staticmethod
    def load_admin_guide() -> Optional[Dict[str, any]]:
        """
        Load and parse ADMIN_GUIDE.md into structured data.

        Returns:
            dict or None: Same structure as load_user_guide(), or None if file doesn't exist
        """
        return HelpService._load_guide(HelpService.ADMIN_GUIDE_PATH)

    @staticmethod
    def _load_guide(file_path: str) -> Optional[Dict[str, any]]:
        """
        Load and parse a markdown guide file into structured data.

        DRY: Reusable for both User and Admin guides.

        Args:
            file_path: Path to markdown file

        Returns:
            dict or None: {
                'sections': [list of section dicts],
                'toc': [list of table of contents items],
                'raw_content': str
            } or None if file doesn't exist
        """
        content = HelpService._read_markdown_file(file_path)

        if not content:
            return None

        sections = HelpService._parse_sections(content)
        toc = HelpService._generate_toc(sections)

        return {
            'sections': sections,
            'toc': toc,
            'raw_content': content
        }

    @staticmethod
    def _read_markdown_file(file_path: str) -> str:
        """
        Read markdown file from filesystem.

        Function Extraction: Separate file reading logic.

        Args:
            file_path: Path to markdown file

        Returns:
            str: File content or empty string if file doesn't exist
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            return ''
        except IOError as e:
            # Log error in production
            print(f"Error reading file {file_path}: {e}")
            return ''

    @staticmethod
    def _parse_sections(content: str) -> List[Dict[str, str]]:
        """
        Parse markdown content into sections based on headers.

        Function Extraction: Separate parsing logic.
        DRY: Reusable for both User and Admin guides.

        Args:
            content: Markdown file content

        Returns:
            list: [
                {
                    'id': 'getting-started',
                    'title': 'Getting Started',
                    'level': 2,
                    'content': '...'
                },
                ...
            ]
        """
        sections = []

        # Split by headers (## or ###)
        header_pattern = re.compile(r'^(#{2,3})\s+(.+)$', re.MULTILINE)

        # Find all headers
        matches = list(header_pattern.finditer(content))

        if not matches:
            # No headers found, return entire content as one section
            return [{
                'id': 'content',
                'title': 'Documentation',
                'level': 2,
                'content': content
            }]

        for i, match in enumerate(matches):
            hashes, title = match.groups()
            level = len(hashes)  # ## = 2, ### = 3

            # Generate ID from title (lowercase, replace spaces with hyphens)
            section_id = HelpService._generate_section_id(title)

            # Extract content between this header and next header
            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            section_content = content[start_pos:end_pos].strip()

            sections.append({
                'id': section_id,
                'title': title.strip(),
                'level': level,
                'content': section_content
            })

        return sections

    @staticmethod
    def _generate_section_id(title: str) -> str:
        """
        Generate URL-friendly ID from section title.

        Function Extraction: Reusable ID generation logic.

        Args:
            title: Section title (e.g., "Getting Started")

        Returns:
            str: URL-friendly ID (e.g., "getting-started")
        """
        # Convert to lowercase
        section_id = title.lower()

        # Remove special characters except spaces and hyphens
        section_id = re.sub(r'[^a-z0-9\s-]', '', section_id)

        # Replace spaces with hyphens
        section_id = re.sub(r'\s+', '-', section_id)

        # Remove multiple consecutive hyphens
        section_id = re.sub(r'-+', '-', section_id)

        # Remove leading/trailing hyphens
        section_id = section_id.strip('-')

        return section_id

    @staticmethod
    def _generate_toc(sections: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Generate table of contents from sections.

        Function Extraction: Separate TOC generation logic.

        Args:
            sections: List of section dictionaries

        Returns:
            list: [
                {
                    'id': 'getting-started',
                    'title': 'Getting Started',
                    'level': 2
                },
                ...
            ]
        """
        toc = []

        for section in sections:
            toc.append({
                'id': section['id'],
                'title': section['title'],
                'level': section['level']
            })

        return toc

    @staticmethod
    def search_documentation(query: str, user_role: str = 'user') -> List[Dict[str, str]]:
        """
        Search help documentation for a query.

        Args:
            query: Search query string
            user_role: 'user' or 'admin' - determines which guides to search

        Returns:
            list: [
                {
                    'section_id': 'daily-quests',
                    'section_title': 'Daily Quests',
                    'guide_type': 'user',  # or 'admin'
                    'snippet': '...highlighted text...',
                    'relevance_score': 0.95
                },
                ...
            ]
        """
        results = []

        # Search User Guide
        user_guide = HelpService.load_user_guide()
        results.extend(HelpService._search_guide_sections(
            user_guide['sections'], query, guide_type='user'
        ))

        # Search Admin Guide if user is admin
        if user_role == 'admin':
            admin_guide = HelpService.load_admin_guide()
            if admin_guide:
                results.extend(HelpService._search_guide_sections(
                    admin_guide['sections'], query, guide_type='admin'
                ))

        # Sort by relevance score (descending)
        results.sort(key=lambda x: x['relevance_score'], reverse=True)

        return results

    @staticmethod
    def _search_guide_sections(sections: List[Dict[str, str]], query: str,
                               guide_type: str) -> List[Dict[str, str]]:
        """
        Search sections of a guide for a query.

        DRY: Reusable for both User and Admin guides.

        Args:
            sections: List of section dictionaries to search
            query: Search query string
            guide_type: 'user' or 'admin'

        Returns:
            list: Matching sections with relevance scores
        """
        results = []
        query_lower = query.lower()

        for section in sections:
            if query_lower in section['title'].lower() or query_lower in section['content'].lower():
                # Calculate relevance score (simple title match = higher score)
                score = 1.0 if query_lower in section['title'].lower() else 0.5

                # Extract snippet around query
                snippet = HelpService._extract_snippet(section['content'], query, max_length=200)

                results.append({
                    'section_id': section['id'],
                    'section_title': section['title'],
                    'guide_type': guide_type,
                    'snippet': snippet,
                    'relevance_score': score
                })

        return results

    @staticmethod
    def _extract_snippet(content: str, query: str, max_length: int = 200) -> str:
        """
        Extract text snippet around query match.

        Function Extraction: Reusable snippet extraction.

        Args:
            content: Full content text
            query: Search query
            max_length: Maximum snippet length

        Returns:
            str: Text snippet with query context
        """
        query_lower = query.lower()
        content_lower = content.lower()

        # Find query position
        pos = content_lower.find(query_lower)

        if pos == -1:
            # Query not found, return first max_length characters
            return content[:max_length] + ('...' if len(content) > max_length else '')

        # Extract snippet around query
        start = max(0, pos - max_length // 2)
        end = min(len(content), pos + len(query) + max_length // 2)

        snippet = content[start:end]

        # Add ellipsis if truncated
        if start > 0:
            snippet = '...' + snippet
        if end < len(content):
            snippet = snippet + '...'

        return snippet
