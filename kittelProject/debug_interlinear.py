import json, gzip
with gzip.open(r'C:\Users\LAPTOP\OneDrive - dts.edu\proyectos_programacion\ebp\kittelProject\interlinear.json.gz', 'rt', encoding='utf-8') as f:
    d = json.load(f)

v = d.get('G\u00e9nesis 1:1')
print('Found:', v is not None)
if v:
    for i, w in enumerate(v['words']):
        wsurf = w['surface'].encode('unicode_escape').decode('ascii')
        print(f"  [{i:2d}] '{wsurf}' strong={w['strong']} orig={w['original'][:30].encode('unicode_escape').decode('ascii')}")