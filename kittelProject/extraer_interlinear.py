#!/usr/bin/env python3
"""
extraer_interlinear.py — Genera interlinear.json.gz a partir de fuentes reales:
  1. OSHB XML (AT: hebreo con Strong + morfologia)
  2. STEPBible TAGNT (NT: griego con Strong + morfologia)
  3. Clear-Bible Alignments (espanol <-> hebreo/griego)
  4. rv1960.js (texto espanol)

Uso: python extraer_interlinear.py
"""
import json, re, gzip, os, xml.etree.ElementTree as ET
from urllib.request import urlopen

SRC = os.path.join(os.path.dirname(__file__), 'source_data')
OUT_JSON = os.path.join(os.path.dirname(__file__), 'interlinear.json.gz')
OUT_JS = os.path.join(os.path.dirname(__file__), 'interlinear_lookup.js')
OUT_FULL = os.path.join(os.path.dirname(__file__), 'interlinear_full.json.gz')

# OSHB XML filenames in the repo (different from BCVWP abbreviations)
OSHB_FILENAMES = {
    "Gen":"Gen","Exo":"Exod","Lev":"Lev","Num":"Num","Deu":"Deut",
    "Jos":"Josh","Jdg":"Judg","Rut":"Ruth","1Sa":"1Sam","2Sa":"2Sam",
    "1Ki":"1Kgs","2Ki":"2Kgs","1Ch":"1Chr","2Ch":"2Chr","Ezr":"Ezra",
    "Neh":"Neh","Est":"Esth","Job":"Job","Psa":"Ps","Pro":"Prov",
    "Ecc":"Eccl","Sng":"Song","Isa":"Isa","Jer":"Jer","Lam":"Lam",
    "Ezk":"Ezek","Dan":"Dan","Hos":"Hos","Joe":"Joel","Amo":"Amos",
    "Oba":"Obad","Jon":"Jonah","Mic":"Mic","Nah":"Nah","Hab":"Hab",
    "Zep":"Zeph","Hag":"Hag","Zec":"Zech","Mal":"Mal",
}

BCVWP_OT = ["Gen","Exo","Lev","Num","Deu","Jos","Jdg","Rut","1Sa","2Sa",
            "1Ki","2Ki","1Ch","2Ch","Ezr","Neh","Est","Job","Psa","Pro",
            "Ecc","Sng","Isa","Jer","Lam","Ezk","Dan","Hos","Joe","Amo",
            "Oba","Jon","Mic","Nah","Hab","Zep","Hag","Zec","Mal"]
BCVWP_NT = ["Mat","Mrk","Luk","Jhn","Act","Rom","1Co","2Co","Gal","Eph",
            "Phi","Col","1Th","2Th","1Ti","2Ti","Tit","Phm","Heb","Jas",
            "1Pe","2Pe","1Jn","2Jn","3Jn","Jud","Rev"]

# Spanish book names as they appear in BIBLE_DATA / rv1960_books.json
SPANISH_BOOKS = [
    "G\u00e9nesis","\u00c9xodo","Lev\u00edtico","N\u00fameros","Deuteronomio",
    "Josu\u00e9","Jueces","Rut","1 Samuel","2 Samuel",
    "1 Reyes","2 Reyes","1 Cr\u00f3nicas","2 Cr\u00f3nicas","Esdras",
    "Nehem\u00edas","Ester","Job","Salmos","Proverbios",
    "Eclesiast\u00e9s","Cantares","Isa\u00edas","Jerem\u00edas","Lamentaciones",
    "Ezequiel","Daniel","Oseas","Joel","Am\u00f3s",
    "Abd\u00edas","Jon\u00e1s","Miqueas","Nah\u00fam","Habacuc",
    "Sofon\u00edas","Hageo","Zacar\u00edas","Malaqu\u00edas",
    "S. Mateo","S. Marcos","S. Lucas","S.Juan","Hechos",
    "Romanos","1 Corintios","2 Corintios","G\u00e1latas","Efesios",
    "Filipenses","Colosenses","1 Tesalonicenses","2 Tesalonicenses","1 Timoteo",
    "2 Timoteo","Tito","Filem\u00f3n","Hebreos","Santiago",
    "1 Pedro","2 Pedro","1 Juan","2 Juan","3 Juan",
    "Judas","Apocalipsis"
]

