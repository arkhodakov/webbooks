"""EPUB format parser using ebooklib."""

from pathlib import Path
import warnings

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from .base import Book, Chapter, TocEntry, clean_text

# Suppress XML parsing warning - we're intentionally using HTML parser for EPUB content
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


class EpubParser:
    """Parser for EPUB format books."""

    def parse(self, file_path: Path) -> Book:
        """Parse an EPUB file and return a Book object."""
        book = epub.read_epub(str(file_path))

        # Extract metadata
        title = self._get_metadata(book, 'title') or file_path.stem
        author = self._get_metadata(book, 'creator') or "Unknown"

        # Extract chapters
        chapters = self._extract_chapters(book)

        # Extract table of contents
        toc = self._extract_toc(book, chapters)

        return Book(
            title=title,
            author=author,
            file_path=file_path,
            chapters=chapters,
            toc=toc,
        )

    def _get_metadata(self, book: epub.EpubBook, field: str) -> str | None:
        """Extract metadata field from EPUB."""
        try:
            values = book.get_metadata('DC', field)
            if values:
                return values[0][0]
        except (IndexError, KeyError):
            pass
        return None

    def _extract_chapters(self, book: epub.EpubBook) -> list[Chapter]:
        """Extract all chapters from EPUB."""
        chapters = []
        index = 0

        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                content = item.get_content().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(content, 'lxml')

                # Get chapter title from first heading
                title = self._extract_title(soup) or f"Chapter {index + 1}"

                # Get text content
                text = self._extract_text(soup)

                if text.strip():  # Only add non-empty chapters
                    chapters.append(Chapter(
                        title=title,
                        content=clean_text(text),
                        index=index,
                    ))
                    index += 1

        return chapters

    def _extract_title(self, soup: BeautifulSoup) -> str | None:
        """Extract title from HTML content."""
        # Try h1, h2, h3 in order
        for tag in ['h1', 'h2', 'h3', 'title']:
            element = soup.find(tag)
            if element:
                return element.get_text(strip=True)
        return None

    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract plain text from HTML content."""
        # Remove script and style elements
        for element in soup(['script', 'style', 'head', 'meta', 'link']):
            element.decompose()

        # Get text with paragraph breaks
        paragraphs = []
        for p in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            # Use separator to preserve spaces between inline elements
            text = p.get_text(separator=' ', strip=True)
            if text:
                paragraphs.append(text)

        if paragraphs:
            return '\n\n'.join(paragraphs)

        # Fallback to all text with spaces
        return soup.get_text(separator=' ')

    def _extract_toc(self, book: epub.EpubBook, chapters: list[Chapter]) -> list[TocEntry]:
        """Extract table of contents from EPUB."""
        toc_entries = []
        chapter_titles = {ch.title.lower(): ch.index for ch in chapters}

        def process_toc_item(item, level=0):
            if isinstance(item, tuple):
                # Section with children
                section, children = item
                if hasattr(section, 'title'):
                    title = section.title
                    # Try to find matching chapter
                    chapter_idx = chapter_titles.get(title.lower(), 0)
                    toc_entries.append(TocEntry(
                        title=title,
                        chapter_index=chapter_idx,
                        level=level,
                    ))
                for child in children:
                    process_toc_item(child, level + 1)
            elif hasattr(item, 'title'):
                # Simple link
                title = item.title
                chapter_idx = chapter_titles.get(title.lower(), 0)
                toc_entries.append(TocEntry(
                    title=title,
                    chapter_index=chapter_idx,
                    level=level,
                ))

        for item in book.toc:
            process_toc_item(item)

        # If no TOC found, generate from chapters
        if not toc_entries:
            toc_entries = [
                TocEntry(title=ch.title, chapter_index=ch.index, level=0)
                for ch in chapters
            ]

        return toc_entries
