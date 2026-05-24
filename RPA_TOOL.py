# ===================
# CHANGELOG
# ===================
# 1.0 primera version / bugs encontrados: problemas con algunas funciones y ui pero programa funcional
# 1.1:
## v1.1 - Mejoras de estabilidad y UI

### 🔧 Fixes
#- Corregido freeze de la interfaz (uso de callbacks thread-safe con `app.after`)
#- Corregido error de cierre de archivos RPA (uso de `try/finally`)
#- Corregido posible crash silencioso en el proceso principal
#- Corregido comportamiento de la barra de progreso

### ⚡ Mejoras
#- Implementación de sistema de progreso funcional
#- Mejora en mensajes de estado (más claros y descriptivos)
#- Indicador de progreso por archivo `(actual/total)`
#- Detección automática de archivos `.rpa`
#- Verificación previa de existencia de archivos `.rpyc`
#- Creación automática de carpeta `extracted`
#- Advertencia si la carpeta `extracted` ya existe

### 🧠 UI / UX
#- Interfaz ahora completamente responsive (sin bloqueos)
#- Botón deshabilitado durante la extracción para evitar múltiples ejecuciones
#- Actualización en tiempo real de estado y progreso
#- Mejor feedback visual al usuario

### 🧹 Limpieza
#- Eliminado soporte para archivos `.td` (inestable y costoso en recursos)
#- Código simplificado y más mantenible
#- Manejo de errores más robusto

### 🔒 Estabilidad
#- Mejor manejo de excepciones globales
#- Prevención de conflictos entre threads y Tkinter
#- Mayor compatibilidad al compilar con PyInstaller
# especial agradecimiento a Shizmob por su codigo fuente de rpa tool con el cual cree esta herramienta si quieren pasarse por su github: https://github.com/shizmob/rpatool

# Update 1.2
#🌐 1. Sistema Internacional de Idiomas (i18n)
##Traducción en Tiempo Real: Se añadió soporte completo bilingüe (Español ↔ Inglés).
#Control Inteligente de Idioma: Se incorporó un menú desplegable moderno (ttk.Combobox) en la esquina superior derecha para alternar idiomas con un clic.
#Persistencia de Estado: Al cambiar el idioma a mitad de un proceso de desencriptación, los estados internos dinámicos (como "Buscando archivos..." o "Decompilando...") se traducen al instante sin alterar el flujo del hilo secundario.
#🎨 2. Rediseño Completo de la Interfaz Gráfica (UI Modernizada)
#Tema Oscuro Integrado: Se eliminó el estilo gris clásico de Windows, sustituyéndolo por una paleta oscura y elegante con contrastes de colores pastel (#1E1E2E, #313244 y #A6E3A1).
#Botones con Diseño Plano (Flat UI): Se removieron los bordes tridimensionales antiguos (bd=0) y se configuró margen interno (padx/pady) para crear botones más estilizados.
#Efectos de Cursor Interactivos: Se programaron transiciones de color (activebackground y activeforeground) en los botones para que respondan visualmente cuando pasas el ratón o haces clic.
#Barra de Progreso y Componentes Estilizados: Se configuró el motor de estilos ttk.Style(theme="clam") para integrar la barra de progreso de forma armónica al tema oscuro.
#🔧 3. Correcciones de Código y Estabilidad (Bugfixes)
#Error de Parámetro en Botones: Se corrigió el uso ilegal de padding= en los componentes tk.Button tradicionales (que causaba el "Fatal Error" de Python al buscar la propiedad nativa de ttk), reemplazándolo por padx y pady.
#Sintaxis de Código Desestructurado: Se repararon múltiples líneas colapsadas por fallas de copiado (como last_status_extralast_status_key), reestructurando el código con la indentación exacta obligatoria de Python.
#Restauración de Eventos de Interfaz: Se corrigió el trigger de detección del idioma enlazando el evento correcto (<<ComboboxSelected>>) que se encontraba borrado.
#Unificación de Bucle Principal: Se removieron ejecuciones duplicadas de la ventana principal garantizando un único punto de entrada con app.mainloop() al cierre del script.
# -*- coding: utf-8 -*-
# especial agradecimiento a Shizmob por su codigo fuente de rpa tool con el cual cree esta herramienta si quieren pasarse por su github: https://github.com
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
# RenPyArchive (Lógica Arreglada)
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

        if len(vals) < 2:
            raise ValueError("Estructura de cabecera corrupta o inválida")

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
    try:
        for filename in archive.list():
            try:
                data = archive.read(filename)
                out_path = os.path.join(output_dir, filename)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "wb") as f:
                    f.write(data)
            except Exception as e:
                print("[RPA ERROR]", filename, e)
    finally:
        if archive.handle:
            archive.handle.close()


# =============================
# Decompilar RPYC (robusto)
# =============================
def decompile_rpyc(root_folder, status_callback=None):
    try:
        import unrpyc

        if status_callback:
            status_callback("msg_searching_rpyc")

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
                status_callback("msg_no_rpyc")
            return

        if status_callback:
            status_callback("msg_decompiling")

        unrpyc.decompile_game(root_folder)

        if status_callback:
            status_callback("msg_decompiled_ok")

    except Exception as e:
        print("[RPYC ERROR]", e)
        if status_callback:
            status_callback("msg_err_rpyc")