def parse_bcvvp(bcvvp_id):
    """Parse BCVWP ID -> (book, ch, vs, wd)
    Formats:
      'nBBCCCVVVWWW' (NT source, 11 chars after n)
      'oBBCCCVVVWWWx' (OT source, 12 chars after o, last char is sub-position)
      'BBCCCVVVWWW' (target, 11 chars)
    """
    s = bcvvp_id.lstrip('no')
    if len(s) == 11:
        return (int(s[0:2]), int(s[2:5]), int(s[5:8]), int(s[8:11]))
    if len(s) == 12:
        # OT source has extra sub-position digit; ignore last char
        return (int(s[0:2]), int(s[2:5]), int(s[5:8]), int(s[8:11]))
    return None

def normalize_strong_lemma(raw):
    """Extract Strong numbers from lemma attribute like 'b/7225' or '1254 a' or 'c/d/776'"""
    if not raw: return []
    parts = raw.replace('b/', 'H').replace('g/', 'G').split('/')
    result = []
    for p in parts:
        p = p.strip()
        m = re.match(r'[HG](\d+)', p)
        if m:
            result.append(p[0] + m.group(1))
            continue
        m = re.match(r'(\d+)$', p)
        if m:
            result.append('H' + m.group(1))
    return result

def normalize_strong(s):
    """Normalize: 'G0976' -> 'G976', '{H5315K}' -> 'H5315'"""
    s = s.strip().strip('{}')
    if s.startswith('G') or s.startswith('g'):
        return 'G' + re.sub(r'\D', '', s)
    if s.startswith('H') or s.startswith('h'):
        return 'H' + re.sub(r'\D', '', s)
    if re.match(r'^\d+$', s):
        return 'H' + s
    return s

# ---- FILE HELPERS ----

def ensure_dir(d):
    os.makedirs(d, exist_ok=True)

def download(url, path):
    if os.path.exists(path):
        print(f"  [OK] {os.path.basename(path)}")
        return
    print(f"  [DL] {url.split('/')[-1][:50]}...", end=' ', flush=True)
    try:
        data = urlopen(url, timeout=300).read()
        with open(path, 'wb') as f:
            f.write(data)
        print(f"{len(data)//1024} KB")
    except Exception as e:
        print(f"ERR: {e}")

def download_all():
    ensure_dir(SRC)
    oshb_base = 'https://raw.githubusercontent.com/openscriptures/morphhb/master/wlc'
    for bcvwp_abbr, oshb_name in OSHB_FILENAMES.items():
        download(f'{oshb_base}/{oshb_name}.xml', os.path.join(SRC, f'{oshb_name}.xml'))
    tagnt_base = 'https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master/Translators%20Amalgamated%20OT%2BNT'
    download(f'{tagnt_base}/TAGNT%20Mat-Jhn%20-%20Translators%20Amalgamated%20Greek%20NT%20-%20STEPBible.org%20CC-BY.txt',
             os.path.join(SRC, 'TAGNT-Mat-Jhn.txt'))
    download(f'{tagnt_base}/TAGNT%20Act-Rev%20-%20Translators%20Amalgamated%20Greek%20NT%20-%20STEPBible.org%20CC-BY.txt',
             os.path.join(SRC, 'TAGNT-Act-Rev.txt'))
    cb_base = 'https://raw.githubusercontent.com/Clear-Bible/Alignments/main/data/spa/alignments/RV09'
    download(f'{cb_base}/SBLGNT-RV09-manual.json', os.path.join(SRC, 'SBLGNT-RV09-manual.json'))
    download(f'{cb_base}/WLCM-RV09-manual.json', os.path.join(SRC, 'WLCM-RV09-manual.json'))
    # RV09 target text files (actual Spanish words with BCVWP positions)
    cb_target_base = 'https://raw.githubusercontent.com/Clear-Bible/Alignments/main/data/spa/targets/RV09'
    download(f'{cb_target_base}/nt_RV09.tsv', os.path.join(SRC, 'nt_RV09.tsv'))
    download(f'{cb_target_base}/ot_RV09.tsv', os.path.join(SRC, 'ot_RV09.tsv'))

