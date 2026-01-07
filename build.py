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
import re
import sys
from pathlib import Path

from config import BOOKS_DIR, OUTPUT_DIR


from parsers import EpubParser, Fb2Parser
from parsers.base import Book, Series
from generator import Renderer


def natural_sort_key(text: str) -> list:
    """Sort key for natural sorting (Том 1, Том 2, ..., Том 10)."""
    parts = re.split(r'(\d+)', text.lower())
    return [int(p) if p.isdigit() else p for p in parts]


def discover_books_by_series(books_dir: Path) -> dict[str, list[Path]]:
    """Find all EPUB and FB2 files, grouped by series (subfolder).

    Returns:
        Dict mapping series name to list of book paths.
        Empty string key "" means standalone books (in root folder).
    """
    series_books: dict[str, list[Path]] = {}

    if not books_dir.exists():
        print(f"Warning: Books directory '{books_dir}' does not exist.")
        return series_books

    # Books in root folder (no series)
    root_books = []
    for pattern in ['*.epub', '*.fb2']:
        root_books.extend(books_dir.glob(pattern))
    if root_books:
        root_books.sort(key=lambda p: p.name.lower())
        series_books[""] = root_books

    # Books in subfolders (series)
    for subfolder in sorted(books_dir.iterdir()):
        if subfolder.is_dir() and not subfolder.name.startswith('.'):
            folder_books = []
            for pattern in ['*.epub', '*.fb2']:
                folder_books.extend(subfolder.glob(pattern))
            if folder_books:
                folder_books.sort(key=lambda p: p.name.lower())
                series_books[subfolder.name] = folder_books

    return series_books


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

    # Discover books grouped by series
    print("Scanning for books...")
    series_files = discover_books_by_series(args.books_dir)

    if not series_files:
        print("No books found!")
        print(f"Add EPUB or FB2 files to: {args.books_dir}")
        sys.exit(0)

    total_books = sum(len(files) for files in series_files.values())
    print(f"Found {total_books} book(s) in {len(series_files)} series/folder(s)")
    print()

    # Parse books and create series
    print("Parsing books...")
    series_list: list[Series] = []
    all_books: list[Book] = []

    for series_name, file_paths in series_files.items():
        if series_name:
            print(f"  Series: {series_name}")
        else:
            print("  Standalone books:")

        series_books: list[Book] = []
        for file_path in file_paths:
            print(f"    Parsing: {file_path.name}")
            book = parse_book(file_path)
            if book:
                series_books.append(book)
                all_books.append(book)
                print(f"      - {book.title} by {book.author}")
                print(f"      - {book.total_chapters} chapter(s)")

        if series_books:
            # Sort books in series by title (natural sort for numbers)
            series_books.sort(key=lambda b: natural_sort_key(b.title))
            series_list.append(Series(name=series_name, books=series_books))

    if not all_books:
        print("No books were successfully parsed!")
        sys.exit(1)

    # Sort series alphabetically (standalone books "" come first)
    series_list.sort(key=lambda s: (s.name != "", s.name.lower()))

    print()

    # Generate site
    print("Generating site...")
    renderer = Renderer(output_dir=args.output_dir)
    renderer.render_site(series_list, all_books)

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
