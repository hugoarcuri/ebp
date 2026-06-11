import json, re, os, sys, math
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))

# === OT/NT BOOKS in canonical order (from BIBLE_DATA in rv1960.js) ===
ALL_BOOKS_CANONICAL = [
    "Génesis","Éxodo","Levítico","Números","Deuteronomio",
    "Josué","Jueces","Rut","1 Samuel","2 Samuel","1 Reyes","2 Reyes",
    "1 Crónicas","2 Crónicas","Esdras","Nehemías","Ester","Job",
    "Salmos","Proverbios","Eclesiastés","Cantares",
    "Isaías","Jeremías","Lamentaciones","Ezequiel","Daniel",
    "Oseas","Joel","Amós","Abdías","Jonás","Miqueas","Nahúm",
    "Habacuc","Sofonías","Hageo","Zacarías","Malaquías",
    "S. Mateo","S. Marcos","S. Lucas","S.Juan","Hechos",
    "Romanos","1 Corintios","2 Corintios","Gálatas","Efesios",
    "Filipenses","Colosenses","1 Tesalonicenses","2 Tesalonicenses",
    "1 Timoteo","2 Timoteo","Tito","Filemón","Hebreos",
    "Santiago","1 Pedro","2 Pedro","1 Juan","2 Juan","3 Juan",
    "Judas","Apocalipsis"
]
OT_BOOKS = set(ALL_BOOKS_CANONICAL[:39])
NT_BOOKS = set(ALL_BOOKS_CANONICAL[39:])

# === FUNCTION WORDS (from biblia.html) ===
FUNC_WORDS = {
    'el','la','los','las','lo','un','una','unos','unas',
    'y','e','o','u','ni','que','como','pero','sino','mas',
    'a','ante','bajo','con','contra','de','desde','durante','en','entre',
    'hacia','hasta','mediante','para','por','segun','sin','sobre','tras',
    'me','te','se','nos','os','le','les','mi','tu','su',
    'mis','tus','sus','del','al','no','si','ya',
    'yo','tu','ella','ello','nosotros','vosotros','ellos','ellas','usted',
    'quien','quienes','cual','cuales','cuanto','donde','cuando',
    'muy','tan','tanto','bien','mal','tambien','aun','cada',
    'todo','toda','todos','todas','otro','otra','otros','otras',
    'este','esta','esto','estos','estas','ese','esa','eso','esos','esas',
    'aquel','aquella','aquello','aquellos','aquellas',
    'he','has','ha','han','hemos','habeis','habia','habian','habra',
    'hay','hubo','era','eras','eramos','eran','fue','fueron','sea','sean',
    'soy','eres','es','somos','sois','son','sido','siendo',
    'estoy','estas','estamos','estais','estan','estaba','estaban',
    'estuvo','estuvieron','estara','estaran'
}

# Articles
ARTICLES = {'el','la','los','las','lo','un','una','unos','unas','del','al'}
# Pronouns
PRONOUNS = {'me','te','se','nos','os','le','les','mi','tu','su','mis','tus','sus',
            'yo','tu','ella','ello','nosotros','vosotros','ellos','ellas','usted',
            'quien','quienes','cual','cuales','cuanto','donde','cuando',
            'este','esta','esto','estos','estas','ese','esa','eso','esos','esas',
            'aquel','aquella','aquello','aquellos','aquellas',
            'todo','toda','todos','todas','otro','otra','otros','otras',
            'muy','tan','tanto','cada',
            'vuestro','vuestra','vuestros','vuestras',
            'nuestro','nuestra','nuestros','nuestras',
            'suyo','suya','suyos','suyas','mio','mia','mios','mias',
            'ti', 'si', 'consigo', 'cuyo', 'cuya', 'cuyos', 'cuyas'}