# ---- PARSE OSHB XML ----

def parse_osbh(book_abbr):
    oshb_name = OSHB_FILENAMES.get(book_abbr)
    if not oshb_name: return {}
    path = os.path.join(SRC, f'{oshb_name}.xml')
    if not os.path.exists(path):
        print(f"  [--] {oshb_name}.xml no encontrado")
        return {}
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        print(f"  [!!] error parseando {path}: {e}")
        return {}
    root = tree.getroot()
    ns = {'osis': 'http://www.bibletechnologies.net/2003/OSIS/namespace'}
    result = {}
    for chapter in root.findall('.//osis:chapter', ns):
        ch_num = int(chapter.get('osisID').split('.')[1])
        for verse in chapter.findall('.//osis:verse', ns):
            vs_num = int(verse.get('osisID').rsplit('.', 1)[-1])
            word_pos = 0
            for child in verse:
                local = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if local == 'w':
                    word_pos += 1
                    lemma_attr = child.get('lemma', '')
                    morph_attr = child.get('morph', '')
                    strongs = normalize_strong_lemma(lemma_attr)
                    text = ''.join(child.itertext()).strip()
                    result[(ch_num, vs_num, word_pos)] = {
                        'strong': strongs,
                        'morph': morph_attr or '',
                        'lemma': lemma_attr,
                        'surface': text,
                    }
    return result

# ---- PARSE TAGNT ----

TAGNT_BOOK_MAP = {
    'Mat':40,'Mrk':41,'Luk':42,'Jhn':43,'Act':44,'Rom':45,
    '1Co':46,'2Co':47,'Gal':48,'Eph':49,'Phi':50,'Col':51,
    '1Th':52,'2Th':53,'1Ti':54,'2Ti':55,'Tit':56,'Phm':57,
    'Heb':58,'Jas':59,'1Pe':60,'2Pe':61,'1Jn':62,'2Jn':63,
    '3Jn':64,'Jud':65,'Rev':66,
}

def parse_tagnt_file(path):
    result = {}
    if not os.path.exists(path):
        print(f"  [--] {os.path.basename(path)} no encontrado")
        return result
    ref_pat = re.compile(r'^(\w+)\.(\d+)\.(\d+)#(\d+)')
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            m = ref_pat.match(line)
            if not m: continue
            book_abbr = m.group(1)
            ch = int(m.group(2))
            vs = int(m.group(3))
            wpos = int(m.group(4))
            cols = line.split('\t')
            if len(cols) < 5: continue
            strong_morph = cols[3].strip() if len(cols) > 3 else ''
            lemma_raw = cols[4].strip() if len(cols) > 4 else ''
            greek_raw = cols[1].strip() if len(cols) > 1 else ''
            greek_word = greek_raw.split('(')[0].strip()
            strongs = []
            morph = ''
            if strong_morph:
                parts = strong_morph.split('=')
                if len(parts) >= 1:
                    s = parts[0].strip()
                    strongs = [normalize_strong(s)]
                if len(parts) >= 2:
                    morph = parts[1].strip()
            bn = TAGNT_BOOK_MAP.get(book_abbr)
            if bn:
                result[(bn, ch, vs, wpos)] = {
                    'strong': strongs,
                    'morph': morph,
                    'lemma': lemma_raw,
                    'surface': greek_word,
                }
    return result

def parse_tagnt():
    result = {}
    for fname in ['TAGNT-Mat-Jhn.txt', 'TAGNT-Act-Rev.txt']:
        result.update(parse_tagnt_file(os.path.join(SRC, fname)))
    return result

# ---- PARSE ALIGNMENTS ----

def parse_alignment(path):
    if not os.path.exists(path):
        print(f"  [--] {os.path.basename(path)} no encontrado")
        return []
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    records = data.get('records', [])
    result = []
    for rec in records:
        src = rec.get('source', [])
        tgt = rec.get('target', [])
        if src and tgt:
            result.append((src, tgt))
    return result

# ---- TOKENIZE SPANISH ----

