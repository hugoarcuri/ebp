import re, json, os, urllib.request, csv, io, sys

OUT_DIR = "C:\\Users\\LAPTOP\\OneDrive - dts.edu\\proyectos_programacion\\ebp\\kittelProject\\source_data\\step"
DATA_DIR = OUT_DIR
os.makedirs(DATA_DIR, exist_ok=True)

BASE = "https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master"

TAHOT_FILES = [
    "Translators%20Amalgamated%20OT%2BNT/TAHOT%20Gen-Deu%20-%20Translators%20Amalgamated%20Hebrew%20OT%20-%20STEPBible.org%20CC%20BY.txt",
    "Translators%20Amalgamated%20OT%2BNT/TAHOT%20Jos-Est%20-%20Translators%20Amalgamated%20Hebrew%20OT%20-%20STEPBible.org%20CC%20BY.txt",
    "Translators%20Amalgamated%20OT%2BNT/TAHOT%20Job-Sng%20-%20Translators%20Amalgamated%20Hebrew%20OT%20-%20STEPBible.org%20CC%20BY.txt",
    "Translators%20Amalgamated%20OT%2BNT/TAHOT%20Isa-Mal%20-%20Translators%20Amalgamated%20Hebrew%20OT%20-%20STEPBible.org%20CC%20BY.txt",
]
TAGNT_FILES = [
    "Translators%20Amalgamated%20OT%2BNT/TAGNT%20Mat-Jhn%20-%20Translators%20Amalgamated%20Greek%20NT%20-%20STEPBible.org%20CC-BY.txt",
    "Translators%20Amalgamated%20OT%2BNT/TAGNT%20Act-Rev%20-%20Translators%20Amalgamated%20Greek%20NT%20-%20STEPBible.org%20CC-BY.txt",
]