# Prepositions
PREPOSITIONS = {'a','ante','bajo','con','contra','de','desde','durante','en','entre',
                'hacia','hasta','mediante','para','por','segun','sin','sobre','tras',
                'y','e','o','u','ni','que','como','pero','sino','mas',
                'no','si','ya','aun','tambien','bien','mal',
                'porque','pues','aunque','sino','sin embargo','ademas',
                'entonces','asi','ahora','siempre','nunca','jamas',
                'tampoco','aqui','alli','allá', 'allí'}


def strip_accents(s):
    replacements = {
        '\u00e1': 'a', '\u00e9': 'e', '\u00ed': 'i', '\u00f3': 'o', '\u00fa': 'u',
        '\u00c1': 'A', '\u00c9': 'E', '\u00cd': 'I', '\u00d3': 'O', '\u00da': 'U',
        '\u00fc': 'u', '\u00dc': 'U', '\u00f1': 'n', '\u00d1': 'N'
    }
    for a, na in replacements.items():
        s = s.replace(a, na)
    return s

def tokenize_spanish(text):
    tokens = re.findall(r'(<[^>]+>)|([a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00fc\u00f1]+)|([^a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00fc\u00f1<]+)', text, re.IGNORECASE)
    result = []
    for html, word, sep in tokens:
        if word:
            result.append(word)
    return result

# === LEMMATIZE (mirrors biblia.html) ===
def lemmatize(w):
    candidates = [w]
    if w.endswith('ces') and len(w) > 4:
        candidates.append(w[:-3] + 'z')
    if w.endswith('es') and len(w) > 4:
        candidates.append(w[:-2])
        candidates.append(w[:-1])
    if w.endswith('s') and len(w) > 3 and not w.endswith('es'):
        candidates.append(w[:-1])
    ar_endings = ['aron','ado','ando','aba','aban','abas','ara','ase','aste','\u00e9','\u00f3']
    for e in ar_endings:
        if w.endswith(e) and len(w) > len(e) + 1:
            candidates.append(w[:-len(e)] + 'ar')
    er_ir_endings = ['ieron','ido','iendo','\u00eda','\u00edan','iera','iese','iste']
    for e in er_ir_endings:
        if w.endswith(e) and len(w) > len(e) + 1:
            candidates.append(w[:-len(e)] + 'er')
            candidates.append(w[:-len(e)] + 'ir')
    if w.endswith('yeron') and len(w) > 6:
        candidates.append(w[:-5] + 'er')
        candidates.append(w[:-5] + 'ir')
    return candidates

# === DATA LOADERS ===

def load_bible_text():
    """Load RV1960 from rv1960.js preserving book order."""
    with open(os.path.join(BASE, 'rv1960.js'), 'r', encoding='utf-8') as f:
        js = f.read()
    m = re.search(r'var\s+BIBLE_DATA\s*=\s*({.*?});\s*$', js, re.DOTALL)
    if not m:
        raise ValueError('Could not parse rv1960.js')
    data = json.loads(m.group(1))
    # Reorder to canonical order (JSON loads alphabetically)
    # We need to extract exact order from the JS var
    # Re-parse manually to preserve key order
    fixed = {}
    # Remove "lang" key
    for b in ALL_BOOKS_CANONICAL:
        if b in data:
            fixed[b] = data[b]
    return fixed

def load_interlinear_lookup():
    path = os.path.join(BASE, 'interlinear_lookup.js')
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        js = f.read()
    m = re.search(r'var\s+INTERLINEAR_LOOKUP\s*=\s*({.*?});\s*$', js, re.DOTALL)
    if not m:
        raise ValueError('Could not parse interlinear_lookup.js')
    return json.loads(m.group(1))

def load_strong_index():
    path = os.path.join(BASE, 'strong_index.js')
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        js = f.read()
    m = re.search(r'STRONG_INDEX\s*=\s*({.*?});', js, re.DOTALL)
    if not m:
        raise ValueError('Could not parse strong_index.js')
    raw_str = m.group(1)
    raw_str = re.sub(r'(\{)(\w+)(:)', r'\1"\2"\3', raw_str, count=1)
    raw_str = re.sub(r',(\w+)(:)', r',"\1"\2', raw_str)
    raw = json.loads(raw_str)
    return raw.get('single', {})