def tokenize_spanish(text):
    tokens = []
    pattern = re.compile(r'([a-zA-Z\u00E1\u00E9\u00ED\u00F3\u00FA\u00FC\u00F1\u00C1\u00C9\u00CD\u00D3\u00DA\u00DC\u00D1]+|[^a-zA-Z\u00E1\u00E9\u00ED\u00F3\u00FA\u00FC\u00F1\u00C1\u00C9\u00CD\u00D3\u00DA\u00DC\u00D1]+)')
    for m in pattern.finditer(text):
        token = m.group(1)
        if re.match(r'^[a-zA-Z\u00E1\u00E9\u00ED\u00F3\u00FA\u00FC\u00F1\u00C1\u00C9\u00CD\u00D3\u00DA\u00DC\u00D1]+$', token):
            tokens.append({'type': 'word', 'text': token})
        else:
            tokens.append({'type': 'sep', 'text': token})
    return tokens

# ---- PARSE RV09 TARGET TSV ----

WORD_RE = re.compile(r'^[a-zA-Z\u00E1\u00E9\u00ED\u00F3\u00FA\u00FC\u00F1\u00C1\u00C9\u00CD\u00D3\u00DA\u00DC\u00D1]+$')

def parse_rv09_targets(path):
    """
    Parse RV09 TSV -> dict of (book, ch, vs): [(bcvwp_pos, text), ...]
    Only non-excluded word-type tokens are included.
    """
    import csv
    result = {}
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            bid = row['id'].strip()
            if len(bid) < 11:
                continue
            exclude = row.get('exclude', '').strip()
            if exclude == 'y':
                continue
            text = row['text'].strip()
            if not WORD_RE.match(text):
                continue
            bn = int(bid[0:2])
            ch = int(bid[2:5])
            vs = int(bid[5:8])
            pos = int(bid[8:11])
            key = (bn, ch, vs)
            if key not in result:
                result[key] = []
            result[key].append((pos, text))
    return result

# ---- BUILD RV1960 <-> RV09 POSITION MAP ----

ACCENT_MAP = str.maketrans({
    '\u00e1': 'a', '\u00e9': 'e', '\u00ed': 'i', '\u00f3': 'o', '\u00fa': 'u',
    '\u00c1': 'A', '\u00c9': 'E', '\u00cd': 'I', '\u00d3': 'O', '\u00da': 'U',
    '\u00fc': 'u', '\u00dc': 'U',
})

def normalize_spanish(s):
    """Remove diacritics for comparison."""
    return s.lower().translate(ACCENT_MAP)

def lcs_align_indices(seq_a, seq_b):
    """
    Map indices of seq_a to indices of seq_b using longest common subsequence.
    Returns list where result[i] = j if seq_a[i] matches seq_b[j], else None.
    Preserves order; maximizes total matches.
    """
    n, m = len(seq_a), len(seq_b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n):
        for j in range(m):
            if normalize_spanish(seq_a[i]) == normalize_spanish(seq_b[j]):
                dp[i + 1][j + 1] = dp[i][j] + 1
            else:
                dp[i + 1][j + 1] = max(dp[i][j + 1], dp[i + 1][j])
    mapping = [None] * n
    i, j = n - 1, m - 1
    while i >= 0 and j >= 0:
        if normalize_spanish(seq_a[i]) == normalize_spanish(seq_b[j]):
            mapping[i] = j
            i -= 1
            j -= 1
        elif dp[i][j + 1] >= dp[i + 1][j]:
            i -= 1
        else:
            j -= 1
    return mapping

def spanish_stem(word):
    """Reduce Spanish verb forms to stem for fuzzy matching.
    Only strips suffixes that are uniquely verb endings (not ambiguous
    noun/adjective endings like 'o', 'a', 'e')."""
    w = word.lower()
    # Uniquely verb endings (infinitive, participle, gerund, past tense)
    for suffix in ['aron', 'ieron', 'ando', 'iendo', 'ado', 'ido',
                   'aba', 'ian', 'ia', 'ara', 'iera', 'ase', 'iese',
                   'ad', 'ed', 'id', 'ar', 'er', 'ir',
                   'to', 'cho', 'so']:
        if len(w) > len(suffix) + 2 and w.endswith(suffix):
            return w[:-len(suffix)]
    # Single-character verb endings (after accent normalization these are 'o', 'a')
    # Only for words where root is 3+ chars
    for suffix in ['o', 'a']:
        if len(w) > len(suffix) + 2 and w.endswith(suffix):
            # Check that the stem is a plausible verb root (ends in consonant)
            root = w[:-len(suffix)]
            if root and root[-1] not in 'aeiou':
                return root
    return w

