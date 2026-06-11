"""Generate direct_strong.js from TAGNT + TIPNR extraction data"""
import json, os, sys, re

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

PROJ_DIR = "C:\\Users\\LAPTOP\\OneDrive - dts.edu\\proyectos_programacion\\ebp\\kittelProject"
STEP_DIR = os.path.join(PROJ_DIR, "source_data", "step")
OUTPUT = os.path.join(PROJ_DIR, "direct_strong.js")

def main():
    # Load extraction results
    with open(os.path.join(STEP_DIR, "spanish_strong_extraction.json"), 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    tagnt_single = data["tagnt_single_candidates"]  # normalized word -> strong number
    tipnr_single = data["tipnr_single_candidates"]  # normalized name -> strong number
    
    # Spanish words in our Bible for cross-reference
    bible_path = os.path.join(PROJ_DIR, "rv1960.js")
    spanish_words = set()
    with open(bible_path, 'r', encoding='utf-8') as f:
        content = f.read()
    for m in re.finditer(r'"([^"]+)"', content):
        for w in re.findall(r'[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+', m.group(1)):
            spanish_words.add(w)
    print(f"Palabras en RV1960: {len(spanish_words)}")
    
    # Build direct mappings: for each Spanish word in our text, check if TAGNT has it
    direct = {}
    for sw in sorted(spanish_words):
        # Normalize
        import unicodedata
        nfkd = unicodedata.normalize('NFKD', sw.lower())
        norm = ''.join(c for c in nfkd if not unicodedata.combining(c))
        if norm in tagnt_single:
            direct[sw.lower()] = tagnt_single[norm]
        elif norm in tipnr_single and sw[0].isupper():
            # Proper names: check TIPNR
            direct[sw.lower()] = tipnr_single[norm]
    
    print(f"Coincidencias directas: {len(direct)}")
    
    # Also add lemmatized suggestions from TAGNT that weren't already matched
    # For words where the original form didn't match but a lemma might
    extra = {}
    for norm, strong in tagnt_single.items():
        if norm not in direct and norm not in [v.lower() for v in direct.values()]:
            # Check if this normalized word could be a lemma for some Spanish word
            # e.g., "hablar" is a lemma, "hablo" is an inflected form
            # We already handle this via the normal lemmatizer
            pass
    
    # Generate JS file
    lines = []
    lines.append("// Direct word -> Strong number mappings from STEPBible TAGNT (CC BY 4.0)")
    lines.append("// Generated from Greek NT Spanish-translation column + TIPNR proper names")
    lines.append("")
    lines.append("const DIRECT_STRONG = {")
    
    for word in sorted(direct.keys()):
        strong = direct[word]
        lines.append(f'    "{word}":"{strong}",')
    
    lines.append("};")
    
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"Guardado: {OUTPUT}")
    print(f"Entradas: {len(direct)}")

if __name__ == "__main__":
    main()