# =============================
# PROCESO PRINCIPAL
# =============================
def process_game(root_folder, status_callback=None, progress_callback=None):
    def update_status(msg_key, extra=""):
        if status_callback:
            status_callback(msg_key, extra)

    def update_progress(i, total):
        if progress_callback:
            progress_callback(i, total)

    update_status("msg_searching_rpa")
    rpa_files = find_rpa_files(root_folder)

    print("RPA encontrados:", rpa_files)

    if not rpa_files:
        update_status("msg_no_rpa")
        return

    output_dir = os.path.join(root_folder, "extracted")
    if os.path.exists(output_dir):
        update_status("msg_overwrite_warn")
    os.makedirs(output_dir, exist_ok=True)

    total = len(rpa_files)
    current = 0

    for rpa in rpa_files:
        current += 1
        base_name = os.path.basename(rpa)
        update_status("msg_extracting", f"({current}/{total}): {base_name}")

        try:
            extract_rpa_file(rpa, output_dir)
        except Exception as e:
            print("[RPA ERROR]", e)

        update_progress(current, total)

    update_status("msg_scripts")
    decompile_rpyc(root_folder, status_callback)
    update_status("msg_success")


# =============================
# Diccionario de Lenguajes (i18n)
# =============================
LANGUAGES = {
    "es": {
        "title": "RPA TOOL por Vuistaz v1.2",
        "btn_select": "📁 Seleccionar carpeta del juego",
        "lbl_selected": "Carpeta seleccionada ✅",
        "lbl_not_selected": "No seleccionada",
        "btn_start": "🚀 Desencriptar",
        "msg_waiting": "Esperando...",
        "msg_warn": "Aviso",
        "msg_select_first": "Selecciona una carpeta primero",
        "msg_fatal_err": "❌ Error inesperado",
        "credits": "Código base adaptado de rpatool - por Shizmob",
        "msg_searching_rpyc": "🔎 Buscando archivos .rpyc...",
        "msg_no_rpyc": "ℹ️ No se encontraron archivos .rpyc",
        "msg_decompiling": "⚙️ Decompilando scripts...",
        "msg_decompiled_ok": "✅ Scripts decompilados correctamente",
        "msg_err_rpyc": "❌ Error al decompilar scripts",
        "msg_searching_rpa": "🔎 Buscando archivos RPA...",
        "msg_no_rpa": "❌ No se encontraron archivos RPA",
        "msg_overwrite_warn": "⚠️ Carpeta 'extracted' ya existe (se sobrescribirá)",
        "msg_extracting": "Extrayendo ",
        "msg_scripts": "Decompilando scripts...",
        "msg_success": "✅ Extracción y decompilación completadas"
    },
    "en": {
        "title": "RPA TOOL by Vuistaz v1.1",
        "btn_select": "📁 Select Game Directory",
        "lbl_selected": "Folder selected ✅",
        "lbl_not_selected": "Not selected",
        "btn_start": "🚀 Decrypt Archive",
        "msg_waiting": "Waiting...",
        "msg_warn": "Warning",
        "msg_select_first": "Please select a directory first",
        "msg_fatal_err": "❌ Unexpected error",
        "credits": "Base code adapted from rpatool - by Shizmob",
        "msg_searching_rpyc": "🔎 Searching for .rpyc files...",
        "msg_no_rpyc": "ℹ️ No .rpyc files found",
        "msg_decompiling": "⚙️ Decompiling scripts...",
        "msg_decompiled_ok": "✅ Scripts decompiled successfully",
        "msg_err_rpyc": "❌ Error decompiling scripts",
        "msg_searching_rpa": "🔎 Searching for RPA archives...",
        "msg_no_rpa": "❌ No RPA archives found",
        "msg_overwrite_warn": "⚠️ 'extracted' directory exists (it will be overwritten)",
        "msg_extracting": "Extracting ",
        "msg_scripts": "Decompiling scripts...",
        "msg_success": "✅ Extraction and decompiling finished"
    }
}

# =============================
# LÓGICA DE CONTROL E INTERFAZ
# =============================
ROOT_DIR = None
current_lang = "es"
last_status_key = "msg_waiting"
last_status_extra = ""


def change_language(event):
    global current_lang
    selected = lang_combo.get()
    current_lang = "es" if "Español" in selected else "en"
    update_ui_texts()


def update_ui_texts():
    lang = LANGUAGES[current_lang]
    app.title(lang["title"])
    title_lbl.config(text="RPA TOOL")
    select_btn.config(text=lang["btn_select"])
    
    if ROOT_DIR:
        root_label.config(text=lang["lbl_selected"])
    else:
        root_label.config(text=lang["lbl_not_selected"])
        
    start_btn.config(text=lang["btn_start"])
    credits_lbl.config(text=lang["credits"])
    
    translated_status = lang.get(last_status_key, last_status_key)
    status.config(text=f"{translated_status}{last_status_extra}")


