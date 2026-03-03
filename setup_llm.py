"""Script de setup: descarga llama.cpp + modelo Qwen2.5-7B-Instruct Q4_K_M."""

import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent
LLAMA_DIR = BASE_DIR / "llama-server"
MODELS_DIR = BASE_DIR / "models"
MODEL_FILENAME = "qwen2.5-7b-instruct-q4_k_m.gguf"
MODEL_REPO = "Qwen/Qwen2.5-7B-Instruct-GGUF"


def download_llama_cpp():
    """Descargar llama.cpp server precompilado para Windows."""
    server_exe = LLAMA_DIR / "llama-server.exe"
    if server_exe.exists():
        print(f"[OK] llama-server.exe ya existe en {LLAMA_DIR}")
        return

    print("[1/2] Descargando llama.cpp server para Windows...")
    LLAMA_DIR.mkdir(parents=True, exist_ok=True)

    # Buscar el último release
    api_url = "https://api.github.com/repos/ggerganov/llama.cpp/releases/latest"
    resp = requests.get(api_url, timeout=30)
    resp.raise_for_status()
    release = resp.json()

    # Buscar asset CPU x64 para Windows
    asset_url = None
    asset_name = None
    for asset in release["assets"]:
        name = asset["name"].lower()
        if "win" in name and "x64" in name and "cpu" in name and name.endswith(".zip"):
            # Evitar variantes avx512 o vulkan
            if "vulkan" not in name and "kompute" not in name:
                asset_url = asset["browser_download_url"]
                asset_name = asset["name"]
                break

    if not asset_url:
        # Fallback: cualquier win-x64 zip
        for asset in release["assets"]:
            name = asset["name"].lower()
            if "win" in name and "x64" in name and name.endswith(".zip"):
                if "vulkan" not in name and "kompute" not in name and "cuda" not in name:
                    asset_url = asset["browser_download_url"]
                    asset_name = asset["name"]
                    break

    if not asset_url:
        print("ERROR: No se encontro release de llama.cpp para Windows x64 CPU.")
        print("Descargalo manualmente desde: https://github.com/ggerganov/llama.cpp/releases")
        sys.exit(1)

    print(f"  Release: {release['tag_name']}")
    print(f"  Asset: {asset_name}")
    print(f"  URL: {asset_url}")

    zip_path = LLAMA_DIR / asset_name
    # Descargar con progreso
    with requests.get(asset_url, stream=True, timeout=300) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f"\r  Descargando: {pct}% ({downloaded // 1024 // 1024}MB)", end="", flush=True)
    print()

    # Extraer
    print("  Extrayendo...")
    with zipfile.ZipFile(str(zip_path), "r") as zf:
        zf.extractall(str(LLAMA_DIR))
    zip_path.unlink()

    # Buscar llama-server.exe en subcarpetas
    found = list(LLAMA_DIR.rglob("llama-server.exe"))
    if found and found[0].parent != LLAMA_DIR:
        # Mover contenido de subcarpeta a LLAMA_DIR
        subdir = found[0].parent
        for item in subdir.iterdir():
            dest = LLAMA_DIR / item.name
            if not dest.exists():
                shutil.move(str(item), str(dest))

    if not server_exe.exists():
        # Buscar de nuevo
        found = list(LLAMA_DIR.rglob("llama-server.exe"))
        if found:
            print(f"  llama-server.exe encontrado en: {found[0]}")
        else:
            print("  WARN: No se encontro llama-server.exe. Revisá la carpeta manualmente.")
            return

    print(f"[OK] llama-server.exe listo en {LLAMA_DIR}")


def download_model():
    """Descargar modelo Qwen2.5-7B-Instruct Q4_K_M via huggingface-cli."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / MODEL_FILENAME

    if model_path.exists():
        size_gb = model_path.stat().st_size / (1024**3)
        print(f"[OK] Modelo ya existe: {model_path} ({size_gb:.1f} GB)")
        return

    print(f"[2/2] Descargando modelo {MODEL_FILENAME} (~4.4 GB)...")
    print(f"  Repo: {MODEL_REPO}")
    print(f"  Destino: {MODELS_DIR}")
    print("  Esto puede tardar varios minutos...\n")

    subprocess.run(
        [
            sys.executable, "-m", "huggingface_hub.commands.huggingface_cli",
            "download", MODEL_REPO, MODEL_FILENAME,
            "--local-dir", str(MODELS_DIR),
        ],
        check=True,
    )

    if model_path.exists():
        size_gb = model_path.stat().st_size / (1024**3)
        print(f"\n[OK] Modelo descargado: {model_path} ({size_gb:.1f} GB)")
    else:
        # huggingface-cli puede guardar con otro nombre
        gguf_files = list(MODELS_DIR.rglob("*.gguf"))
        if gguf_files:
            print(f"\n[OK] Modelo descargado en: {gguf_files[0]}")
        else:
            print("\nERROR: No se encontro el archivo .gguf despues de la descarga.")


def print_next_steps():
    server_exe = LLAMA_DIR / "llama-server.exe"
    # Buscar exe si no esta en raiz
    if not server_exe.exists():
        found = list(LLAMA_DIR.rglob("llama-server.exe"))
        if found:
            server_exe = found[0]

    model_path = MODELS_DIR / MODEL_FILENAME
    if not model_path.exists():
        gguf_files = list(MODELS_DIR.rglob("*.gguf"))
        if gguf_files:
            model_path = gguf_files[0]

    print("\n" + "=" * 60)
    print("SETUP COMPLETO - Proximos pasos:")
    print("=" * 60)
    print()
    print("1) Copiar tu PDF de prueba a:")
    print(f"   {BASE_DIR / 'test_input' / ''}")
    print()
    print("2) Abrir una terminal y levantar el servidor LLM:")
    print(f'   "{server_exe}" -m "{model_path}" --host 127.0.0.1 --port 8080 -c 4096 -t 6')
    print()
    print("   Esperar a que diga: 'llama server listening at http://127.0.0.1:8080'")
    print()
    print("3) En OTRA terminal, correr el procesador:")
    print(f"   cd \"{BASE_DIR}\"")
    print(f"   python process_pdfs.py --input test_input --output test_output")
    print()
    print("4) Ver resultados en test_output/")
    print("=" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("Setup: LLM local para procesamiento de oficios judiciales")
    print("=" * 60)
    print()
    download_llama_cpp()
    print()
    download_model()
    print_next_steps()
