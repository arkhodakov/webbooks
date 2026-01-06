#!/usr/bin/env python3
"""
WebBooks - Static site generator for reading EPUB/FB2 books on feature phones.

Usage:
    python build.py [--books-dir PATH] [--output-dir PATH]

Example:
    python build.py
    python build.py --books-dir ./my-books --output-dir ./public
"""

import argparse
import sys
from pathlib import Path

from config import BOOKS_DIR, OUTPUT_DIR
from parsers import EpubParser, Fb2Parser
from parsers.base import Book
from generator import Renderer


def discover_books(books_dir: Path) -> list[Path]:
    """Find all EPUB and FB2 files in the books directory."""
    books = []

    if not books_dir.exists():
        print(f"Warning: Books directory '{books_dir}' does not exist.")
        return books

    for pattern in ['*.epub', '*.fb2']:
        books.extend(books_dir.glob(pattern))

    # Sort by filename
    books.sort(key=lambda p: p.name.lower())

    return books


def parse_book(file_path: Path) -> Book | None:
    """Parse a book file using the appropriate parser."""
    suffix = file_path.suffix.lower()

    try:
        if suffix == '.epub':
            parser = EpubParser()
        elif suffix == '.fb2':
            parser = Fb2Parser()
        else:
            print(f"  Skipping unsupported format: {file_path.name}")
            return None

        return parser.parse(file_path)

    except Exception as e:
        print(f"  Error parsing {file_path.name}: {e}")
        return None


def main():
    """Main entry point for the build script."""
    parser = argparse.ArgumentParser(
        description='Generate a static site for reading EPUB/FB2 books.'
    )
    parser.add_argument(
        '--books-dir',
        type=Path,
        default=BOOKS_DIR,
        help=f'Directory containing book files (default: {BOOKS_DIR})',
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=OUTPUT_DIR,
        help=f'Output directory for generated site (default: {OUTPUT_DIR})',
    )

    args = parser.parse_args()

    print("WebBooks - Static Site Generator")
    print("=" * 40)
    print(f"Books directory: {args.books_dir}")
    print(f"Output directory: {args.output_dir}")
    print()

    # Discover books
    print("Scanning for books...")
    book_files = discover_books(args.books_dir)

    if not book_files:
        print("No books found!")
        print(f"Add EPUB or FB2 files to: {args.books_dir}")
        sys.exit(0)

    print(f"Found {len(book_files)} book(s)")
    print()

    # Parse books
    print("Parsing books...")
    books: list[Book] = []

    for file_path in book_files:
        print(f"  Parsing: {file_path.name}")
        book = parse_book(file_path)
        if book:
            books.append(book)
            print(f"    - {book.title} by {book.author}")
            print(f"    - {book.total_chapters} chapter(s)")

    if not books:
        print("No books were successfully parsed!")
        sys.exit(1)

    print()

    # Generate site
    print("Generating site...")
    renderer = Renderer(output_dir=args.output_dir)
    renderer.render_site(books)

    print()
    print("Done!")
    print(f"Open {args.output_dir / 'index.html'} in a browser to preview.")
    print()
    print("To deploy to GitHub Pages:")
    print("  1. git add docs/")
    print("  2. git commit -m 'Update books'")
    print("  3. git push")


if __name__ == '__main__':
    main()
