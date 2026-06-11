import json, os

SRC = r'C:\Users\LAPTOP\OneDrive - dts.edu\proyectos_programacion\ebp\kittelProject\source_data'

def parse_bcvvp(bcvvp_id):
    s = bcvvp_id.lstrip('n')
    if len(s) != 11: return None
    return (int(s[0:2]), int(s[2:5]), int(s[5:8]), int(s[8:11]))

with open(os.path.join(SRC, 'WLCM-RV09-manual.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)
recs = data.get('records', [])

# Find first and last records
print("First 5 records:")
for rec in recs[:5]:
    src = rec.get('source', [])
    tgt = rec.get('target', [])
    s = parse_bcvvp(src[0]) if src else None
    t = parse_bcvvp(tgt[0]) if tgt else None
    if s:
        print(f"  src={src} -> tgt={tgt}  (src: b={s[0]} c={s[1]} v={s[2]} w={s[3]})")
    else:
        print(f"  src={src} -> tgt={tgt}  (src: PARSE_FAIL)")

print("\nLast 5 records:")
for rec in recs[-5:]:
    src = rec.get('source', [])
    tgt = rec.get('target', [])
    s = parse_bcvvp(src[0]) if src else None
    t = parse_bcvvp(tgt[0]) if tgt else None
    if s:
        print(f"  src={src} -> tgt={tgt}  (src: b={s[0]} c={s[1]} v={s[2]} w={s[3]})")
    else:
        print(f"  src={src} -> tgt={tgt}  (src: PARSE_FAIL)")

# Count books in source
books = {}
for rec in recs:
    src = rec.get('source', [])
    if src:
        s = parse_bcvvp(src[0])
        if s:
            b = s[0]
            books[b] = books.get(b, 0) + 1

print("\nBooks in OT alignment:")
for b in sorted(books.keys()):
    print(f"  Book {b}: {books[b]} records")