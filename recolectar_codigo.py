# -*- coding: utf-8 -*-
"""
Created on Tue Nov 11 20:57:40 2025

@author: jvz16
"""

### POWERSHELL ###
# cd "C:\Users\jvz16\Proyectos\ordero"
# & "C:\Users\jvz16\anaconda3\python.exe" -m venv .venv
# .\.venv\Scripts\Activate.ps1
# python recolectar_codigo.py



import os

# CONFIGURACIÓN: tú solo cambias ESTA línea con la ruta de tu proyecto
PROJECT_ROOT = r"C:\Users\jvz16\Proyectos\salon_agenda"  # <-- pon aquí la raíz de tu proyecto

# nombre del archivo de salida en la raíz del proyecto
OUTPUT_FILENAME = "codigo_proyecto_completo.txt"

# extensiones que consideraremos "de código" o texto
ALLOWED_EXTENSIONS = {
    ".py", ".html", ".htm", ".css", ".js", ".ts", ".tsx",
    ".json", ".md", ".txt", ".yml", ".yaml", ".env",
    ".ini", ".cfg", ".sh", ".bat", ".ps1", ".xml",
    ".csv", ".sql", ".jinja", ".j2", ".vue"
}

# carpetas a ignorar
IGNORED_DIRS = {
    ".git", "__pycache__", ".venv", "venv",
    "node_modules", "dist", "build", ".mypy_cache",
    ".pytest_cache"
}

def should_skip_dir(dirname: str) -> bool:
    return dirname in IGNORED_DIRS

def should_include_file(filename: str) -> bool:
    _, ext = os.path.splitext(filename)
    return ext.lower() in ALLOWED_EXTENSIONS

def main():
    project_root = os.path.abspath(PROJECT_ROOT)
    output_path = os.path.join(project_root, OUTPUT_FILENAME)

    with open(output_path, "w", encoding="utf-8") as outfile:
        outfile.write(f"RECOLECCIÓN DE ARCHIVOS DEL PROYECTO: {project_root}\n")
        outfile.write("=" * 80 + "\n\n")

        for root, dirs, files in os.walk(project_root):
            # filtrar directorios no deseados
            dirs[:] = [d for d in dirs if not should_skip_dir(d)]

            for fname in files:
                if not should_include_file(fname):
                    continue

                file_path = os.path.join(root, fname)
                rel_path = os.path.relpath(file_path, project_root)

                outfile.write(f"\n>>> ARCHIVO: {rel_path}\n")
                outfile.write("-" * 80 + "\n")

                try:
                    with open(file_path, "r", encoding="utf-8") as infile:
                        outfile.write(infile.read())
                except UnicodeDecodeError:
                    # por si algún archivo de texto no está en utf-8
                    try:
                        with open(file_path, "r", encoding="latin-1") as infile:
                            outfile.write(infile.read())
                    except Exception as e:
                        outfile.write(f"[NO SE PUDO LEER ESTE ARCHIVO: {e}]\n")
                except Exception as e:
                    outfile.write(f"[ERROR LEYENDO ARCHIVO: {e}]\n")

                outfile.write("\n" + "=" * 80 + "\n")

    print(f"Listo. Se guardó todo en: {output_path}")

if __name__ == "__main__":
    main()
