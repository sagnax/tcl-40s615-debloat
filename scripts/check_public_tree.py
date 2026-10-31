#!/usr/bin/env python3
"""Revisão heurística de conteúdo público; não imprime o valor suspeito."""
import argparse
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = {".tools", "reports", "private", "backups", ".venv", ".git", "__pycache__", ".pytest_cache", "build"}
FORBIDDEN_SUFFIXES = {".apk", ".apks", ".img", ".bin", ".pkg", ".zip", ".log", ".pem", ".key", ".jks", ".keystore", ".pk8", ".dex", ".jar"}
PATTERNS = {
    "token GitHub": r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b",
    "chave privada": r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----",
    "IPv4 de rede privada": r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b",
    "MAC": r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b",
    "IPv6": r"\b(?:[0-9a-fA-F]{1,4}:){3,}[0-9a-fA-F:]+\b",
    "ESN Netflix": r"\bNFANDROID[0-9A-Z-]+\b",
    "e-mail": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "caminho pessoal": r"(?:/home/|/Users/|[A-Za-z]:\\Users\\)[A-Za-z0-9_.-]+[/\\]",
}


def findings(name, data):
    path = Path(name)
    result = []
    if any(p in PRIVATE for p in path.parts) or path.name == ".env" or path.name.startswith(".env."):
        result.append("caminho privado")
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        result.append("artefato privado/binário")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return result + ["arquivo não textual"]
    if b"\0" in data:
        result.append("conteúdo binário")
    for label, pattern in PATTERNS.items():
        if re.search(pattern, text):
            result.append(label)
    return result


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True).stdout


def audit(root, staged=False):
    errors = []
    count = 0
    if staged:
        names = git(root, "ls-files", "--cached", "-z").decode("utf-8").split("\0")
        entries = [(n, git(root, "show", ":" + n)) for n in names if n]
    else:
        entries = []
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if any(part in PRIVATE for part in relative.parts):
                continue
            if path.is_symlink():
                errors.append((str(relative), ["link simbólico: revisar destino manualmente"]))
            elif path.is_file():
                entries.append((str(relative), path.read_bytes()))
    for name, data in entries:
        count += 1
        issues = findings(name, data)
        if issues:
            errors.append((name, issues))
    return count, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--staged", action="store_true", help="Ler o conteúdo do índice Git")
    args = parser.parse_args()
    try:
        count, errors = audit(args.root.resolve(), args.staged)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Não foi possível concluir a revisão: {type(exc).__name__}", file=sys.stderr)
        return 2
    for name, issues in errors:
        print(f"REVISAR {name}: {', '.join(issues)}")
    if errors:
        print("Nenhum valor suspeito foi impresso. Revise antes de publicar.")
        return 1
    print(f"{count} arquivos verificados; nenhum padrão privado conhecido encontrado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