def select_root():
    global ROOT_DIR
    path = filedialog.askdirectory(title="Seleccionar carpeta del juego")
    if not path:
        return

    ROOT_DIR = path
    root_label.config(text=LANGUAGES[current_lang]["lbl_selected"])


def run_extraction():
    try:
        def status_update_handler(msg_key, extra=""):
            global last_status_key, last_status_extra
            last_status_key = msg_key
            last_status_extra = extra
            translated = LANGUAGES[current_lang].get(msg_key, msg_key)
            safe_ui_update(lambda: status.config(text=f"{translated}{extra}"))

        process_game(
            ROOT_DIR,
            status_callback=status_update_handler,
            progress_callback=lambda i, t: safe_ui_update(
                lambda: (progress.config(maximum=t, value=i))
            ),
        )
    except Exception as e:
        print("[FATAL ERROR]", e)
        global last_status_key, last_status_extra
        last_status_key = "msg_fatal_err"
        last_status_extra = ""
        safe_ui_update(lambda: status.config(text=LANGUAGES[current_lang]["msg_fatal_err"]))


def run_extraction():
    try:
        def status_update_handler(msg_key, extra=""):
            global last_status_key, last_status_extra
            last_status_key = msg_key
            last_status_extra = extra
            translated = LANGUAGES[current_lang].get(msg_key, msg_key)
            safe_ui_update(lambda: status.config(text=f"{translated}{extra}"))

        process_game(
            ROOT_DIR,
            status_callback=status_update_handler,
            progress_callback=lambda i, t: safe_ui_update(
                lambda: (progress.config(maximum=t, value=i))
            ),
        )
    except Exception as e:
        print("[FATAL ERROR]", e)
        global last_status_key, last_status_extra
        last_status_key = "msg_fatal_err"
        last_status_extra = ""
        safe_ui_update(lambda: status.config(text=LANGUAGES[current_lang]["msg_fatal_err"]))


def start_extraction():
    lang = LANGUAGES[current_lang]
    if not ROOT_DIR:
        messagebox.showwarning(lang["msg_warn"], lang["msg_select_first"])
        return

    progress["value"] = 0
    progress["maximum"] = 1
    start_btn.config(state="disabled")

    def task():
        run_extraction()
        safe_ui_update(lambda: start_btn.config(state="normal"))

    thread = threading.Thread(target=task)
    thread.start()


def safe_ui_update(func):
    app.after(0, func)


# =============================
# Ventana Principal (Estilo Moderno)
# =============================
app = tk.Tk()
app.geometry("460x320")
app.resizable(False, False)
app.configure(bg="#1e1e2e")

style = ttk.Style()
style.theme_use("clam")
style.configure("TProgressbar", thickness=15, troughcolor="#313244", background="#a6e3a1")
style.configure("TCombobox", fieldbackground="#313244", background="#313244", foreground="#cdd6f4", arrowcolor="#cdd6f4")

# Top Frame para idioma
top_frame = tk.Frame(app, bg="#1e1e2e")
top_frame.pack(fill="x", padx=15, pady=(10, 0))

lang_combo = ttk.Combobox(top_frame, values=["🌐 Español (ES)", "🌐 English (EN)"], state="readonly", width=15)
lang_combo.current(0)
lang_combo.pack(side="right")
lang_combo.bind("<<ComboboxSelected>>", change_language)

# Componentes Visuales
title_lbl = tk.Label(app, text="RPA TOOL", font=("Segoe UI", 18, "bold"), bg="#1e1e2e", fg="#cdd6f4")
title_lbl.pack(pady=(5, 10))

select_btn = tk.Button(
    app,
    text="",
    command=select_root,
    font=("Segoe UI", 10, "bold"),
    bg="#313244",
    fg="#cdd6f4",
    activebackground="#45475a",
    activeforeground="#ffffff",
    bd=0,
    padx=8,
    pady=4
)
select_btn.pack(pady=5)

root_label = tk.Label(app, text="", font=("Segoe UI", 9, "italic"), bg="#1e1e2e", fg="#bac2de")
root_label.pack(pady=(0, 15))

start_btn = tk.Button(
    app,
    text="",
    command=start_extraction,
    font=("Segoe UI", 11, "bold"),
    bg="#11111b",
    fg="#a6e3a1",
    activebackground="#a6e3a1",
    activeforeground="#11111b",
    bd=1,
    relief="solid",
    highlightcolor="#a6e3a1",
    padx=8,
    pady=4
)
start_btn.pack(pady=10)

progress = ttk.Progressbar(app, length=340, style="TProgressbar")
progress.pack(pady=5)

status = tk.Label(app, text="", font=("Segoe UI", 10), bg="#1e1e2e", fg="#f5e0dc")
status.pack(pady=5)

credits_lbl = tk.Label(app, text="", font=("Segoe UI", 8), bg="#1e1e2e", fg="#585b70")
credits_lbl.pack(side="bottom", pady=10)

# Cargar textos iniciales y arrancar el loop principal (una sola vez)
update_ui_texts()
app.mainloop()





