"""
Extraer la Biblia Reina Valera 1960 desde PDF a JSON.

Uso:
    pip install PyMuPDF pdfplumber
    python extraer_biblia.py

Requiere: PyMuPDF (fitz) o pdfplumber
El PDF debe estar en la raíz del proyecto: ../Biblia Reina-Valera 1960 - Anonimo.pdf
"""

import os, re, json, gzip

# Intentar importar librería PDF
try:
    import fitz
    ENGINE = 'fitz'
except ImportError:
    try:
        import pdfplumber
        ENGINE = 'pdfplumber'
    except ImportError:
        print("ERROR: Necesitas instalar PyMuPDF o pdfplumber:")
        print("  pip install PyMuPDF")
        exit(1)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH = os.path.join(BASE_DIR, "Biblia Reina-Valera 1960 - Anonimo.pdf")
OUT_PATH = os.path.join(BASE_DIR, "estudio", "kittelProject", "rv1960_from_pdf.json")
OUT_GZ = os.path.join(BASE_DIR, "estudio", "kittelProject", "rv1960_from_pdf.json.gz")

if not os.path.exists(PDF_PATH):
    print(f"No se encontró el PDF: {PDF_PATH}")
    exit(1)

print(f"Leyendo PDF: {PDF_PATH}")
print(f"Motor: {ENGINE}")

def extract_text_fitz(path):
    doc = fitz.open(path)
    lines = []
    for i in range(len(doc)):
        page = doc[i]
        text = page.get_text()
        for line in text.split('\n'):
            s = line.strip()
            if s:
                lines.append((i + 1, s))
    doc.close()
    return lines

def extract_text_pdfplumber(path):
    import pdfplumber
    lines = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                for line in text.split('\n'):
                    s = line.strip()
                    if s:
                        lines.append((i + 1, s))
    return lines

if ENGINE == 'fitz':
    raw_lines = extract_text_fitz(PDF_PATH)
else:
    raw_lines = extract_text_pdfplumber(PDF_PATH)

print(f"  Líneas extraídas: {len(raw_lines)}")

# --- Aquí iría la lógica de parseo de libros/capítulos/versículos ---
# La estructura del PDF puede variar. Este es un esqueleto que debes
# adaptar según el formato real del PDF.

# Heurística simple: detectar patrones de libros y capítulos
# Ejemplo de referencia: "Génesis 1:1" o "1:1" al inicio de línea
BOOK_RE = re.compile(r'^(Génesis|Éxodo|Levítico|Números|Deuteronomio|'
    r'Josué|Jueces|Rut|1 Samuel|2 Samuel|1 Reyes|2 Reyes|'
    r'1 Crónicas|2 Crónicas|Esdras|Nehemías|Ester|Job|Salmos|'
    r'Proverbios|Eclesiastés|Cantares|Isaías|Jeremías|Lamentaciones|'
    r'Ezequiel|Daniel|Oseas|Joel|Amós|Abdías|Jonás|Miqueas|'
    r'Nahúm|Habacuc|Sofonías|Hageo|Zacarías|Malaquías|'
    r'S\. Mateo|S\. Marcos|S\. Lucas|S\.Juan|Hechos|'
    r'Romanos|1 Corintios|2 Corintios|Gálatas|Efesios|'
    r'Filipenses|Colosenses|1 Tesalonicenses|2 Tesalonicenses|'
    r'1 Timoteo|2 Timoteo|Tito|Filemón|Hebreos|'
    r'Santiago|1 Pedro|2 Pedro|1 Juan|2 Juan|3 Juan|'
    r'Judas|Apocalipsis)\s+(\d+)$', re.UNICODE)

CHAPTER_RE = re.compile(r'^\s*(\d+)\s*$')
VERSE_RE = re.compile(r'^\s*(\d+)\s+(.+)$')

print("NOTA: Este script es un esqueleto. Debes adaptar la lógica de")
print("      extracción según el formato específico del PDF.")
print("      Por ahora, los datos se cargan desde la fuente online en rv1960.js")
print()
print("Para regenerar desde la fuente online ya descargada:")
print("  Los archivos rv1960.js y rv1960.json.gz ya están listos en")
print("  estudio/kittelProject/")