def download_file(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        print(f"  Ya existe: {path}")
        return
    print(f"  Descargando {url[:80]}...")
    try:
        urllib.request.urlretrieve(url, path)
        print(f"  OK ({os.path.getsize(path)} bytes)")
    except Exception as e:
        print(f"  Error: {e}")

def download_all():
    for f in TAHOT_FILES:
        url = BASE + "/" + f
        name = os.path.basename(f.replace("%20", " "))
        download_file(url, os.path.join(DATA_DIR, name))
    for f in TAGNT_FILES:
        url = BASE + "/" + f
        name = os.path.basename(f.replace("%20", " "))
        download_file(url, os.path.join(DATA_DIR, name))

def extract_dstrongs(dstrong_field):
    """Extract base Strong number from dStrongs field like H1254A, {H0430G}, H9002/H9009/{H0776G}"""
    if not dstrong_field:
        return None
    # Remove braces
    text = dstrong_field.strip().strip('{}')
    # Split on / and take last part
    parts = text.split('/')
    last = parts[-1].strip()
    # Remove suffix letters (A, B, G, etc.) - keep alphanumeric + H/G prefix
    m = re.match(r'^[HG](\d+)[A-Za-z]?$', last)
    if m:
        return last  # Return full code with suffix letter
    m = re.match(r'^[HG]\d+$', last)
    if m:
        return last
    return None

def extract_hebrew_lemma(expanded_tags):
    """Extract Hebrew lemma from Expanded Strong tags like {H1254A=בָּרָא=to create}"""
    if not expanded_tags:
        return None
    # Pattern: {H####=HEBREW=gloss}
    m = re.search(r'\{[^}]+\}', expanded_tags)
    if not m:
        return None
    inner = m.group(0).strip('{}')
    parts = inner.split('=')
    if len(parts) >= 2:
        # parts[0] = H1254A, parts[1] = בָּרָא
        return parts[1]
    return None

def parse_tahot(path):
    """Parse TAHOT file, extract Hebrew lemma -> dStrong pairs"""
    lemmas = {}
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        in_data = False
        for row in reader:
            if not row or len(row) < 4:
                continue
            # Detect data rows: start with book abbreviation like Gen.1.1#01=L
            if row[0].startswith('Gen.') or row[0].startswith('Exo.') or row[0].startswith('Lev.') or \
               row[0].startswith('Num.') or row[0].startswith('Deu.') or row[0].startswith('Jos.') or \
               row[0].startswith('Jdg.') or row[0].startswith('Rut.') or row[0].startswith('1Sa.') or \
               row[0].startswith('2Sa.') or row[0].startswith('1Ki.') or row[0].startswith('2Ki.') or \
               row[0].startswith('1Ch.') or row[0].startswith('2Ch.') or row[0].startswith('Ezr.') or \
               row[0].startswith('Neh.') or row[0].startswith('Est.') or row[0].startswith('Job.') or \
               row[0].startswith('Psa.') or row[0].startswith('Pro.') or row[0].startswith('Ecc.') or \
               row[0].startswith('Sng.') or row[0].startswith('Isa.') or row[0].startswith('Jer.') or \
               row[0].startswith('Lam.') or row[0].startswith('Ezk.') or row[0].startswith('Dan.') or \
               row[0].startswith('Hos.') or row[0].startswith('Jol.') or row[0].startswith('Amo.') or \
               row[0].startswith('Oba.') or row[0].startswith('Jon.') or row[0].startswith('Mic.') or \
               row[0].startswith('Nam.') or row[0].startswith('Hab.') or row[0].startswith('Zep.') or \
               row[0].startswith('Hag.') or row[0].startswith('Zec.') or row[0].startswith('Mal.'):
                in_data = True
            if not in_data:
                continue
            # Expected columns for detailed data:
            # 0: Ref, 1: Hebrew, 2: Transliteration, 3: Translation, 4: dStrongs, 5: Grammar, ...
            # Alternatively compact format with 4 columns
            if len(row) < 5:
                continue
            dstrong_raw = row[4].strip()
            hebrew = row[1].strip() if len(row) > 1 else ""
            transliteration = row[2].strip() if len(row) > 2 else ""
            translation = row[3].strip() if len(row) > 3 else ""
            expanded = row[11].strip() if len(row) > 11 else ""
            # Extract base Strong number
            strong = extract_dstrongs(dstrong_raw)
            if not strong:
                continue
            # Extract Hebrew lemma from expanded tags if available
            hebrew_lemma = extract_hebrew_lemma(expanded) if expanded else None
            if not hebrew_lemma:
                hebrew_lemma = hebrew  # fallback: use the inflected form
            if hebrew_lemma:
                # Store: normalize Strong number (strip suffix letter for base comparison)
                base_strong = re.sub(r'[A-Za-z]$', '', strong)
                if hebrew_lemma not in lemmas:
                    lemmas[hebrew_lemma] = set()
                lemmas[hebrew_lemma].add(base_strong)
    return lemmas

def parse_tagnt(path):
    """Parse TAGNT file, extract Greek lemma -> dStrong pairs"""
    lemmas = {}
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        in_data = False
        for row in reader:
            if not row or len(row) < 4:
                continue
            # Detect data rows: start with Mat. or Mrk. or Luk. or Jhn. or Act. or Rom. etc.
            book_abbrevs = ['Mat.', 'Mrk.', 'Luk.', 'Jhn.', 'Act.', 'Rom.', '1Co.', '2Co.', 'Gal.', 'Eph.',
                            'Php.', 'Col.', '1Th.', '2Th.', '1Ti.', '2Ti.', 'Tit.', 'Phm.', 'Heb.', 'Jas.',
                            '1Pe.', '2Pe.', '1Jn.', '2Jn.', '3Jn.', 'Jud.', 'Rev.']
            is_data = any(row[0].startswith(b) for b in book_abbrevs)
            if not is_data:
                # Check if row starts with # which marks summary lines in TAGNT
                if row[0].startswith('#'):
                    continue
                # Some data rows start with the Greek word directly
                continue
            in_data = True
            # Columns: 0: Word&Type, 1: Greek, 2: English, 3: dStrongs=Grammar, 4: DictForm=Gloss, ...
            if len(row) < 8:
                continue
            dstrong_grammar = row[3].strip() if len(row) > 3 else ""
            dict_form = row[4].strip() if len(row) > 4 else ""
            greek = row[1].strip() if len(row) > 1 else ""
            # Extract dStrong from "G0976=N-NSF" format
            strong = None
            if '=' in dstrong_grammar:
                strong = dstrong_grammar.split('=')[0].strip()
            else:
                strong = dstrong_grammar.strip()
            if not strong or not strong.startswith('G'):
                continue
            # Extract Greek lemma from "βίβλος=book" format
            greek_lemma = None
            if '=' in dict_form:
                greek_lemma = dict_form.split('=')[0].strip()
            else:
                greek_lemma = greek  # fallback
            if greek_lemma:
                base_strong = re.sub(r'[A-Za-z]$', '', strong)
                if greek_lemma not in lemmas:
                    lemmas[greek_lemma] = set()
                lemmas[greek_lemma].add(base_strong)
    return lemmas

def load_current_strong_index():
    """Load current strong_index.js and extract all Strong numbers"""
    path = "C:\\Users\\LAPTOP\\OneDrive - dts.edu\\proyectos_programacion\\ebp\\kittelProject\\strong_index.js"
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Extract all Strong numbers referenced
    strongs = set()
    for m in re.finditer(r'[HG]\d+', content):
        strongs.add(m.group(0))
    # Count entries
    entry_count = len(re.findall(r'"([^"]+)":"', content))
    return strongs, entry_count

def load_current_aliases():
    """Load current aliases.js and extract all alias word forms"""
    path = "C:\\Users\\LAPTOP\\OneDrive - dts.edu\\proyectos_programacion\\ebp\\kittelProject\\aliases.js"
    if not os.path.exists(path):
        return set()
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    aliases = set()
    for m in re.finditer(r'"([^"]+)"\s*:\s*"([^"]+)"', content):
        aliases.add(m.group(1).lower())
    return aliases

def main():
    print("=" * 60)
    print("ANALISIS DE STEPBible TAHOT + TAGNT")
    print("=" * 60)
    
    # Step 1: Download files
    print("\n[1] Descargando archivos...")
    download_all()
    
    # Step 2: Parse TAHOT
    print("\n[2] Parseando TAHOT (hebreo AT)...")
    all_hebrew_lemmas = {}
    tahot_files = [f for f in os.listdir(DATA_DIR) if f.startswith('TAHOT')]
    for fname in tahot_files:
        path = os.path.join(DATA_DIR, fname)
        print(f"  Procesando {fname}...")
        try:
            lemmas = parse_tahot(path)
            print(f"    {len(lemmas)} lemmas hebreos extraidos")
            for k, v in lemmas.items():
                if k not in all_hebrew_lemmas:
                    all_hebrew_lemmas[k] = set()
                all_hebrew_lemmas[k] |= v
        except Exception as e:
            print(f"    Error: {e}")
    
    print(f"\n  Total lemmas hebreos unicos: {len(all_hebrew_lemmas)}")
    
    # Step 3: Parse TAGNT
    print("\n[3] Parseando TAGNT (griego NT)...")
    all_greek_lemmas = {}
    tagnt_files = [f for f in os.listdir(DATA_DIR) if f.startswith('TAGNT')]
    for fname in tagnt_files:
        path = os.path.join(DATA_DIR, fname)
        print(f"  Procesando {fname}...")
        try:
            lemmas = parse_tagnt(path)
            print(f"    {len(lemmas)} lemmas griegos extraidos")
            for k, v in lemmas.items():
                if k not in all_greek_lemmas:
                    all_greek_lemmas[k] = set()
                all_greek_lemmas[k] |= v
        except Exception as e:
            print(f"    Error: {e}")
    
    print(f"\n  Total lemmas griegos unicos: {len(all_greek_lemmas)}")
    
    # Step 4: Compare with current strong_index.js
    print("\n[4] Comparando con strong_index.js actual...")
    current_strongs, entry_count = load_current_strong_index()
    print(f"  strong_index.js: {entry_count} entradas, {len(current_strongs)} Strong numbers unicos")
    
    # Collect all Strong numbers from TAHOT+TAGNT
    all_step_strongs = set()
    for v in all_hebrew_lemmas.values():
        all_step_strongs |= v
    for v in all_greek_lemmas.values():
        all_step_strongs |= v
    print(f"  STEPBible data: {len(all_step_strongs)} Strong numbers unicos en TAHOT+TAGNT")
    
    new_strongs = all_step_strongs - current_strongs
    print(f"  Strong numbers en STEPBible pero NO en strong_index.js: {len(new_strongs)}")
    if new_strongs:
        print(f"  Ejemplos: {sorted(list(new_strongs))[:20]}")
    
    # Step 5: Compare lemma counts
    print("\n[5] Resumen de lemas por Testament:")
    print(f"  AT (hebreo): {len(all_hebrew_lemmas)} lemmas unicos")
    print(f"  NT (griego): {len(all_greek_lemmas)} lemmas unicos")
    
    # Step 6: Save comprehensive index
    print("\n[6] Guardando indice completo...")
    output = {
        "hebrew": {k: sorted(list(v)) for k, v in sorted(all_hebrew_lemmas.items())},
        "greek": {k: sorted(list(v)) for k, v in sorted(all_greek_lemmas.items())},
        "stats": {
            "hebrew_lemmas": len(all_hebrew_lemmas),
            "greek_lemmas": len(all_greek_lemmas),
            "total_lemmas": len(all_hebrew_lemmas) + len(all_greek_lemmas),
            "hebrew_strongs_unique": len(set.union(*all_hebrew_lemmas.values())) if all_hebrew_lemmas else 0,
            "greek_strongs_unique": len(set.union(*all_greek_lemmas.values())) if all_greek_lemmas else 0,
            "step_unique_strongs": len(all_step_strongs),
            "current_index_strongs": len(current_strongs),
            "new_strongs_available": len(new_strongs),
        }
    }
    out_path = os.path.join(DATA_DIR, "lema_index_step.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  Guardado en {out_path}")
    print(f"  Tamaño: {os.path.getsize(out_path)} bytes")

if __name__ == "__main__":
    main()
