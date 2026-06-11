"""
Generate aliases.js additions from:
1. TAGNT Spanish column (reliable, >=2 occurrences)
2. TIPNR names (cross-referenced with actual Spanish text)
"""
import json, os, re, unicodedata, sys

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

PROJ_DIR = "C:\\Users\\LAPTOP\\OneDrive - dts.edu\\proyectos_programacion\\ebp\\kittelProject"
STEP_DIR = os.path.join(PROJ_DIR, "source_data", "step")

def normalize(text):
    nfkd = unicodedata.normalize('NFKD', text.lower())
    return ''.join(c for c in nfkd if not unicodedata.combining(c) and c.isalnum())

def load_existing_aliases():
    path = os.path.join(PROJ_DIR, "aliases.js")
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    existing = {}
    for m in re.finditer(r'"([^"]+)"\s*:\s*"([^"]+)"', content):
        existing[m.group(1).lower()] = m.group(2)
    return existing

def load_strong_index():
    path = os.path.join(PROJ_DIR, "strong_index.js")
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    existing = {}
    for m in re.finditer(r'"([^"]+)"\s*:\s*"([^"]+)"', content):
        existing[m.group(1).lower()] = m.group(2)
    return existing

def get_spanish_words_from_bible():
    """Extract all unique words from the Spanish Bible text (rv1960.js)"""
    path = os.path.join(PROJ_DIR, "rv1960.js")
    words = set()
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Extract words from verse arrays
    for m in re.finditer(r'"([^"]+)"', content):
        text = m.group(1)
        # Split by space and take each word
        for w in re.findall(r'[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+', text):
            words.add(w)
    print(f"  Total palabras en RV1960: {len(words)}")
    return words

def load_tagnt_extraction():
    path = os.path.join(STEP_DIR, "spanish_strong_extraction.json")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    print("GENERANDO ADICIONES A aliases.js")
    print("=" * 60)
    
    existing_aliases = load_existing_aliases()
    strong_index = load_strong_index()
    extraction = load_tagnt_extraction()
    
    print(f"\n  aliases.js existentes: {len(existing_aliases)}")
    print(f"  strong_index.js existentes: {len(strong_index)}")
    
    # 1. TAGNT aliases (single candidate, >=2 occurrences)
    tagnt_single = extraction["tagnt_single_candidates"]
    tagnt_entries = []
    tagnt_skipped = 0
    for word, strong in sorted(tagnt_single.items()):
        if word not in existing_aliases and word not in strong_index:
            tagnt_entries.append(f'    "{word}":"{strong}"')
        else:
            tagnt_skipped += 1
    
    print(f"\n  TAGNT: {len(tagnt_entries)} nuevos, {tagnt_skipped} ya existentes")
    
    # 2. TIPNR names - cross-reference with Spanish text
    tipnr_single = extraction["tipnr_single_candidates"]
    
    # Get Spanish words, normalize them
    spanish_words = get_spanish_words_from_bible()
    spanish_normalized = {normalize(w): w for w in spanish_words}
    
    tipnr_entries = []
    tipnr_skipped = 0
    tipnr_no_match = 0
    for name, strong in sorted(tipnr_single.items()):
        name_norm = normalize(name)
        if name_norm in existing_aliases or name_norm in strong_index:
            tipnr_skipped += 1
            continue
        if name_norm in spanish_normalized:
            # The normalized name matches a Spanish word in our text
            orig_spanish = spanish_normalized[name_norm]
            tipnr_entries.append(f'    "{name_norm}":"{strong}"')
        else:
            tipnr_no_match += 1
    
    print(f"  TIPNR: {len(tipnr_entries)} coinciden con RV1960, {tipnr_skipped} ya existentes, {tipnr_no_match} sin coincidencia")
    
    # 3. Generate actual alias lines with section headers
    lines = []
    lines.append("")
    lines.append("    // ========== GENERATED: TAGNT Spanish->Greek (NT) ==========")
    for entry in tagnt_entries:
        lines.append(entry + ",")
    
    lines.append("")
    lines.append("    // ========== GENERATED: TIPNR Proper Names ==========")
    for entry in tipnr_entries:
        lines.append(entry + ",")
    
    output_path = os.path.join(STEP_DIR, "aliases_addition_snippet.txt")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"\n  Snippet guardado en {output_path}")
    print(f"  Lineas: {len(lines)}")
    print(f"  Total nuevas entradas: {len(tagnt_entries) + len(tipnr_entries)}")

if __name__ == "__main__":
    main()
