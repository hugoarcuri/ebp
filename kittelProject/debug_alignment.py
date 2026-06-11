import json, gzip, os

SRC = r'C:\Users\LAPTOP\OneDrive - dts.edu\proyectos_programacion\ebp\kittelProject\source_data'

# Check alignment for Genesis 1:1 (BCVWP book 1)
def parse_bcvvp(bcvvp_id):
    s = bcvvp_id.lstrip('n')
    if len(s) != 11: return None
    return (int(s[0:2]), int(s[2:5]), int(s[5:8]), int(s[8:11]))

with open(os.path.join(SRC, 'WLCM-RV09-manual.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)
recs = data.get('records', [])

# Find Gen 1:1 records
gen11 = []
for rec in recs:
    src = rec.get('source', [])
    tgt = rec.get('target', [])
    if not src or not tgt: continue
    s = parse_bcvvp(src[0])
    t = parse_bcvvp(tgt[0])
    if s and t and s[0]==1 and s[1]==1 and s[2]==1:
        gen11.append((src, tgt))

print(f"Gen 1:1 alignment records: {len(gen11)}")
for src, tgt in gen11[:5]:
    s = parse_bcvvp(src[0]) if src else None
    t = parse_bcvvp(tgt[0]) if tgt else None
    print(f"  src={src} (b={s[0]} c={s[1]} v={s[2]} w={s[3]}) -> tgt={tgt} (b={t[0]} c={t[1]} v={t[2]} w={t[3]})")

# Check if OSHB has Gen 1:1 words
print("\n--- Checking OSHB Gen 1:1 ---")
import xml.etree.ElementTree as ET
tree = ET.parse(os.path.join(SRC, 'Gen.xml'))
root = tree.getroot()
ns = {'osis': 'http://www.bibletechnologies.net/2003/OSIS/namespace'}
for chapter in root.findall('.//osis:chapter', ns):
    ch_num = int(chapter.get('osisID').split('.')[1])
    if ch_num != 1: continue
    for verse in chapter.findall('.//osis:verse', ns):
        vs_num = int(verse.get('osisID').rsplit('.', 1)[-1])
        if vs_num != 1: continue
        word_pos = 0
        for child in verse:
            local = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if local == 'w':
                word_pos += 1
                lemma = child.get('lemma', '')
                text = ''.join(child.itertext()).strip()
                print(f"  [{word_pos}] lemma={lemma!r} text={text[:30].encode('unicode_escape').decode('ascii')}")
        print(f"  Total words: {word_pos}")
        break
    break