def verb_stem_match(a, b):
    """Check if two Spanish words likely share the same verb root.
    Only matches when at least one word was actually reduced (had a verb suffix)."""
    a_stem = spanish_stem(a)
    b_stem = spanish_stem(b)
    if len(a_stem) < 3 or len(b_stem) < 3:
        return False
    if a_stem != b_stem:
        return False
    a_was_reduced = (a_stem != a.lower())
    b_was_reduced = (b_stem != b.lower())
    return a_was_reduced or b_was_reduced

def build_pos_map_1960_to_rv09(rv1960_words, rv09_words_with_pos):
    rv09_texts = [t for _, t in rv09_words_with_pos]
    # Primary: exact LCS with accent normalization
    idx_map = lcs_align_indices(rv1960_words, rv09_texts)
    # Secondary: verb-stem matching for unmatched words
    used = set(j for j in idx_map if j is not None)
    for i in range(len(rv1960_words)):
        if idx_map[i] is not None:
            continue
        a_norm = normalize_spanish(rv1960_words[i])
        best_j = None
        for j in range(len(rv09_texts)):
            if j in used:
                continue
            b_norm = normalize_spanish(rv09_texts[j])
            if verb_stem_match(a_norm, b_norm):
                best_j = j
                break
        if best_j is not None:
            idx_map[i] = best_j
            used.add(best_j)
    # Tertiary: exact text match for remaining unmatched words (handles nouns,
    # adjectives, and other non-verb words that are identical in both versions)
    used = set(j for j in idx_map if j is not None)
    for i in range(len(rv1960_words)):
        if idx_map[i] is not None:
            continue
        a_norm = normalize_spanish(rv1960_words[i])
        for j in range(len(rv09_texts)):
            if j in used:
                continue
            b_norm = normalize_spanish(rv09_texts[j])
            if a_norm == b_norm:
                idx_map[i] = j
                used.add(j)
                break
    # Build result
    result = []
    for i, rv09_idx in enumerate(idx_map):
        if rv09_idx is not None:
            result.append(rv09_words_with_pos[rv09_idx][0])
        else:
            result.append(None)
    return result

# ---- MAIN ----

