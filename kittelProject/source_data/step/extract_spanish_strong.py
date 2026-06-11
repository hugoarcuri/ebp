"""
Extract Spanish word -> Strong number mappings from:
1. TAGNT (Spanish translation column) - direct Spanish to Greek mapping
2. TIPNR (proper names) - name to Strong mapping
Produces a file of suggested additions for aliases.js
"""
import re, json, csv, os, unicodedata, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

STEP_DIR = "C:\\Users\\LAPTOP\\OneDrive - dts.edu\\proyectos_programacion\\ebp\\kittelProject\\source_data\\step"
PROJ_DIR = "C:\\Users\\LAPTOP\\OneDrive - dts.edu\\proyectos_programacion\\ebp\\kittelProject"

def normalize(text):
    """Remove accents, lowercase, strip punctuation"""
    text = text.strip().lower()
    # Remove diacritics
    nfkd = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in nfkd if not unicodedata.combining(c))
    # Remove punctuation except guion
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()

def strip_accents(text):
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))

def load_strong_index():
    """Load strong_index.js as dict"""
    path = os.path.join(PROJ_DIR, "strong_index.js")
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Find the var strongIndex = { ... }
    m = re.search(r'\{([\s\S]*)\}', content)
    if not m:
        return {}
    obj_str = '{' + m.group(1) + '}'
    # Parse manually using regex to extract key-value pairs
    result = {}
    for m2 in re.finditer(r'"([^"]+)"\s*:\s*"([^"]+)"', obj_str):
        word = m2.group(1).strip().lower()
        strongs = m2.group(2).strip()
        result[word] = strongs
    return result

def load_aliases():
    """Load aliases.js as dict"""
    path = os.path.join(PROJ_DIR, "aliases.js")
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    result = {}
    for m in re.finditer(r'"([^"]+)"\s*:\s*"([^"]+)"', content):
        result[m.group(1).lower()] = m.group(2)
    return result

def extract_tagnt_spanish(path):
    """Extract Spanish word -> Strong number pairs from TAGNT"""
    mappings = {}  # word -> set of strong numbers
    word_counts = {}  # word -> count of occurrences
    
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            if len(row) < 9:
                continue
            # Check if it's a data row (has word ref in col 0)
            ref = row[0].strip()
            # Data rows contain things like Jhn.21.25#01=NKO or Mat.1.1#01=NKO
            if not re.match(r'^[A-Z][a-z]+\.\d+\.\d+#\d+', ref):
                continue
            dstrong_grammar = row[3].strip() if len(row) > 3 else ""
            spanish = row[8].strip() if len(row) > 8 else ""
            if not dstrong_grammar or not spanish:
                continue
            
            # Extract Strong number from "G1510=V-PAI-3S" format
            strong = None
            if '=' in dstrong_grammar:
                strong = dstrong_grammar.split('=')[0].strip()
            else:
                strong = dstrong_grammar.strip()
            
            if not strong.startswith('G'):
                continue
            
            # Clean Strong number: remove suffix letter
            base_strong = re.sub(r'[A-Za-z]$', '', strong)
            
            # Clean Spanish: remove parenthetical content, split on semicolons
            spanish_clean = re.sub(r'\([^)]*\)', '', spanish).strip()
            
            # Handle multi-word translations: take the first content word
            # But also try splitting
            words = re.findall(r'[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+', spanish_clean)
            for word in words:
                if len(word) < 2:
                    continue
                word_lower = normalize(word)
                if not word_lower:
                    continue
                if word_lower not in mappings:
                    mappings[word_lower] = set()
                mappings[word_lower].add(base_strong)
                if word_lower not in word_counts:
                    word_counts[word_lower] = 0
                word_counts[word_lower] += 1
    
    return mappings, word_counts

