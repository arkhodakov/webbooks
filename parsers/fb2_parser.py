"""FB2 (FictionBook) format parser."""

from pathlib import Path
import xml.etree.ElementTree as ET
import re

from .base import Book, Chapter, TocEntry, clean_text


# FB2 namespace
FB2_NS = '{http://www.gribuser.ru/xml/fictionbook/2.0}'


class Fb2Parser:
    """Parser for FB2 format books."""

    def parse(self, file_path: Path) -> Book:
        """Parse an FB2 file and return a Book object."""
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Handle namespace
        ns = self._detect_namespace(root)

        # Extract metadata
        title, author = self._extract_metadata(root, ns)
        if not title:
            title = file_path.stem

        # Extract chapters
        chapters = self._extract_chapters(root, ns)

        # Build TOC from chapters
        toc = [
            TocEntry(title=ch.title, chapter_index=ch.index, level=0)
            for ch in chapters
        ]

        return Book(
            title=title,
            author=author,
            file_path=file_path,
            chapters=chapters,
            toc=toc,
        )

    def _detect_namespace(self, root: ET.Element) -> str:
        """Detect the FB2 namespace from root element."""
        tag = root.tag
        if tag.startswith('{'):
            return tag.split('}')[0] + '}'
        return ''

    def _extract_metadata(self, root: ET.Element, ns: str) -> tuple[str, str]:
        """Extract title and author from FB2 metadata."""
        title = ""
        author = "Unknown"

        description = root.find(f'{ns}description')
        if description is not None:
            title_info = description.find(f'{ns}title-info')
            if title_info is not None:
                # Book title
                book_title = title_info.find(f'{ns}book-title')
                if book_title is not None and book_title.text:
                    title = book_title.text.strip()

                # Author
                author_elem = title_info.find(f'{ns}author')
                if author_elem is not None:
                    author = self._extract_author_name(author_elem, ns)

        return title, author

    def _extract_author_name(self, author_elem: ET.Element, ns: str) -> str:
        """Extract author name from author element."""
        parts = []

        for field in ['first-name', 'middle-name', 'last-name']:
            elem = author_elem.find(f'{ns}{field}')
            if elem is not None and elem.text:
                parts.append(elem.text.strip())

        if parts:
            return ' '.join(parts)

        # Fallback to nickname
        nickname = author_elem.find(f'{ns}nickname')
        if nickname is not None and nickname.text:
            return nickname.text.strip()

        return "Unknown"

    def _extract_chapters(self, root: ET.Element, ns: str) -> list[Chapter]:
        """Extract chapters from FB2 body."""
        chapters = []

        for body in root.findall(f'{ns}body'):
            # Skip notes body
            body_name = body.get('name', '')
            if body_name == 'notes':
                continue

            sections = body.findall(f'{ns}section')

            if sections:
                # Process sections as chapters
                for i, section in enumerate(sections):
                    chapter = self._process_section(section, ns, len(chapters))
                    if chapter:
                        chapters.append(chapter)
            else:
                # No sections, treat entire body as one chapter
                content = self._extract_section_text(body, ns)
                if content.strip():
                    chapters.append(Chapter(
                        title="Main",
                        content=clean_text(content),
                        index=0,
                    ))

        return chapters

    def _process_section(self, section: ET.Element, ns: str, index: int) -> Chapter | None:
        """Process a single section into a chapter."""
        # Get section title
        title_elem = section.find(f'{ns}title')
        if title_elem is not None:
            title = self._extract_element_text(title_elem, ns)
        else:
            title = f"Chapter {index + 1}"

        # Get section content
        content = self._extract_section_text(section, ns)

        if not content.strip():
            return None

        return Chapter(
            title=title.strip() or f"Chapter {index + 1}",
            content=clean_text(content),
            index=index,
        )

    def _extract_section_text(self, section: ET.Element, ns: str) -> str:
        """Extract text content from a section."""
        paragraphs = []

        for elem in section:
            tag = elem.tag.replace(ns, '')

            if tag == 'p':
                text = self._extract_element_text(elem, ns)
                if text:
                    paragraphs.append(text)
            elif tag == 'empty-line':
                paragraphs.append('')
            elif tag == 'subtitle':
                text = self._extract_element_text(elem, ns)
                if text:
                    paragraphs.append(f"\n{text}\n")
            elif tag == 'poem':
                poem_text = self._extract_poem(elem, ns)
                if poem_text:
                    paragraphs.append(poem_text)
            elif tag == 'cite':
                cite_text = self._extract_cite(elem, ns)
                if cite_text:
                    paragraphs.append(cite_text)
            # Skip: title, epigraph, image, annotation, section (nested)

        return '\n\n'.join(paragraphs)

    def _extract_element_text(self, elem: ET.Element, ns: str) -> str:
        """Extract all text from an element, including nested elements."""
        texts = []

        if elem.text:
            texts.append(elem.text)

        for child in elem:
            child_tag = child.tag.replace(ns, '')

            # Handle inline elements
            if child_tag in ('strong', 'emphasis', 'strikethrough', 'a'):
                texts.append(self._extract_element_text(child, ns))

            if child.tail:
                texts.append(child.tail)

        return ''.join(texts).strip()

    def _extract_poem(self, poem: ET.Element, ns: str) -> str:
        """Extract poem content."""
        lines = []

        for stanza in poem.findall(f'{ns}stanza'):
            for v in stanza.findall(f'{ns}v'):
                text = self._extract_element_text(v, ns)
                if text:
                    lines.append(text)
            lines.append('')  # Empty line between stanzas

        return '\n'.join(lines).strip()

    def _extract_cite(self, cite: ET.Element, ns: str) -> str:
        """Extract citation content."""
        paragraphs = []

        for p in cite.findall(f'{ns}p'):
            text = self._extract_element_text(p, ns)
            if text:
                paragraphs.append(f"  {text}")  # Indent citations

        # Add text-author if present
        author = cite.find(f'{ns}text-author')
        if author is not None:
            author_text = self._extract_element_text(author, ns)
            if author_text:
                paragraphs.append(f"  — {author_text}")

        return '\n'.join(paragraphs)
