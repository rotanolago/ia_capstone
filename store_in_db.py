import subprocess,sys
import sqlite3 

if len(sys.argv) > 1:
    # The first command-line argument is at sys.argv[1]
    command = sys.argv[1]
    print(f"The first command-line argument is: {command}")
else:
    print("No command-line arguments provided.")

raw = subprocess.run(f"man {command}", shell = True, capture_output=True, text=True, executable="/bin/bash")

def save_man_to_sqlite(comando, raw_text):
    conn = sqlite3.connect('manuales_ai.db')
    cursor = conn.cursor()

    # Tip: En un RAG real, aquí usarías regex para dividir el manual
    # por secciones (OPTIONS, DESCRIPTION, etc.)
    # Para este ejemplo, guardamos el bloque principal:

    secciones = {
        "FULL_TEXT": raw_text,
        "SYNOPSIS": extract_section(raw_text, "SYNOPSIS"), # Función imaginaria de regex
        "OPTIONS": extract_section(raw_text, "OPTIONS")
    }

    for nombre_sec, contenido in secciones.items():
        if contenido:
            cursor.execute('''
                INSERT INTO man_pages (comando, seccion_nombre, contenido, raw_man_text)
                VALUES (?, ?, ?, ?)
            ''', (comando, nombre_sec, contenido, raw_text))

    conn.commit()
    print(f"✅ [Data Prep] '{comando}' guardado correctamente en SQLite.")
    conn.close()

def extract_section(text, section_name):
    # Lógica simple para extraer secciones de un man page
    import re
    pattern = rf"{section_name}\n(.*?)(?=\n[A-Z ]+\n|$)"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else None

save_man_to_sqlite(command, raw.stdout)