def extract_tipnr_proper_names(path):
    """Extract proper name -> Strong number pairs from TIPNR"""
    names = {}  # normalized_name -> set of strong numbers
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Each data line contains: Named\tName@Ref\tStrong\tesv_name\t...
    # Lines may have leading characters like "? Named\tName@..."
    for line in content.split('\n'):
        # Find "Named" followed by tab anywhere in the line
        idx = line.find('Named\t')
        if idx < 0:
            continue
        # Take everything after "Named\t"
        after = line[idx + 6:]  # len('Named\t') = 6
        parts = after.split('\t')
        if len(parts) < 3:
            continue
        full_name_ref = parts[0].strip()
        strong_field = parts[1].strip()
        esv_name = parts[2].strip()
        
        # Extract name (before @)
        name = full_name_ref.split('@')[0].strip()
        # Handle combined names like "Abijah|Abi@2Ki.18.2-2Ch"
        for n in name.split('|'):
            n = n.strip()
            if not n or n.startswith('('):
                continue
            
            # Extract Strong number
            # Format: H0175〜H0175=אהרן or H5653G〜H5653=אבדה
            strong_match = re.match(r'([HG]\d+[A-Za-z]?)', strong_field)
            if not strong_match:
                continue
            strong = strong_match.group(1)
            base_strong = re.sub(r'[A-Za-z]', '', strong)
            
            norm = normalize(n)
            if norm:
                if norm not in names:
                    names[norm] = set()
                names[norm].add(base_strong)
                
                # Also try without the ESV variant
                # e.g., "Jeshaiah|Isshiah" -> also try "Jeshaiah" -> "H3470"
                # and "Isshiah" -> "H3470"
    return names

