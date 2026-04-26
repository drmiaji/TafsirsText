#!/usr/bin/env python3
"""
convert_tafsir_quotes.py

Converts Urdu tafsir pipe-quote patterns like:
    |" Arabic text |"
    |" Arabic text "|
    |' Arabic text |'
    etc.

Into Persian-style Quranic brackets:
    ﴿Arabic text﴾

Only converts content that is Arabic (Quranic) text.
Urdu content inside pipe-quotes is left unchanged.

How Arabic vs Urdu is detected:
  - Arabic Quranic text contains diacritics (harakat) like fatha, damma,
    kasra, shadda, sukun (U+064B-U+065F) or superscript alef (U+0670).
    These are heavily used in the Quran but almost never in Urdu prose.
  - Urdu text contains Urdu-specific letters like ٹ ڈ ڑ ں ھ ے
    (U+0679, U+0688, U+0691, U+06BA, U+06BE, U+06D2)
    which never appear in Arabic. Note: ہ (U+06C1) is excluded from
    this list because it appears in the Urdu-script spelling of Allah.

Usage:
    python convert_tafsir_quotes.py --input /path/to/tafsir/folder
    python convert_tafsir_quotes.py --input /path/to/single_file.json
    python convert_tafsir_quotes.py --input /path/to/folder --dry-run
"""

import re
import json
import argparse
import sys
from pathlib import Path


# Regex: match all known pipe-quote variants (with or without spaces)
PIPE_QUOTE_PATTERN = re.compile(
    r'\|'                        # opening pipe
    r'["\'\u201C\u201D]'        # opening quote (any variant)
    r'\s*'                       # optional space after opening quote
    r'(.+?)'                     # captured content (lazy)
    r'\s*'                       # optional space before closing pipe/quote
    r'\|?'                       # optional closing pipe (before quote)
    r'["\'\u201C\u201D]'        # closing quote (any variant)
    r'\|?',                      # optional closing pipe (after quote)
    re.DOTALL
)

OPEN_BRACKET  = '﴿'  # U+FD3F
CLOSE_BRACKET = '﴾'  # U+FD3E

# Arabic diacritics (harakat) + superscript alef:
# heavily used in Quran, almost never in Urdu prose
ARABIC_DIACRITICS = re.compile(r'[\u064B-\u065F\u0670]')

# Urdu-specific letters not present in Arabic.
# Note: U+06C1 (ہ) is intentionally excluded — it appears in
# the Urdu-script spelling of Allah (اللہ) in Quranic text.
URDU_SPECIFIC = re.compile(r'[\u0679\u0688\u0691\u06BA\u06BE\u06D2]')


def is_arabic_quran(text: str) -> bool:
    """
    Return True if the text is Arabic Quranic content.
      - Contains Urdu-specific letters → Urdu → False
      - Contains Arabic diacritics     → Arabic → True
      - Otherwise                      → unclear, skip → False
    """
    if URDU_SPECIFIC.search(text):
        return False
    if ARABIC_DIACRITICS.search(text):
        return True
    return False


def convert_text(text: str) -> tuple:
    """
    Convert pipe-quote patterns containing Arabic text to bracket style.
    Returns (converted_text, number_of_replacements).
    """
    count = 0

    def replacer(match):
        nonlocal count
        inner = match.group(1).strip()
        count += 1
        if is_arabic_quran(inner):
            return f'{OPEN_BRACKET}{inner}{CLOSE_BRACKET}'
        # Urdu/other text: remove pipes, wrap in plain curly quotes
        return f'\u201c{inner}\u201d'

    result = PIPE_QUOTE_PATTERN.sub(replacer, text)
    return result, count


def process_json_file(filepath: Path, dry_run: bool = False) -> tuple:
    """
    Process a single JSON file.
    Returns (verses_changed, total_replacements).
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f'  x Skipped (parse error): {filepath.name} - {e}')
        return 0, 0

    verses_changed     = 0
    total_replacements = 0
    modified           = False

    verses = data.get('verses', {})
    for verse_key, verse_data in verses.items():
        if not isinstance(verse_data, dict):
            continue
        text = verse_data.get('text', '')
        if not isinstance(text, str) or not text:
            continue

        converted, count = convert_text(text)
        if count > 0:
            verse_data['text'] = converted
            verses_changed     += 1
            total_replacements += count
            modified           = True

    if modified and not dry_run:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    return verses_changed, total_replacements


def process_path(input_path: str, dry_run: bool = False):
    """Process a file or directory of JSON files."""
    path = Path(input_path)

    if not path.exists():
        print(f'Error: path does not exist: {input_path}')
        sys.exit(1)

    if path.is_file():
        json_files = [path] if path.suffix == '.json' else []
    else:
        json_files = sorted(path.rglob('*.json'))

    if not json_files:
        print('No JSON files found.')
        return

    print(f'{"[DRY RUN] " if dry_run else ""}Processing {len(json_files)} file(s)...\n')

    total_files_changed  = 0
    total_verses_changed = 0
    total_replacements   = 0

    for json_file in json_files:
        verses_changed, replacements = process_json_file(json_file, dry_run)
        if verses_changed > 0:
            total_files_changed  += 1
            total_verses_changed += verses_changed
            total_replacements   += replacements
            status = '[DRY RUN] would update' if dry_run else 'updated'
            print(f'  + {status}: {json_file.name} '
                  f'({verses_changed} verse(s), {replacements} replacement(s))')

    print(f'\n{"--" * 25}')
    print(f'Files changed  : {total_files_changed}')
    print(f'Verses changed : {total_verses_changed}')
    print(f'Replacements   : {total_replacements}')
    if dry_run:
        print('\n[DRY RUN] No files were modified. Remove --dry-run to apply.')
    else:
        print('\nDone. All files updated in place.')


def main():
    parser = argparse.ArgumentParser(
        description='Convert Urdu tafsir pipe-quote patterns to bracket style.'
    )
    parser.add_argument('--input', '-i', required=True,
        help='Path to a single JSON file or a folder containing JSON files')
    parser.add_argument('--dry-run', action='store_true',
        help='Preview changes without modifying any files')
    args = parser.parse_args()
    process_path(args.input, dry_run=args.dry_run)


if __name__ == '__main__':
    main()