def load_aliases():
    path = os.path.join(BASE, 'aliases.js')
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        js = f.read()
    m = re.search(r'const\s+MANUAL_ALIASES\s*=\s*({.*?});', js, re.DOTALL)
    if not m:
        return {}
    raw_str = m.group(1)
    # Remove comments
    raw_str = re.sub(r'//.*', '', raw_str)
    # Remove trailing commas before closing braces
    raw_str = re.sub(r',\s*}', '}', raw_str)
    # Remove trailing commas before closing brackets
    raw_str = re.sub(r',\s*]', ']', raw_str)
    return json.loads(raw_str)

# === FALLBACK LOGIC (mirrors biblia.html) ===

def load_direct_strong():
    path = os.path.join(BASE, 'direct_strong.js')
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        js = f.read()
    m = re.search(r'const\s+DIRECT_STRONG\s*=\s*({.*?});', js, re.DOTALL)
    if not m:
        return {}
    obj_str = m.group(1)
    result = {}
    for m2 in re.finditer(r'"([^"]+)"\s*:\s*"([^"]+)"', obj_str):
        result[m2.group(1)] = m2.group(2)
    return result

def find_fallback(word, is_ot, is_nt, strong_index, aliases, direct_strong):
    lower = word.lower()
    stripped = strip_accents(lower)
    if stripped in FUNC_WORDS:
        return None, 'funcword'
    # 1. Check aliases first
    if stripped in aliases:
        lemma = aliases[stripped]
        entry = strong_index.get(strip_accents(lemma))
        if entry:
            nums = entry.split('||')[0].split(';')
            candidate = None
            for n in nums:
                if (is_ot and n.startswith('H')) or (is_nt and n.startswith('G')):
                    if candidate is None:
                        candidate = n
                    else:
                        return None, 'alias_ambiguous'
            if candidate:
                return candidate, 'alias'
    # 1b. Check direct_strong (word -> Strong number, bypass lemma lookup)
    if stripped in direct_strong:
        strong = direct_strong[stripped]
        if (is_ot and strong.startswith('H')) or (is_nt and strong.startswith('G')):
            return strong, 'direct_strong'
    # 2. Try original form
    entry = strong_index.get(stripped)
    if entry:
        nums = entry.split('||')[0].split(';')
        candidate = None
        for n in nums:
            if (is_ot and n.startswith('H')) or (is_nt and n.startswith('G')):
                if candidate is None:
                    candidate = n
                else:
                    return None, 'original_ambiguous'
        if candidate:
            return candidate, 'original'
    # 3. Try lemmas
    candidates = lemmatize(lower)
    seen = set()
    best = None
    best_count = float('inf')
    for c in candidates:
        key = strip_accents(c)
        if key in seen:
            continue
        seen.add(key)
        entry = strong_index.get(key)
        if not entry:
            continue
        nums = entry.split('||')[0].split(';')
        filtered = []
        for n in nums:
            if (is_ot and n.startswith('H')) or (is_nt and n.startswith('G')):
                filtered.append(n)
        if len(filtered) > 0 and len(filtered) < best_count:
            best = filtered[0]
            best_count = len(filtered)
    if best is not None and best_count == 1:
        return best, 'lemma'
    if best is not None and best_count > 1:
        return None, 'lemma_ambiguous'
    return None, 'not_found'

# Strong verb endings that are distinctive (unlikely for nouns)
STRONG_VERB_ENDINGS = ['aba', 'aban', 'aron', 'ieron', 'ando', 'iendo',
                        'aste', 'iste', 'ara', 'ase', 'iera', 'iese',
                        'amos', 'imos', 'ais', 'eis', 'isteis',
                        'ad', 'ed', 'id',
                        'aban', 'abas', 'aran', 'aras',
                        'asen', 'ases', 'asteis',
                        'isteis', 'imos']

