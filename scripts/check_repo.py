"""Lint the repository for data-quality issues.

Checks:
  1. Per-category app counts match the README categories table.
  2. The "Total Apps" badge matches the sum of category counts.
  3. No app is listed more than once within the same category file.
  4. Reports apps that appear in multiple categories (informational — cross-listing
     is sometimes intentional, e.g. NewPipe under both Multi-Media and News).

Exit code is non-zero when any hard error (checks 1-3) is found, so this can be
used to gate CI. Run it from the repo root:  python scripts/check_repo.py
"""

import os
import re
import sys

from maintain_repo import count_apps_in_category

CATEGORIES_DIR = 'categories'
README_PATH = 'README.md'


def read_category_counts():
    """Return {filename: app_count} for every category file on disk."""
    counts = {}
    for filename in sorted(os.listdir(CATEGORIES_DIR)):
        if filename.endswith('.md'):
            path = os.path.join(CATEGORIES_DIR, filename)
            counts[filename] = count_apps_in_category(path)
    return counts


def parse_readme_counts():
    """Return {filename: count} as currently stated in the README categories table."""
    counts = {}
    row_re = re.compile(r'\]\(categories/([^)]+\.md)\) \| [^|]* \| (\d+) \|')
    with open(README_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            m = row_re.search(line)
            if m:
                counts[m.group(1)] = int(m.group(2))
    return counts


def parse_readme_badge_total():
    with open(README_PATH, 'r', encoding='utf-8') as f:
        text = f.read()
    m = re.search(r'Total%20Apps-(\d+)-brightgreen', text)
    return int(m.group(1)) if m else None


def find_duplicates():
    """Scan every category file for app names.

    Returns (cross_category, within_file) where cross_category maps an app name
    to the sorted list of files it appears in, and within_file lists
    (filename, name) pairs duplicated inside the same file.
    """
    locations = {}
    within_file = []
    name_re = re.compile(r'^\| \[\*\*([^*]+)\*\*\]')
    for filename in sorted(os.listdir(CATEGORIES_DIR)):
        if not filename.endswith('.md'):
            continue
        path = os.path.join(CATEGORIES_DIR, filename)
        seen_here = set()
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                m = name_re.match(line.strip())
                if not m:
                    continue
                name = m.group(1)
                locations.setdefault(name, set()).add(filename)
                if name in seen_here:
                    within_file.append((filename, name))
                seen_here.add(name)
    cross = {name: sorted(files) for name, files in locations.items() if len(files) > 1}
    return cross, within_file


def main():
    errors = 0
    warnings = 0

    actual = read_category_counts()
    readme_counts = parse_readme_counts()

    print("== Per-category counts (README vs actual) ==")
    for filename, count in sorted(actual.items()):
        stated = readme_counts.get(filename)
        if stated is None:
            print(f"  [WARN] {filename}: not listed in README categories table")
            warnings += 1
        elif stated != count:
            print(f"  [FAIL] {filename}: README says {stated}, actual {count}")
            errors += 1
        else:
            print(f"  [ OK ] {filename}: {count}")
    for filename in readme_counts:
        if filename not in actual:
            print(f"  [FAIL] {filename}: listed in README but file is missing")
            errors += 1

    total = sum(actual.values())
    badge = parse_readme_badge_total()
    print("\n== Total Apps badge ==")
    if badge is None:
        print("  [WARN] Total Apps badge not found in README")
        warnings += 1
    elif badge != total:
        print(f"  [FAIL] badge says {badge}, actual total {total}")
        errors += 1
    else:
        print(f"  [ OK ] badge {badge} == total {total}")

    cross, within_file = find_duplicates()
    print("\n== Duplicate entries ==")
    if within_file:
        for filename, name in within_file:
            print(f"  [FAIL] {filename}: '{name}' listed more than once")
            errors += 1
    else:
        print("  [ OK ] no within-file duplicates")

    if cross:
        print("  [INFO] apps appearing in multiple categories (allowed if intentional):")
        for name, files in sorted(cross.items()):
            print(f"    - {name}: {', '.join(files)}")
        warnings += 1

    print(f"\n{errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