def main():
    print("=" * 60)
    print("EXTRACCION DE MAPEOS ESPAÑOL -> STRONG")
    print("=" * 60)
    
    # Load current data
    strong_index = load_strong_index()
    aliases = load_aliases()
    
    print(f"\n[0] Datos actuales:")
    print(f"  strong_index.js: {len(strong_index)} entradas")
    print(f"  aliases.js: {len(aliases)} entradas")
    
    all_spanish_strongs = {}
    all_word_counts = {}
    
    # Step 1: Extract from TAGNT Spanish column
    print("\n[1] Extrayendo TAGNT (NT griego -> español)...")
    tagnt_files = [f for f in os.listdir(STEP_DIR) if f.startswith('TAGNT')]
    for fname in tagnt_files:
        path = os.path.join(STEP_DIR, fname)
        print(f"  Procesando {fname}...")
        try:
            mappings, counts = extract_tagnt_spanish(path)
            for word, strongs in mappings.items():
                if word not in all_spanish_strongs:
                    all_spanish_strongs[word] = set()
                all_spanish_strongs[word] |= strongs
            for word, c in counts.items():
                if word not in all_word_counts:
                    all_word_counts[word] = 0
                all_word_counts[word] += c
            print(f"    {len(mappings)} palabras únicas extraídas")
        except Exception as e:
            print(f"    Error: {e}")
    
    print(f"\n  Total palabras únicas de TAGNT: {len(all_spanish_strongs)}")
    
    # Step 2: Extract from TIPNR
    print("\n[2] Extrayendo TIPNR (nombres propios)...")
    tipnr_path = os.path.join(STEP_DIR, "TIPNR.txt")
    tipnr_names = {}
    if os.path.exists(tipnr_path):
        tipnr_names = extract_tipnr_proper_names(tipnr_path)
        print(f"  {len(tipnr_names)} nombres propios extraídos")
    else:
        print(f"  Archivo no encontrado: {tipnr_path}")
    
    # Step 3: Analyze what's new
    print("\n[3] Analizando nuevas coberturas...")
    
    # TAGNT -> what's NOT in strong_index.js
    tagnt_new = {}
    tagnt_single = {}
    for word, strongs in all_spanish_strongs.items():
        if word not in strong_index and word not in aliases:
            tagnt_new[word] = list(strongs)
            if len(strongs) == 1:
                tagnt_single[word] = list(strongs)[0]
    
    print(f"\n  Palabras de TAGNT con Strong sencillo NO en índice: {len(tagnt_single)}")
    print(f"  Palabras de TAGNT con múltiples Strongs NO en índice: {len(tagnt_new) - len(tagnt_single)}")
    
    # TIPNR -> what's NOT in strong_index.js
    tipnr_new = {}
    tipnr_single = {}
    for name, strongs in tipnr_names.items():
        if name not in strong_index and name not in aliases:
            tipnr_new[name] = list(strongs)
            if len(strongs) == 1:
                tipnr_single[name] = list(strongs)[0]
    
    print(f"\n  Nombres TIPNR con Strong sencillo NO en índice: {len(tipnr_single)}")
    print(f"  Nombres TIPNR con múltiples Strongs NO en índice: {len(tipnr_new) - len(tipnr_single)}")
    
    # Step 4: Generate alias suggestions 
    print("\n[4] Generando sugerencias de aliases...")
    
    # Single-candidate TAGNT Spanish words -> aliases
    tagnt_alias_lines = []
    for word in sorted(tagnt_single.keys()):
        strong = tagnt_single[word]
        # Use accented form? We have normalized (unaccented) form. 
        # Let's add the normalized form as that's what our matching does.
        # But we should try to preserve the most common accented form
        # For now, add normalized form to match fallback logic
        tagnt_alias_lines.append(f'    "{word}":"{strong}"')
    
    # Single-candidate TIPNR names -> aliases
    tipnr_alias_lines = []
    for name in sorted(tipnr_single.keys()):
        strong = tipnr_single[name]
        tipnr_alias_lines.append(f'    "{name}":"{strong}"')
    
    # Also check if any existing aliases or strong_index entries could be expanded
    # with additional Strong numbers from TAGNT
    expansion_lines = []
    for word, strongs in sorted(all_spanish_strongs.items()):
        if word in strong_index:
            existing = set(strong_index[word].split(';'))
            new_strongs = [s for s in strongs if s not in existing and s.startswith('G')]
            if new_strongs:
                # Only suggest if all new Strongs are from the same testament
                expansion_lines.append(f'    // "{word}" actual: "{strong_index[word]}" -> agregar: {new_strongs}')
    
    print(f"\n  Nuevos aliases sugeridos de TAGNT: {len(tagnt_alias_lines)}")
    print(f"  Nuevos aliases sugeridos de TIPNR: {len(tipnr_alias_lines)}")
    print(f"  Expansiones sugeridas para strong_index: {len(expansion_lines)}")
    
    # Step 5: Save analysis
    output = {
        "stats": {
            "tagnt_spanish_words": len(all_spanish_strongs),
            "tagnt_single_candidate_new": len(tagnt_single),
            "tagnt_multi_candidate_new": len(tagnt_new) - len(tagnt_single),
            "tipnr_proper_names": len(tipnr_names),
            "tipnr_single_candidate_new": len(tipnr_single),
        },
        "tagnt_single_candidates": {k: v for k, v in tagnt_single.items()},
        "tagnt_multi_candidates": {k: sorted(list(all_spanish_strongs[k])) 
                                    for k in sorted(all_spanish_strongs.keys()) 
                                    if k in tagnt_new and k not in tagnt_single},
        "tipnr_single_candidates": {k: v for k, v in tipnr_single.items()},
    }
    
    out_path = os.path.join(STEP_DIR, "spanish_strong_extraction.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  Análisis guardado en {out_path}")
    
    # Also generate a ready-to-use aliases snippet
    # Limit to reliable mappings
    tagnt_entries = []
    for word, strong in sorted(tagnt_single.items()):
        # Only include if the word appears at least 2 times (to filter rare errors)
        count = all_word_counts.get(word, 0)
        if count >= 2:
            tagnt_entries.append(f'    "{word}":"{strong}"')
    
    tipnr_entries = []
    for name, strong in sorted(tipnr_single.items()):
        tipnr_entries.append(f'    "{name}":"{strong}"')
    
    print(f"\n  Aliases confiables de TAGNT (≥2 ocurrencias): {len(tagnt_entries)}")
    print(f"  Aliases confiables de TIPNR: {len(tipnr_entries)}")
    print(f"  TOTAL sugerido: {len(tagnt_entries) + len(tipnr_entries)}")

if __name__ == "__main__":
    main()
