# especial agradecimiento a Shizmob por su codigo fuente de rpa tool con el cual cree esta herramienta si quieren pasarse por su github: https://github.com/shizmob/rpatool
from __future__ import print_function

import os
import sys
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# =============================
# Pickle robusto
# =============================
try:
    import pickle5 as pickle
except Exception:
    import pickle


def _unpickle(data):
    try:
        return pickle.loads(data, encoding="latin1")
    except TypeError:
        return pickle.loads(data)


# =============================
# RenPyArchive (tu clase, recortada a lo necesario)
# =============================
import codecs
import errno
import random


class RenPyArchive:
    RPA2_MAGIC = 'RPA-2.0 '
    RPA3_MAGIC = 'RPA-3.0 '
    RPA3_2_MAGIC = 'RPA-3.2 '

    def __init__(self, file=None):
        self.file = file
        self.handle = None
        self.indexes = {}
        self.key = 0

        if file:
            self.load(file)

    def __del__(self):
        if self.handle:
            self.handle.close()

    def get_version(self):
        self.handle.seek(0)
        magic = self.handle.readline().decode("utf-8")

        if magic.startswith(self.RPA3_2_MAGIC):
            return 3.2
        elif magic.startswith(self.RPA3_MAGIC):
            return 3
        elif magic.startswith(self.RPA2_MAGIC):
            return 2
        elif self.file.endswith(".rpi"):
            return 1

        raise ValueError("Archivo RPA no soportado")

    def extract_indexes(self):
        self.handle.seek(0)
        metadata = self.handle.readline()
        vals = metadata.split()

        offset = int(vals[1], 16)

        if self.version in (3, 3.2):
            self.key = 0
            start = 2 if self.version == 3 else 3
            for subkey in vals[start:]:
                self.key ^= int(subkey, 16)

        self.handle.seek(offset)
        contents = codecs.decode(self.handle.read(), "zlib")
        indexes = _unpickle(contents)

        if self.version in (3, 3.2):
            new_indexes = {}
            for k in indexes:
                new_indexes[k] = [
                    (a ^ self.key, b ^ self.key)
                    for a, b, *rest in indexes[k]
                ]
            indexes = new_indexes

        return indexes

    def load(self, filename):
        self.file = filename
        self.handle = open(filename, "rb")
        self.version = self.get_version()
        self.indexes = self.extract_indexes()

    def list(self):
        return list(self.indexes.keys())

    def read(self, filename):
        (offset, length) = self.indexes[filename][0]
        self.handle.seek(offset)
        return self.handle.read(length)


# =============================
# Utilidades RPA
# =============================
def find_rpa_files(root_folder):
    rpas = []
    for root, _, files in os.walk(root_folder):
        for f in files:
            if f.lower().endswith(".rpa"):
                rpas.append(os.path.join(root, f))
    return rpas


def extract_rpa_file(rpa_path, output_dir):
    archive = RenPyArchive(rpa_path)

    for filename in archive.list():
        try:
            data = archive.read(filename)
            out_path = os.path.join(output_dir, filename)

            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            with open(out_path, "wb") as f:
                f.write(data)

        except Exception as e:
            print("[RPA ERROR]", filename, e)


# =============================
# Decompilar RPYC (robusto)
# =============================
def decompile_rpyc(root_folder, status_callback=None):
    """
    Decompila todos los .rpyc usando unrpyc (sin abrir segunda GUI)
    """
    try:
        import unrpyc

        if status_callback:
            status_callback("🔎 Buscando archivos .rpyc...")

        # Verificar si existen .rpyc antes de intentar
        found = False
        for root, _, files in os.walk(root_folder):
            for f in files:
                if f.lower().endswith(".rpyc"):
                    found = True
                    break
            if found:
                break

        if not found:
            if status_callback:
                status_callback("ℹ️ No se encontraron .rpyc")
            return

        if status_callback:
            status_callback("⚙️ Decompilando scripts...")

        unrpyc.decompile_game(root_folder)

        if status_callback:
            status_callback("✅ Scripts decompilados correctamente")

    except Exception as e:
        print("[RPYC ERROR]", e)
        if status_callback:
            status_callback("❌ Error al decompilar scripts")


# =============================
# PROCESO PRINCIPAL
# =============================
def process_game(root_folder, status_callback=None, progress_callback=None):
    if status_callback:
        status_callback("Buscando archivos RPA...")

    rpa_files = find_rpa_files(root_folder)

    if not rpa_files:
        if status_callback:
            status_callback("No se encontraron RPA")
        return

    output_dir = os.path.join(root_folder, "extracted")
    total = len(rpa_files)

    for i, rpa in enumerate(rpa_files, start=1):
        if status_callback:
            status_callback(f"Extrayendo {os.path.basename(rpa)}")

        extract_rpa_file(rpa, output_dir)

        if progress_callback:
            progress_callback(i, total)

    decompile_rpyc(root_folder, status_callback)

    if status_callback:
        status_callback("✅ Todo completado")


# =============================
# GUI
# =============================
ROOT_DIR = None


def select_root():
    global ROOT_DIR
    path = filedialog.askdirectory(title="Seleccionar carpeta del juego")
    if not path:
        return

    ROOT_DIR = path
    root_label.config(text="Carpeta seleccionada ✅")


def run_extraction():
    process_game(
        ROOT_DIR,
        status_callback=lambda t: status.config(text=t),
        progress_callback=lambda i, t: progress.config(maximum=t, value=i),
    )


def start_extraction():
    if not ROOT_DIR:
        messagebox.showwarning("Aviso", "Selecciona una carpeta primero")
        return

    thread = threading.Thread(target=run_extraction)
    thread.start()


# =============================
# Ventana
# =============================
app = tk.Tk()
app.title("RPA TOOL by Vuistaz v1.0")
app.geometry("420x260")
app.resizable(False, False)

title = tk.Label(app, text="RPA TOOL", font=("Segoe UI", 14, "bold"))
title.pack(pady=10)

tk.Button(app, text="Seleccionar carpeta del juego", command=select_root).pack(pady=5)

root_label = tk.Label(app, text="No seleccionada")
root_label.pack()

tk.Button(app, text="🚀 Desencriptar", command=start_extraction).pack(pady=10)

progress = ttk.Progressbar(app, length=300)
progress.pack(pady=5)

status = tk.Label(app, text="Esperando...")
status.pack()
# ----------------- Agradecimientos -----------------
credits = tk.Label(
    app, 
    text="Código base adaptado de rpatool - por Shizmob", 
    font=("Segoe UI", 8), 
    fg="gray"
)
credits.pack(pady=5)
app.mainloop()
