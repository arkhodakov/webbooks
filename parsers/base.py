"""Base classes and data structures for book parsing."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol
import hashlib
import re


@dataclass
class TocEntry:
    """Table of contents entry."""
    title: str
    chapter_index: int
    level: int = 0  # Nesting level (0 = top level)


@dataclass
class Chapter:
    """A chapter or section of a book."""
    title: str
    content: str  # Plain text content
    index: int


@dataclass
class Book:
    """Parsed book with metadata and content."""
    title: str
    author: str
    file_path: Path
    chapters: list[Chapter] = field(default_factory=list)
    toc: list[TocEntry] = field(default_factory=list)

    @property
    def format(self) -> str:
        """Return the book format based on file extension."""
        return self.file_path.suffix.lower().lstrip(".")

    @property
    def slug(self) -> str:
        """Generate a URL-safe slug from the title."""
        # Transliterate Cyrillic to Latin
        translit_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        }

        slug = self.title.lower()
        for cyr, lat in translit_map.items():
            slug = slug.replace(cyr, lat)
            slug = slug.replace(cyr.upper(), lat.capitalize())

        # Replace non-alphanumeric with hyphens
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = slug.strip('-')

        # Add short hash to ensure uniqueness
        hash_suffix = hashlib.md5(str(self.file_path).encode()).hexdigest()[:6]
        return f"{slug[:30]}-{hash_suffix}" if slug else hash_suffix

    @property
    def total_chapters(self) -> int:
        return len(self.chapters)


class BookParser(Protocol):
    """Protocol for book parsers."""

    def parse(self, file_path: Path) -> Book:
        """Parse a book file and return a Book object."""
        ...


def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    # Normalize whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    # Normalize line breaks
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Strip leading/trailing whitespace from lines
    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join(lines).strip()