# Common short verb forms not caught by ending heuristics
SHORT_VERBS = {'es','son','soy','eres','somos','sois','seas','sea','sean',
               'he','ha','has','han','hemos','habeis','hay','era','eras','eramos','eran',
               'fue','fui','fuiste','fue','fuimos','fue','fueron',
               'era','eras','eramos','eran',
               'estoy','estas','esta','estamos','estais','estan',
               'estaba','estaban',
               'tuve','tuviste','tuvo','tuvimos','tuvieron',
               'doy','das','da','damos','dais','dan',
               'di','diste','dio','dimos','dieron',
               've','ves','ven','veo','ven',
               'vi','viste','vio','vimos','vieron',
               'voy','vas','va','vamos','vais','van',
               'hago','haces','hace','hacemos','haceis','hacen',
               'hice','hiciste','hizo','hicimos','hicieron',
               'pongo','pones','pone','ponemos','poneis','ponen',
               'puse','pusiste','puso','pusimos','pusieron',
               'tengo','tienes','tiene','tenemos','teneis','tienen',
               'digo','dices','dice','decimos','decis','dicen',
               'dije','dijiste','dijo','dijimos','dijeron',
               'salgo','sales','sale','salimos','salis','salen',
               'sali','saliste','salio','salimos','salieron',
               'vengo','vienes','viene','venimos','venis','vienen',
               'vine','viniste','vino','vinimos','vinieron',
               'vivo','vives','vive','vivimos','vivis','viven',
               'puedo','puedes','puede','podemos','podeis','pueden',
               'pude','pudiste','pudo','pudimos','pudieron',
               'se','sabe','sabes','saben','sabemos','sabeis',
               'supe','supiste','supo','supimos','supieron',
               'habia','habian','habra','habran','habre','habras','habria','habrian',
               'habeis','hubo','hubieron','hubiera','hubieran','hubiese','hubiesen','hubiere',
               'haya','hayas','hayan','hayamos',
               'podia','podias','podian','podamos'}

def classify_word(word, strong_index=None):
    """Classify a word into: articulo, pronombre, preposicion, verbo, nombre_propio, sustantivo"""
    lower = word.lower()
    stripped = strip_accents(lower)
    if stripped in ARTICLES:
        return 'articulo'
    if stripped in PRONOUNS:
        return 'pronombre'
    if stripped in PREPOSITIONS:
        return 'preposicion'
    if stripped in SHORT_VERBS:
        return 'verbo'
    # Check if it's a known verb infinitive
    if any(stripped.endswith(e) for e in ('ar','er','ir')) and len(stripped) > 3:
        return 'verbo'
    # Check strong verb endings (not ambiguous with nouns)
    for ve in STRONG_VERB_ENDINGS:
        if stripped.endswith(ve) and len(stripped) - len(ve) >= 2:
            return 'verbo'
    # Proper name detection: not in strong_index + has biblical name patterns
    # Check this AFTER verb checks to avoid classifying verb forms as names
    if strong_index:
        in_index = stripped in strong_index
    else:
        in_index = False
    # Exclude common verb endings before trying proper name patterns
    VERB_ENDING_EXCLUDE = ('io','ia','ian','ieron','iendo','iera','iese')
    if not any(stripped.endswith(e) for e in VERB_ENDING_EXCLUDE):
        if stripped.endswith(('el','ai')) and len(stripped) >= 3 and len(stripped) <= 10 and not in_index:
            return 'nombre_propio'
        if stripped.endswith('on') and len(stripped) >= 4 and len(stripped) <= 10 and not in_index:
            return 'nombre_propio'
        if stripped.endswith(('ea','eo')) and len(stripped) >= 4 and not in_index:
            return 'nombre_propio'
        if stripped.endswith('im') and len(stripped) >= 4 and not in_index:
            return 'nombre_propio'
        if stripped.endswith(('an','en','in')) and len(stripped) == 4 and not in_index and stripped[0].isalpha():
            return 'nombre_propio'
    # Default: sustantivo
    return 'sustantivo'

