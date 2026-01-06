"""HTML renderer using Jinja2 templates."""

from pathlib import Path
import shutil

from jinja2 import Environment, FileSystemLoader

from config import TEMPLATES_DIR, STATIC_DIR, OUTPUT_DIR, FONT_SIZES, NAV_KEYS
from parsers.base import Book
from .paginator import Page, Paginator


class Renderer:
    """Renders books to static HTML files."""

    def __init__(self, output_dir: Path = OUTPUT_DIR):
        """Initialize renderer with Jinja2 environment."""
        self.output_dir = output_dir
        self.env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            autoescape=True,
        )

        # Add global template variables
        self.env.globals['nav_keys'] = NAV_KEYS
        self.env.globals['font_sizes'] = FONT_SIZES

    def render_site(self, books: list[Book]) -> None:
        """Render the entire site.

        Args:
            books: List of parsed Book objects
        """
        # Clean and create output directory
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True)

        # Copy static files
        self._copy_static_files()

        # Render index page
        self._render_index(books)

        # Render each book
        for book in books:
            self._render_book(book)

        print(f"Site generated at: {self.output_dir}")

    def _copy_static_files(self) -> None:
        """Copy static files to output directory."""
        if STATIC_DIR.exists():
            for file in STATIC_DIR.iterdir():
                if file.is_file():
                    shutil.copy(file, self.output_dir / file.name)

    def _render_index(self, books: list[Book]) -> None:
        """Render the index page with book list."""
        template = self.env.get_template('index.html')
        html = template.render(books=books)

        (self.output_dir / 'index.html').write_text(html, encoding='utf-8')

    def _render_book(self, book: Book) -> None:
        """Render all pages for a single book."""
        book_dir = self.output_dir / book.slug
        book_dir.mkdir(parents=True, exist_ok=True)

        # Paginate the book
        paginator = Paginator()
        pages = paginator.paginate_book(book.chapters)
        chapter_ranges = paginator.get_chapter_page_ranges(pages)

        total_pages = len(pages)

        # Render TOC
        self._render_toc(book, book_dir, chapter_ranges)

        # Render each page
        page_template = self.env.get_template('page.html')

        for i, page in enumerate(pages):
            prev_page = i if i > 0 else None  # Previous page number (1-indexed)
            next_page = i + 2 if i < total_pages - 1 else None  # Next page number

            html = page_template.render(
                book=book,
                page=page,
                total_pages=total_pages,
                prev_page=prev_page,
                next_page=next_page,
                chapter_ranges=chapter_ranges,
            )

            page_file = book_dir / f'{page.number}.html'
            page_file.write_text(html, encoding='utf-8')

        print(f"  - {book.title}: {total_pages} pages")

    def _render_toc(
        self,
        book: Book,
        book_dir: Path,
        chapter_ranges: dict[int, tuple[int, int]],
    ) -> None:
        """Render table of contents page."""
        template = self.env.get_template('toc.html')

        # Prepare TOC entries with page numbers
        toc_with_pages = []
        for entry in book.toc:
            page_range = chapter_ranges.get(entry.chapter_index, (1, 1))
            toc_with_pages.append({
                'title': entry.title,
                'level': entry.level,
                'first_page': page_range[0],
            })

        html = template.render(
            book=book,
            toc=toc_with_pages,
        )

        (book_dir / 'toc.html').write_text(html, encoding='utf-8')
