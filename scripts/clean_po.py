import io
from pathlib import Path

po_path = Path(r"c:\Accounting_soft\finspilot\locale\ar\LC_MESSAGES\django.po")
backup = po_path.with_suffix('.po.bak')
text = po_path.read_text(encoding='utf-8')

# Split into entries by two or more newlines
entries = []
block = []
for line in text.splitlines(True):
    if line.strip() == "" and block:
        entries.append(''.join(block))
        block = []
    else:
        block.append(line)
if block:
    entries.append(''.join(block))

# header is the first entry where msgid "" occurs at start
header = ''
rest = entries
if entries and entries[0].lstrip().startswith('msgid ""'):
    header = entries[0]
    rest = entries[1:]

seen = set()
unique = []
import re
for ent in rest:
    # find msgid block between 'msgid' and the following 'msgstr'
    m = re.search(r'msgid\s+("(?:.|\n)*?")\s*\n', ent)
    # attempt robust extraction: collect all "..." before msgstr
    if 'msgid' in ent:
        before_msgstr = ent.split('msgstr',1)[0]
        quotes = re.findall(r'"([^\"]*)"', before_msgstr)
        msgid_text = ''.join(quotes)
    else:
        msgid_text = None
    if msgid_text is None:
        # keep as is
        unique.append(ent)
    else:
        if msgid_text in seen:
            # skip duplicate
            continue
        seen.add(msgid_text)
        unique.append(ent)

# Write backup and cleaned file
po_path.rename(backup)
with po_path.open('w', encoding='utf-8') as f:
    if header:
        f.write(header.rstrip()+"\n\n")
    f.write('\n\n'.join(u.strip() for u in unique))

print('Cleaned', po_path, 'backup at', backup)
