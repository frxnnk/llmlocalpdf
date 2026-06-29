"""Script de setup: descarga llama.cpp + modelo local allowlisted."""

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import requests

from model_registry import (
    build_manifest,
    get_model_spec,
    validate_manifest,
    write_manifest,
)

BASE_DIR = Path(__file__).parent
LLAMA_DIR = BASE_DIR / "llama-server"
MODELS_DIR = BASE_DIR / "models"
MANIFEST_PATH = MODELS_DIR / "model-manifest.json"

# --- Pinned llama.cpp release ---
LLAMA_RELEASE_TAG = "b8192"
LLAMA_ASSET_NAME = f"llama-{LLAMA_RELEASE_TAG}-bin-win-cpu-x64.zip"
LLAMA_ASSET_URL = f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_RELEASE_TAG}/{LLAMA_ASSET_NAME}"
LLAMA_ASSET_SHA256 = "8a206290df3466388c42510b975660dd709f0084ea0809abc36e4f4fc3602ee7"


def verify_sha256(file_path: Path, expected_hash: str) -> bool:
    """Verificar SHA256 de un archivo descargado."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    actual = sha256.hexdigest()
    if actual != expected_hash:
        print(f"  ERROR: Hash SHA256 no coincide!")
        print(f"    Esperado: {expected_hash}")
        print(f"    Obtenido: {actual}")
        return False
    return True


def download_llama_cpp():
    """Descargar llama.cpp server precompilado para Windows (version pineada + SHA256)."""
    server_exe = LLAMA_DIR / "llama-server.exe"
    if server_exe.exists():
        print(f"[OK] llama-server.exe ya existe en {LLAMA_DIR}")
        return

    print(f"[1/2] Descargando llama.cpp server {LLAMA_RELEASE_TAG} para Windows...")
    LLAMA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"  Release: {LLAMA_RELEASE_TAG}")
    print(f"  Asset: {LLAMA_ASSET_NAME}")
    print(f"  URL: {LLAMA_ASSET_URL}")

    zip_path = LLAMA_DIR / LLAMA_ASSET_NAME
    # Descargar con progreso
    with requests.get(LLAMA_ASSET_URL, stream=True, timeout=300) as r:
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

    # Verificar integridad
    print("  Verificando SHA256...")
    if not verify_sha256(zip_path, LLAMA_ASSET_SHA256):
        zip_path.unlink()
        print("ERROR: El archivo descargado esta corrupto o fue alterado.")
        print("Esto puede indicar un problema de red o un ataque de supply chain.")
        sys.exit(1)
    print("  SHA256 OK")

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


def model_download_accepted(explicit_accept: bool) -> bool:
    """Return whether this run may download a multi-GB model artifact."""
    return explicit_accept or os.environ.get("LLMLOCALPDF_ACCEPT_MODEL_DOWNLOAD") == "1"


def verify_or_manifest_existing_model(model_path: Path, model_spec: dict) -> None:
    """Verify an existing model or create a first local manifest."""
    if MANIFEST_PATH.exists():
        errors = validate_manifest(model_path, MANIFEST_PATH)
        if errors:
            print("ERROR: La verificacion del modelo fallo:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        print(f"[OK] Modelo verificado contra manifest: {model_path}")
        return

    manifest = build_manifest(model_path, model_spec)
    write_manifest(manifest, MANIFEST_PATH)
    print(f"[WARN] Modelo existente sin manifest previo: {model_path}")
    print(f"[WARN] Se creo manifest local en: {MANIFEST_PATH}")
    print("[WARN] Este artifact queda como candidate_unreviewed hasta aprobacion del banco.")


def download_model(accept_download: bool = False):
    """Descargar modelo allowlisted via huggingface-cli."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_spec = get_model_spec()
    model_filename = model_spec["filename"]
    model_repo = model_spec["repo"]
    model_path = MODELS_DIR / model_filename

    if model_path.exists():
        size_gb = model_path.stat().st_size / (1024**3)
        print(f"[OK] Modelo ya existe: {model_path} ({size_gb:.1f} GB)")
        verify_or_manifest_existing_model(model_path, model_spec)
        return

    if not model_download_accepted(accept_download):
        print("ERROR: El modelo no esta descargado y la descarga no fue aceptada explicitamente.")
        print("Para desarrollo, ejecutar con --accept-model-download o definir:")
        print("  LLMLOCALPDF_ACCEPT_MODEL_DOWNLOAD=1")
        print("Para staging bancario, usar paquete offline + manifest SHA-256 aprobado.")
        sys.exit(1)

    print(f"[2/2] Descargando modelo {model_filename} (~4.4 GB)...")
    print(f"  Repo: {model_repo}")
    print(f"  Destino: {MODELS_DIR}")
    print(f"  Licencia declarada: {model_spec['license']}")
    print(f"  Fuente: {model_spec['source_url']}")
    print("  Esto puede tardar varios minutos...\n")

    subprocess.run(
        [
            sys.executable, "-m", "huggingface_hub.commands.huggingface_cli",
            "download", model_repo, model_filename,
            "--local-dir", str(MODELS_DIR),
        ],
        check=True,
    )

    if model_path.exists():
        size_gb = model_path.stat().st_size / (1024**3)
        print(f"\n[OK] Modelo descargado: {model_path} ({size_gb:.1f} GB)")
        manifest = build_manifest(model_path, model_spec)
        write_manifest(manifest, MANIFEST_PATH)
        print(f"[OK] Manifest escrito: {MANIFEST_PATH}")
    else:
        print("\nERROR: No se encontro el archivo .gguf esperado despues de la descarga.")
        print(f"Esperado: {model_path}")
        sys.exit(1)


def print_next_steps():
    server_exe = LLAMA_DIR / "llama-server.exe"
    # Buscar exe si no esta en raiz
    if not server_exe.exists():
        found = list(LLAMA_DIR.rglob("llama-server.exe"))
        if found:
            server_exe = found[0]

    model_spec = get_model_spec()
    model_path = MODELS_DIR / model_spec["filename"]
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
    parser = argparse.ArgumentParser(
        description="Setup local LLM runtime for judicial-office processing"
    )
    parser.add_argument(
        "--accept-model-download",
        action="store_true",
        help="Allow development download of the multi-GB model from Hugging Face.",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Setup: LLM local para procesamiento de oficios judiciales")
    print("=" * 60)
    print()
    download_llama_cpp()
    print()
    download_model(accept_download=args.accept_model_download)
    print_next_steps()
