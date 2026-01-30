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

        # Extract cover image
        cover_data, cover_ext = self._extract_cover(book)

        return Book(
            title=title,
            author=author,
            file_path=file_path,
            chapters=chapters,
            toc=toc,
            cover_data=cover_data,
            cover_ext=cover_ext,
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
        """Extract all chapters from EPUB using spine order."""
        chapters = []
        index = 0

        # Use spine to get correct reading order
        for spine_item in book.spine:
            item_id = spine_item[0]
            item = book.get_item_with_id(item_id)

            if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
                continue

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
        for tag in ['h1', 'h2', 'h3']:
            element = soup.find(tag)
            if element:
                return element.get_text(strip=True)

        # Try div/p with title class (common in FB2-converted EPUBs)
        for selector in ['div.title1', 'div.title', 'p.title', '.title']:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)

        # Try first paragraph if it looks like a chapter title
        first_p = soup.find('p')
        if first_p:
            text = first_p.get_text(strip=True)
            # Check if it looks like a chapter title (short, starts with common patterns)
            if len(text) < 50 and any(text.lower().startswith(p) for p in
                ['глава', 'chapter', 'часть', 'part', 'пролог', 'эпилог', 'prologue', 'epilogue', 'введение', 'заключение']):
                return text

        return None

    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract plain text from HTML content."""
        # Remove script and style elements
        for element in soup(['script', 'style', 'head', 'meta', 'link']):
            element.decompose()

        # Get text with paragraph breaks
        paragraphs = []
        prev_text = None

        for p in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            # Use separator to preserve spaces between inline elements
            text = p.get_text(separator=' ', strip=True)
            if text and text != prev_text:  # Skip duplicates
                paragraphs.append(text)
                prev_text = text

        # Check if we have actual content (not just headers)
        non_header_content = [p for p in paragraphs
                             if len(p) > 100 or not any(p.lower().startswith(x)
                             for x in ['глава', 'chapter', 'часть', 'part'])]

        if non_header_content:
            return '\n\n'.join(paragraphs)

        # Fallback: Handle HTML with <br/> tags instead of <p>
        # Replace <br> tags with newlines, then get text
        body = soup.find('body')
        if body:
            # Convert <br> to newlines
            for br in body.find_all('br'):
                br.replace_with('\n')

            # Get text and split by newlines
            text = body.get_text()
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if lines:
                return '\n\n'.join(lines)

        # Last fallback
        return soup.get_text(separator=' ')

    def _extract_toc(self, book: epub.EpubBook, chapters: list[Chapter]) -> list[TocEntry]:
        """Extract table of contents from EPUB."""
        # Build a map from href to chapter index
        # We need to track which spine items became actual chapters
        href_to_chapter: dict[str, int] = {}

        chapter_idx = 0
        for spine_item in book.spine:
            item_id = spine_item[0]
            item = book.get_item_with_id(item_id)
            if item and item.get_type() == ebooklib.ITEM_DOCUMENT:
                # Check if this item has content (was included as a chapter)
                content = item.get_content().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(content, 'lxml')
                text = soup.get_text(strip=True)

                if text:  # Only count non-empty items
                    href = item.get_name()
                    href_to_chapter[href] = chapter_idx
                    # Also store just the filename
                    if '/' in href:
                        href_to_chapter[href.split('/')[-1]] = chapter_idx
                    chapter_idx += 1

        # Also create a map by chapter title for fallback
        title_to_chapter = {ch.title.lower(): ch.index for ch in chapters}

        toc_entries = []

        def find_chapter_index(item) -> int:
            """Find chapter index from TOC item href or title."""
            # Try href first
            if hasattr(item, 'href') and item.href:
                href = item.href.split('#')[0]  # Remove fragment
                if href in href_to_chapter:
                    return href_to_chapter[href]
                # Try just filename
                filename = href.split('/')[-1]
                if filename in href_to_chapter:
                    return href_to_chapter[filename]

            # Fallback to title matching
            if hasattr(item, 'title') and item.title:
                title_lower = item.title.lower()
                if title_lower in title_to_chapter:
                    return title_to_chapter[title_lower]
                # Partial match
                for ch_title, ch_idx in title_to_chapter.items():
                    if title_lower in ch_title or ch_title in title_lower:
                        return ch_idx

            return 0

        def process_toc_item(item, level=0):
            if isinstance(item, tuple):
                # Section with children
                section, children = item
                if hasattr(section, 'title'):
                    chapter_idx = find_chapter_index(section)
                    toc_entries.append(TocEntry(
                        title=section.title,
                        chapter_index=chapter_idx,
                        level=level,
                    ))
                for child in children:
                    process_toc_item(child, level + 1)
            elif hasattr(item, 'title'):
                # Simple link
                chapter_idx = find_chapter_index(item)
                toc_entries.append(TocEntry(
                    title=item.title,
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

    def _extract_cover(self, book: epub.EpubBook) -> tuple[bytes | None, str]:
        """Extract cover image from EPUB."""
        # Method 1: Look for cover in metadata
        cover_id = None
        try:
            meta = book.get_metadata('OPF', 'cover')
            if meta:
                cover_id = meta[0][0]
        except (IndexError, KeyError):
            pass

        # Method 2: Look for item with cover-image property
        if not cover_id:
            for item in book.get_items():
                if hasattr(item, 'get_name'):
                    name = item.get_name().lower()
                    if 'cover' in name and item.get_type() == ebooklib.ITEM_IMAGE:
                        cover_id = item.get_id()
                        break

        # Get the cover image by ID
        if cover_id:
            cover_item = book.get_item_with_id(cover_id)
            if cover_item:
                data = cover_item.get_content()
                # Determine extension from media type or filename
                media_type = getattr(cover_item, 'media_type', '') or ''
                if 'jpeg' in media_type or 'jpg' in media_type:
                    ext = 'jpg'
                elif 'png' in media_type:
                    ext = 'png'
                elif 'gif' in media_type:
                    ext = 'gif'
                else:
                    # Try from filename
                    name = cover_item.get_name().lower()
                    if name.endswith('.png'):
                        ext = 'png'
                    elif name.endswith('.gif'):
                        ext = 'gif'
                    else:
                        ext = 'jpg'
                return data, ext

        # Method 3: Look for any image with "cover" in the name
        for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
            name = item.get_name().lower()
            if 'cover' in name:
                data = item.get_content()
                ext = 'png' if name.endswith('.png') else 'jpg'
                return data, ext

        return None, ""
