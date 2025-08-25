import polib
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

# Rules:
# - If msgstr is non-empty and not marked obsolete, drop 'fuzzy' flag.
# - If msgstr is empty, keep fuzzy (or leave as-is).
# - Preserve translator comments and references.
# - Work on both ar/en django.po files.

def defuzzy_file(po_path: Path) -> int:
    po = polib.pofile(str(po_path))
    changed = 0
    for entry in po:
        if 'fuzzy' in entry.flags:
            # keep fuzzy if untranslated
            if not entry.msgstr and not entry.msgstr_plural:
                continue
            # if plural, ensure all forms have values
            if entry.msgstr_plural:
                if any(v.strip() == '' for v in entry.msgstr_plural.values()):
                    continue
            # remove fuzzy flag
            entry.flags = [f for f in entry.flags if f != 'fuzzy']
            changed += 1
    if changed:
        po.save(str(po_path))
    return changed


def main():
    total = 0
    for lang in ('ar', 'en'):
        p = BASE / 'locale' / lang / 'LC_MESSAGES' / 'django.po'
        if p.exists():
            changed = defuzzy_file(p)
            print(f"{lang}: removed fuzzy from {changed} entries")
            total += changed
    print(f"Done. Total cleaned: {total}")

if __name__ == '__main__':
    main()