def main():
    print("Cargando datos...")
    bible = load_bible_text()
    ilookup = load_interlinear_lookup()
    strong_index = load_strong_index()
    aliases = load_aliases()
    direct_strong = load_direct_strong()
    print(f"  Libros: {len(bible)}")
    print(f"  Interlinear verses: {len(ilookup)}")
    print(f"  Strong index entries: {len(strong_index)}")
    print(f"  Aliases: {len(aliases)}")
    print(f"  Direct strong: {len(direct_strong)}")
    
    # === STATS ===
    total_words = 0
    strong_words = 0
    interlinear_words = 0
    fallback_words = 0
    missing_words = 0
    
    strong_counter = Counter()        # Strong number -> freq
    recognized_word_counter = Counter()  # word text -> freq (for recognized words)
    missing_counter = Counter()       # word (lower) -> freq
    book_stats = {}                   # book -> {total, strong, missing}
    
    missing_word_info = {}            # missing word -> {freq, classification, suggestions}
    
    total_ot = 0
    total_nt = 0
    strong_ot = 0
    strong_nt = 0
    
    book_order = list(bible.keys())
    
    for book_idx, (book_name, chapters) in enumerate(bible.items()):
        is_ot = book_name in OT_BOOKS
        is_nt = book_name in NT_BOOKS
        book_total = 0
        book_strong = 0
        
        for ch_num, verses in chapters.items():
            for vs_num, text in verses.items():
                verse_ref = f"{book_name} {int(ch_num)}:{int(vs_num)}"
                words = tokenize_spanish(text)
                verse_lookup = ilookup.get(verse_ref, [])
                
                for word_idx, word_text in enumerate(words):
                    total_words += 1
                    book_total += 1
                    if is_ot: total_ot += 1
                    if is_nt: total_nt += 1
                    
                    has_strong = False
                    strong_num = None
                    source = None
                    
                    # Check interlinear
                    if word_idx < len(verse_lookup):
                        strongs = verse_lookup[word_idx]
                        if strongs and len(strongs) > 0:
                            has_strong = True
                            strong_num = strongs[0]
                            source = 'interlinear'
                            interlinear_words += 1
                    
                    # Check fallback
                    if not has_strong:
                        result, src = find_fallback(word_text, is_ot, is_nt, strong_index, aliases, direct_strong)
                        if result:
                            has_strong = True
                            strong_num = result
                            source = src
                            fallback_words += 1
                    
                    if has_strong:
                        strong_words += 1
                        book_strong += 1
                        if is_ot: strong_ot += 1
                        if is_nt: strong_nt += 1
                        strong_counter[strong_num] += 1
                        recognized_word_counter[word_text.lower()] += 1
                    else:
                        missing_words += 1
                        lower_word = word_text.lower()
                        missing_counter[lower_word] += 1
                        # Store first seen text for classification
                        if lower_word not in missing_word_info:
                            missing_word_info[lower_word] = {
                                'word': word_text,
                                'freq': 0,
                                'classification': classify_word(word_text, strong_index)
                            }
                        missing_word_info[lower_word]['freq'] = missing_counter[lower_word]
        
        book_stats[book_name] = {
            'total': book_total,
            'strong': book_strong,
            'missing': book_total - book_strong,
            'pct': round(100 * book_strong / book_total, 1) if book_total > 0 else 0
        }
        
        if (book_idx + 1) % 10 == 0 or book_idx == len(bible) - 1:
            pct = 100 * strong_words / total_words if total_words > 0 else 0
            print(f"  Procesados {book_idx + 1}/{len(bible)} libros | {total_words} palabras | {pct:.1f}% reconocido")
    
    # === GENERATE REPORT ===
    
    # Global stats
    global_pct = round(100 * strong_words / total_words, 1) if total_words > 0 else 0
    ot_pct = round(100 * strong_ot / total_ot, 1) if total_ot > 0 else 0
    nt_pct = round(100 * strong_nt / total_nt, 1) if total_nt > 0 else 0
    
    # ALL missing words (sorted)
    top_missing = missing_counter.most_common()
    
    # Generate normalization suggestions for all missing
    suggestions = []
    for word, freq in top_missing:
        info = missing_word_info.get(word, {})
        classification = info.get('classification', 'sustantivo')
        
        # Generate possible lemma
        lower = word.lower()
        stripped = strip_accents(lower)
        
        # Check plural -> singular
        singular = None
        if stripped.endswith('ces') and len(stripped) > 4:
            singular = stripped[:-3] + 'z'
        elif stripped.endswith('es') and len(stripped) > 4:
            singular = stripped[:-2]
        elif stripped.endswith('s') and len(stripped) > 3 and not stripped.endswith('es'):
            singular = stripped[:-1]
        
        # Check verb -> infinitive via lemmatize
        lemma_candidates = lemmatize(lower)
        infinitive = None
        if len(lemma_candidates) > 1:
            # Pick the infinitive (last candidates are the lemmatized forms)
            for lc in reversed(lemma_candidates):
                if lc != lower:
                    infinitive = lc
                    break
        
        # Check alias
        alias_target = aliases.get(stripped)
        
        suggestion = {
            'word': word,
            'freq': freq,
            'classification': classification,
            'possible_lemma': singular or infinitive or alias_target or None,
            'alias_exists': alias_target is not None
        }
        suggestions.append(suggestion)
    
    # Recalculate theoretical percentage if all suggestions applied
    # For each missing word, if a suggestion exists and the lemma exists in strong_index,
    # count it as potentially recoverable
    recoverable = 0
    still_missing = 0
    for word, count in missing_counter.items():
        stripped = strip_accents(word.lower())
        # Check alias
        if stripped in aliases:
            lemma = aliases[stripped]
            if strip_accents(lemma) in strong_index:
                recoverable += count
                continue
        # Check lemma
        lemma_candidates = lemmatize(word.lower())
        found = False
        for lc in lemma_candidates[1:]:
            key = strip_accents(lc)
            if key in strong_index:
                recoverable += count
                found = True
                break
        if not found:
            still_missing += count
    
    theoretical_pct = round(100 * (strong_words + recoverable) / total_words, 1) if total_words > 0 else 0
    theoretical_strong = strong_words + recoverable
    
    # TOP 500 Strong numbers used
    top_strong = strong_counter.most_common(500)
    
    # TOP 500 recognized words
    top_recognized = recognized_word_counter.most_common(500)
    
    # Coverage by book (for table)
    book_coverage = []
    for book in book_order:
        stats = book_stats.get(book, {})
        book_coverage.append({
            'book': book,
            'total': stats.get('total', 0),
            'strong': stats.get('strong', 0),
            'missing': stats.get('missing', 0),
            'pct': stats.get('pct', 0)
        })
    
    # === BUILD OUTPUT ===
    output = {
        'stats': {
            'total_words': total_words,
            'strong_words': strong_words,
            'interlinear_words': interlinear_words,
            'fallback_words': fallback_words,
            'missing_words': missing_words,
            'global_pct': global_pct,
            'ot_total': total_ot,
            'ot_strong': strong_ot,
            'ot_pct': ot_pct,
            'nt_total': total_nt,
            'nt_strong': strong_nt,
            'nt_pct': nt_pct,
            'theoretical_pct': theoretical_pct,
            'theoretical_strong': theoretical_strong,
            'still_missing': still_missing,
            'strong_index_entries': len(strong_index),
            'aliases_count': len(aliases)
        },
        'top_missing': [{'word': w, 'freq': c} for w, c in top_missing],
        'top_missing_suggestions': suggestions,
        'top_strong': [{'strong': s, 'freq': c} for s, c in top_strong],
        'top_recognized': [{'word': w, 'freq': c} for w, c in top_recognized],
        'book_coverage': book_coverage,
        'aliases': dict(sorted(aliases.items()))
    }
    
    # Save to JSON
    output_path = os.path.join(BASE, 'analisis_completo.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nReporte guardado en: {output_path}")
    
    # === PRINT SUMMARY ===
    print("\n" + "="*60)
    print("RESUMEN FINAL - ANÁLISIS DE COBERTURA STRONG")
    print("="*60)
    print(f"\n{'Total palabras:':<30} {total_words:>10,}")
    print(f"{'Con Strong (interlinear):':<30} {interlinear_words:>10,}  ({100*interlinear_words/total_words:.1f}%)")
    print(f"{'Con Strong (fallback):':<30} {fallback_words:>10,}  ({100*fallback_words/total_words:.1f}%)")
    print(f"{'Total con Strong:':<30} {strong_words:>10,}  ({global_pct}%)")
    print(f"{'Sin Strong:':<30} {missing_words:>10,}  ({100-100*strong_words/total_words:.1f}%)")
    print(f"\n{'Cobertura AT:':<30} {strong_ot:>10,} / {total_ot:,}  ({ot_pct}%)")
    print(f"{'Cobertura NT:':<30} {strong_nt:>10,} / {total_nt:,}  ({nt_pct}%)")
    print(f"\n{'Potencial con aliases:':<30} {theoretical_strong:>10,} / {total_words:,}  ({theoretical_pct}%)")
    print(f"{'Irrecuperables:':<30} {still_missing:>10,}")
    
    # Separate function words from content words
    EXCLUDED = ('articulo','pronombre','preposicion')
    content_suggestions = [s for s in suggestions if s['classification'] not in EXCLUDED]
    
    print(f"\n--- TOP 20 PALABRAS SIN STRONG (TODAS) ---")
    print(f"{'Palabra':<25} {'Free.':>8} {'Clasif.':<14} {'Sugerencia':<20}")
    print("-"*70)
    for s in suggestions[:20]:
        cls = s['classification']
        sug = s['possible_lemma'] or '-'
        print(f"{s['word']:<25} {s['freq']:>8} {cls:<14} {sug:<20}")
    
    print(f"\n--- TOP 1000 PALABRAS DE CONTENIDO SIN STRONG ---")
    print(f"{'#':>4} {'Palabra':<25} {'Free.':>8} {'Clasif.':<14} {'Sugerencia':<20}")
    print("-"*75)
    for i, s in enumerate(content_suggestions[:1000], 1):
        cls = s['classification']
        sug = s['possible_lemma'] or '-'
        print(f"{i:>4} {s['word']:<25} {s['freq']:>8} {cls:<14} {sug:<20}")
    
    # Count function words total
    func_missing = sum(s['freq'] for s in suggestions if s['classification'] in EXCLUDED)
    content_missing = sum(s['freq'] for s in content_suggestions)
    print(f"\n  Palabras funcionales sin Strong: {func_missing:,} ({100*func_missing/missing_words:.1f}% del total sin Strong)")
    print(f"  Palabras de contenido sin Strong: {content_missing:,} ({100*content_missing/missing_words:.1f}% del total sin Strong)")
    print(f"  Palabras de contenido unicas: {len(content_suggestions):,}")
    
    print(f"\n--- TOP 20 STRONG MAS USADOS ---")
    print(f"{'Strong':<12} {'Free.':>8}")
    print("-"*25)
    for s, c in top_strong[:20]:
        print(f"{s:<12} {c:>8}")
    
    print(f"\n--- COBERTURA POR LIBRO (Top 10 mejores / peores) ---")
    sorted_books = sorted(book_coverage, key=lambda x: x['pct'], reverse=True)
    print(f"\nMejores:")
    print(f"{'Libro':<25} {'Total':>8} {'Strong':>8} {'%':>6}")
    print("-"*50)
    for b in sorted_books[:10]:
        print(f"{b['book']:<25} {b['total']:>8} {b['strong']:>8} {b['pct']:>5}%")
    print(f"\nPeores:")
    for b in sorted_books[-10:]:
        print(f"{b['book']:<25} {b['total']:>8} {b['strong']:>8} {b['pct']:>5}%")
    
    print("\n" + "="*60)

if __name__ == '__main__':
    main()
