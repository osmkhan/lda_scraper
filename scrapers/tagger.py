"""
Auto-tagging system for identifying advocacy topics in documents.
"""

import re
from typing import Dict, List, Set, Tuple
import yaml
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentTagger:
    """Automatically tag documents based on keyword matching."""

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize tagger with advocacy topic keywords.

        Args:
            config_path: Path to configuration file
        """
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        self.topics = config['advocacy_topics']
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficient matching."""
        self.patterns = {}

        for category, keywords in self.topics.items():
            # Create case-insensitive patterns with word boundaries
            patterns = []
            for keyword in keywords:
                # Escape special regex characters and add word boundaries
                escaped = re.escape(keyword)
                pattern = r'\b' + escaped + r'\b'
                patterns.append(pattern)

            # Combine all patterns for this category with OR
            combined_pattern = '|'.join(patterns)
            self.patterns[category] = re.compile(combined_pattern, re.IGNORECASE)

    def tag_text(self, text: str, min_mentions: int = 1) -> Dict[str, int]:
        """
        Tag text with advocacy topics based on keyword matches.

        Args:
            text: Text content to tag
            min_mentions: Minimum number of mentions to include tag

        Returns:
            Dictionary mapping category names to mention counts
        """
        if not text:
            return {}

        tags = {}

        for category, pattern in self.patterns.items():
            matches = pattern.findall(text)
            count = len(matches)

            if count >= min_mentions:
                tags[category] = count

        return tags

    def tag_document(
        self,
        text_by_page: Dict[int, str],
        min_mentions: int = 2
    ) -> Dict[str, Dict]:
        """
        Tag entire document with detailed statistics.

        Args:
            text_by_page: Dictionary mapping page numbers to text
            min_mentions: Minimum total mentions to include tag

        Returns:
            Dictionary with tag statistics
        """
        # Combine all pages
        full_text = ' '.join(text_by_page.values())

        # Get overall tags
        overall_tags = self.tag_text(full_text, min_mentions=min_mentions)

        # Get page-level distribution
        tag_details = {}

        for category in overall_tags.keys():
            pattern = self.patterns[category]
            pages_with_mentions = []

            for page_num, text in text_by_page.items():
                matches = pattern.findall(text)
                if matches:
                    pages_with_mentions.append({
                        'page': page_num,
                        'count': len(matches)
                    })

            tag_details[category] = {
                'total_mentions': overall_tags[category],
                'pages': pages_with_mentions,
                'page_count': len(pages_with_mentions)
            }

        return tag_details

    def get_keywords_for_category(self, category: str) -> List[str]:
        """Get all keywords for a specific category."""
        return self.topics.get(category, [])

    def get_all_categories(self) -> List[str]:
        """Get list of all available categories."""
        return list(self.topics.keys())

    def search_keywords(self, text: str, category: str) -> List[Tuple[str, int, str]]:
        """
        Find all keyword matches with context.

        Args:
            text: Text to search
            category: Category to search for

        Returns:
            List of tuples (keyword, position, context)
        """
        if category not in self.patterns:
            return []

        pattern = self.patterns[category]
        matches = []

        for match in pattern.finditer(text):
            keyword = match.group()
            position = match.start()

            # Extract context (50 chars before and after)
            context_start = max(0, position - 50)
            context_end = min(len(text), position + len(keyword) + 50)
            context = text[context_start:context_end].strip()

            matches.append((keyword, position, context))

        return matches

    def create_tag_summary(self, tag_details: Dict[str, Dict]) -> str:
        """
        Create human-readable summary of tags.

        Args:
            tag_details: Tag details from tag_document()

        Returns:
            Formatted summary string
        """
        if not tag_details:
            return "No advocacy topics detected."

        lines = ["Detected advocacy topics:"]

        # Sort by total mentions
        sorted_tags = sorted(
            tag_details.items(),
            key=lambda x: x[1]['total_mentions'],
            reverse=True
        )

        for category, details in sorted_tags:
            mentions = details['total_mentions']
            page_count = details['page_count']
            lines.append(
                f"  • {category}: {mentions} mentions across {page_count} pages"
            )

        return '\n'.join(lines)


def tag_document_simple(text: str, config_path: str = "config/config.yaml") -> Set[str]:
    """
    Simple convenience function to get tags for text.

    Args:
        text: Text to tag
        config_path: Path to config file

    Returns:
        Set of category names
    """
    tagger = DocumentTagger(config_path)
    tags = tagger.tag_text(text)
    return set(tags.keys())


if __name__ == "__main__":
    # Test the tagger
    tagger = DocumentTagger()

    print("Available categories:")
    for category in tagger.get_all_categories():
        keywords = tagger.get_keywords_for_category(category)
        print(f"  {category}: {len(keywords)} keywords")

    # Test with sample text
    sample_text = """
    The new development plan includes provisions for pedestrian walkways
    and sidewalks to improve walkability in the city center. The plan also
    addresses traffic congestion issues and proposes a new bus rapid transit
    system. Parking requirements will be reduced to encourage public transport
    use. The density will be increased with higher floor area ratios, and more
    green spaces and parks will be added for environmental sustainability.
    """

    print("\nTesting with sample text:")
    tags = tagger.tag_text(sample_text)
    print("Detected tags:")
    for category, count in tags.items():
        print(f"  {category}: {count} mentions")
