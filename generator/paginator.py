"""Text pagination for small screens."""

import textwrap
from dataclasses import dataclass

from config import FONT_SIZES, DEFAULT_FONT_SIZE


@dataclass
class Page:
    """A single page of text."""
    number: int  # 1-indexed page number
    content: str
    chapter_index: int
    chapter_title: str
    is_chapter_start: bool = False  # True if this is the first page of a chapter


class Paginator:
    """Splits book chapters into pages for small screens."""

    def __init__(self, font_size: str = DEFAULT_FONT_SIZE):
        """Initialize paginator with font size settings.

        Args:
            font_size: One of 'small', 'medium', 'large'
        """
        self.settings = FONT_SIZES.get(font_size, FONT_SIZES[DEFAULT_FONT_SIZE])
        self.chars_per_line = self.settings['chars_per_line']
        self.lines_per_page = self.settings['lines_per_page']

    def paginate_text(self, text: str, chapter_index: int, chapter_title: str) -> list[Page]:
        """Split text into pages.

        Args:
            text: The text content to paginate
            chapter_index: Index of the chapter
            chapter_title: Title of the chapter

        Returns:
            List of Page objects
        """
        # Remove chapter title from the beginning of text (it will be shown separately)
        text = text.strip()
        if text.lower().startswith(chapter_title.lower()):
            text = text[len(chapter_title):].strip()

        # Split into paragraphs
        paragraphs = text.split('\n\n')

        # Wrap each paragraph and collect lines
        all_lines: list[str] = []

        for para in paragraphs:
            para = para.strip()
            if not para:
                all_lines.append('')  # Preserve paragraph breaks
                continue

            # Handle multi-line content within paragraph (like poems)
            para_lines = para.split('\n')

            for line in para_lines:
                line = line.strip()
                if not line:
                    all_lines.append('')
                    continue

                # Wrap long lines to fit screen width
                wrapped = textwrap.wrap(
                    line,
                    width=self.chars_per_line,
                    break_long_words=True,
                    break_on_hyphens=True,
                )

                if wrapped:
                    all_lines.extend(wrapped)
                else:
                    all_lines.append('')

            # Add paragraph separator
            all_lines.append('')

        # Remove trailing empty lines
        while all_lines and all_lines[-1] == '':
            all_lines.pop()

        # Group lines into pages
        pages: list[Page] = []
        current_lines: list[str] = []
        page_number = 1
        is_first_page = True

        # First page has fewer lines because of chapter heading
        lines_for_first_page = max(1, self.lines_per_page - 3)

        for line in all_lines:
            current_lines.append(line)

            max_lines = lines_for_first_page if is_first_page else self.lines_per_page
            if len(current_lines) >= max_lines:
                # Strip leading/trailing empty lines from content
                while current_lines and current_lines[0] == '':
                    current_lines.pop(0)
                while current_lines and current_lines[-1] == '':
                    current_lines.pop()

                if current_lines:
                    pages.append(Page(
                        number=page_number,
                        content='\n'.join(current_lines),
                        chapter_index=chapter_index,
                        chapter_title=chapter_title,
                        is_chapter_start=is_first_page,
                    ))
                    page_number += 1
                    is_first_page = False

                current_lines = []

        # Don't forget the last page
        if current_lines:
            while current_lines and current_lines[0] == '':
                current_lines.pop(0)
            while current_lines and current_lines[-1] == '':
                current_lines.pop()

            if current_lines:
                pages.append(Page(
                    number=page_number,
                    content='\n'.join(current_lines),
                    chapter_index=chapter_index,
                    chapter_title=chapter_title,
                    is_chapter_start=is_first_page,
                ))

        return pages

    def paginate_book(self, chapters: list) -> list[Page]:
        """Paginate all chapters of a book.

        Args:
            chapters: List of Chapter objects

        Returns:
            List of all pages across all chapters
        """
        all_pages: list[Page] = []
        global_page_number = 1

        for chapter in chapters:
            chapter_pages = self.paginate_text(
                chapter.content,
                chapter.index,
                chapter.title,
            )

            # Renumber pages globally
            for page in chapter_pages:
                page.number = global_page_number
                global_page_number += 1
                all_pages.append(page)

        return all_pages

    def get_chapter_page_ranges(self, pages: list[Page]) -> dict[int, tuple[int, int]]:
        """Get page ranges for each chapter.

        Args:
            pages: List of all pages

        Returns:
            Dict mapping chapter_index to (first_page, last_page) tuple
        """
        ranges: dict[int, tuple[int, int]] = {}

        for page in pages:
            ch_idx = page.chapter_index
            if ch_idx not in ranges:
                ranges[ch_idx] = (page.number, page.number)
            else:
                first, _ = ranges[ch_idx]
                ranges[ch_idx] = (first, page.number)

        return ranges
