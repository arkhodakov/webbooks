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

        # Save cover image if available
        has_cover = False
        if book.cover_data and book.cover_ext:
            cover_filename = f"cover.{book.cover_ext}"
            (book_dir / cover_filename).write_bytes(book.cover_data)
            has_cover = True

        # Paginate the book
        paginator = Paginator()
        pages = paginator.paginate_book(book.chapters)
        chapter_ranges = paginator.get_chapter_page_ranges(pages)

        total_pages = len(pages)

        # Render cover page (page 0) if cover exists
        if has_cover:
            self._render_cover_page(book, book_dir, cover_filename, total_pages)

        # Render TOC
        self._render_toc(book, book_dir, chapter_ranges, has_cover)

        # Render each page
        page_template = self.env.get_template('page.html')

        for i, page in enumerate(pages):
            # Previous page: 0 (cover) for page 1 if cover exists, else normal
            if page.number == 1:
                prev_page = 0 if has_cover else None
            else:
                prev_page = page.number - 1

            next_page = page.number + 1 if i < total_pages - 1 else None

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

        print(f"  - {book.title}: {total_pages} pages" + (" + cover" if has_cover else ""))

    def _render_cover_page(
        self,
        book: Book,
        book_dir: Path,
        cover_filename: str,
        total_pages: int,
    ) -> None:
        """Render cover page (page 0)."""
        template = self.env.get_template('cover.html')
        html = template.render(
            book=book,
            cover_filename=cover_filename,
            total_pages=total_pages,
        )
        (book_dir / '0.html').write_text(html, encoding='utf-8')

    def _render_toc(
        self,
        book: Book,
        book_dir: Path,
        chapter_ranges: dict[int, tuple[int, int]],
        has_cover: bool = False,
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
            has_cover=has_cover,
        )

        (book_dir / 'toc.html').write_text(html, encoding='utf-8')