def build_interlinear():
    print("="*60)
    print("EXTRAYENDO FUENTES DE DATOS")
    print("="*60)
    download_all()

    print("\n[AT] PARSING OSHB HEBREW...")
    ot_words = {}
    for i, book_abbr in enumerate(BCVWP_OT):
        book_num = i + 1
        data = parse_osbh(book_abbr)
        for (ch, vs, wpos), wdata in data.items():
            ot_words[(book_num, ch, vs, wpos)] = wdata
        print(f"  {book_abbr}: {len(data)} palabras")
    print(f"  Total AT: {len(ot_words)} palabras")

    print("\n[NT] PARSING TAGNT GRIEGO...")
    nt_words = parse_tagnt()
    print(f"  Total NT: {len(nt_words)} palabras")

    print("\n[ALIGN] PARSING CLEAR-BIBLE...")
    align_nt = parse_alignment(os.path.join(SRC, 'SBLGNT-RV09-manual.json'))
    align_ot = parse_alignment(os.path.join(SRC, 'WLCM-RV09-manual.json'))
    print(f"  NT alineaciones: {len(align_nt)}, OT alineaciones: {len(align_ot)}")

    # Build reverse alignment: (t_book, t_ch, t_vs, t_pos) -> [(s_book, s_ch, s_vs, s_pos), ...]
    # t_pos comes from the RV09 BCVWP target IDs (includes punctuation positions)
    reverse_align = {}
    def add_alignment(src_ids, tgt_ids):
        s = parse_bcvvp(src_ids[0])
        if not s: return
        s_book, s_ch, s_vs, s_pos = s
        for tid in tgt_ids:
            t = parse_bcvvp(tid)
            if not t: continue
            t_book, t_ch, t_vs, t_pos = t
            key = (t_book, t_ch, t_vs, t_pos)
            if key not in reverse_align:
                reverse_align[key] = []
            reverse_align[key].append((s_book, s_ch, s_vs, s_pos))
    for src_ids, tgt_ids in align_nt:
        add_alignment(src_ids, tgt_ids)
    for src_ids, tgt_ids in align_ot:
        add_alignment(src_ids, tgt_ids)
    print(f"  Mapeos reversos: {len(reverse_align)}")

    print("\n[RV09] PARSING RV09 TARGET TEXT...")
    rv09_nt = parse_rv09_targets(os.path.join(SRC, 'nt_RV09.tsv'))
    rv09_ot = parse_rv09_targets(os.path.join(SRC, 'ot_RV09.tsv'))
    rv09_all = {}
    rv09_all.update(rv09_ot)
    rv09_all.update(rv09_nt)
    total_verses_rv09 = sum(1 for k, v in rv09_all.items() if v)
    print(f"  {total_verses_rv09} versiculos con datos RV09")

    print("\n[BIBLE] LOADING BIBLE_DATA...")
    rv1960_path = os.path.join(os.path.dirname(__file__), 'rv1960.js')
    rv1960_data = {}
    if os.path.exists(rv1960_path):
        with open(rv1960_path, 'r', encoding='utf-8') as f:
            content = f.read()
        m = re.search(r'var\s+BIBLE_DATA\s*=\s*(\{.+?\});', content, re.DOTALL)
        if m:
            rv1960_data = json.loads(m.group(1))
            print(f"  {sum(len(c) for c in rv1960_data.values())} versiculos cargados")
        else:
            print("  ERROR: No se pudo parsear BIBLE_DATA")
            return None
    else:
        print("  ERROR: rv1960.js no encontrado")
        return None

    # Verify book name mapping
    sp_to_bcvwp = {}
    for i, sp_name in enumerate(SPANISH_BOOKS):
        sp_to_bcvwp[sp_name] = i + 1
    unknown_books = [b for b in rv1960_data if b not in sp_to_bcvwp]
    if unknown_books:
        print(f"  Libros desconocidos: {unknown_books}")
        # Try approximate matching
        for sp_b in unknown_books:
            # Find closest match
            for k in sp_to_bcvwp:
                if k.lower() == sp_b.lower() or k.lower().replace('.','') == sp_b.lower().replace('.',''):
                    sp_to_bcvwp[sp_b] = sp_to_bcvwp[k]
                    print(f"    Mapeado: '{sp_b}' -> '{k}' (book {sp_to_bcvwp[k]})")
                    break

    print("\n[BUILD] CONSTRUYENDO INTERLINEAL...")
    interlinear = {}
    stats = {'versiculos': 0, 'palabras': 0, 'palabras_con_strong': 0}

    for sp_book, chapters in rv1960_data.items():
        bn = sp_to_bcvwp.get(sp_book)
        if not bn:
            print(f"  [!!] libro desconocido: '{sp_book}'")
            continue
        for ch_str, verses in chapters.items():
            ch = int(ch_str)
            for vs_str, vtext in verses.items():
                vs = int(vs_str)
                ref = f"{sp_book} {ch}:{vs}"
                tokens = tokenize_spanish(vtext)

                # Get RV1960 word texts
                rv1960_words = [tok['text'] for tok in tokens if tok['type'] == 'word']

                # Get RV09 words for this verse (empty list if unavailable)
                rv09_entry = rv09_all.get((bn, ch, vs), [])
                if rv09_entry and len(rv09_entry) > 0:
                    # Build position map: RV1960 word index -> RV09 BCVWP position
                    pos_map = build_pos_map_1960_to_rv09(rv1960_words, rv09_entry)
                else:
                    pos_map = [None] * len(rv1960_words)

                words_out = []
                rv1960_word_idx = 0
                for tok in tokens:
                    if tok['type'] == 'word':
                        rv09_bcvwp_pos = pos_map[rv1960_word_idx] if rv1960_word_idx < len(pos_map) else None
                        strongs = []
                        morph = ''
                        lemma = ''
                        original = ''
                        if rv09_bcvwp_pos is not None:
                            tgt_key = (bn, ch, vs, rv09_bcvwp_pos)
                            if tgt_key in reverse_align:
                                for s_book, s_ch, s_vs, s_pos in reverse_align[tgt_key]:
                                    src_key = (s_book, s_ch, s_vs, s_pos)
                                    src_data = None
                                    if 1 <= s_book <= 39:
                                        src_data = ot_words.get(src_key)
                                    elif 40 <= s_book <= 66:
                                        src_data = nt_words.get(src_key)
                                    if src_data:
                                        for s in src_data.get('strong', []):
                                            if s and s not in strongs:
                                                strongs.append(s)
                                        if not morph and src_data.get('morph'):
                                            morph = src_data['morph']
                                        if not lemma and src_data.get('lemma'):
                                            lemma = src_data['lemma']
                                        if not original and src_data.get('surface'):
                                            original = src_data['surface']
                        words_out.append({
                            'surface': tok['text'],
                            'strong': strongs,
                            'morph': morph,
                            'lemma': lemma,
                            'original': original,
                            'rv09_pos': rv09_bcvwp_pos,
                        })
                        rv1960_word_idx += 1
                        stats['palabras'] += 1
                        if strongs:
                            stats['palabras_con_strong'] += 1
                    else:
                        words_out.append({
                            'surface': tok['text'],
                            'strong': [],
                            'morph': '',
                            'lemma': '',
                            'original': '',
                            'rv09_pos': None,
                        })
                interlinear[ref] = {
                    'book': sp_book,
                    'chapter': ch,
                    'verse': vs,
                    'words': words_out,
                }
                stats['versiculos'] += 1

    print(f"\n[STATS]")
    print(f"  Versiculos: {stats['versiculos']}")
    print(f"  Palabras totales: {stats['palabras']}")
    print(f"  Palabras con Strong: {stats['palabras_con_strong']} ({stats['palabras_con_strong']/max(1,stats['palabras'])*100:.1f}%)")

    print(f"\n[OUT] ESCRIBIENDO {OUT_JSON} (full)...")
    with gzip.open(OUT_JSON, 'wt', encoding='utf-8') as f:
        json.dump(interlinear, f, ensure_ascii=False)
    size_kb = os.path.getsize(OUT_JSON) / 1024
    print(f"  {size_kb:.0f} KB comprimido")

    # Also write compact positional lookup for fast JS loading
    # Format: INTERLINEAR_LOOKUP[verseRef] = [ [strongs at word pos 0], [strongs at word pos 1], ... ]
    # Separators are skipped (only word positions are indexed)
    lookup = {}
    for ref, vdata in interlinear.items():
        word_strongs = [w['strong'] for w in vdata['words'] if re.match(r'^[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+$', w['surface'])]
        lookup[ref] = word_strongs
    print(f"\n[OUT] ESCRIBIENDO {OUT_JS} (lookup)...")
    with open(OUT_JS, 'w', encoding='utf-8') as f:
        f.write('var INTERLINEAR_LOOKUP=')
        json.dump(lookup, f, ensure_ascii=False)
        f.write(';\n')
    js_size = os.path.getsize(OUT_JS) / 1024
    print(f"  {js_size:.0f} KB")

    return interlinear

if __name__ == '__main__':
    result = build_interlinear()
    if result:
        print("\n[DONE] Interlineal generado!")
        sample = list(result.keys())[:5]
        for ref in sample:
            w = result[ref]['words']
            w_strong = [x for x in w if x.get('strong')]
            print(f"  {ref}: {sum(1 for x in w if bool(x['strong']))}/{len(w)} con Strong")
            for ws in w_strong[:2]:
                print(f"    '{ws['surface']}' -> {ws['strong']}  orig={ws['original'][:30]}")
    else:
        print("\n[FAIL] No se pudo generar el interlineal")
