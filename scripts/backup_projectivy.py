#!/usr/bin/env python3
"""Copia todos os APKs Projectivy; não desinstala nem altera o aparelho."""
import argparse
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import tvtool  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--adb")
    parser.add_argument("--user", type=int, default=0)
    args = parser.parse_args()
    tv = tvtool.TV(args)
    package = "com.spocky.projengmenu"
    state = tv.state(package)
    lines = tv.shell("pm", "path", package).splitlines()
    if not lines or any(not line.startswith("package:") for line in lines):
        raise ValueError("Não foi possível obter a lista completa de APKs")
    folder = ROOT / "reports" / (tvtool.timestamp() + "-projectivy-apks")
    folder.mkdir(parents=True, mode=0o700)
    record = {"identity": tv.identity, "user": tv.user, "package": package,
              "before_state": state, "backup_complete": False, "apks": []}
    path = folder / "backup.json"
    tvtool.save_json(path, record)
    for i, line in enumerate(lines):
        remote = line[len("package:"):].strip()
        dest = folder / (str(i) + "-" + Path(remote).name)
        tv.run("pull", remote, str(dest))
        data = dest.read_bytes()
        if not data.startswith(b"PK"):
            raise ValueError("APK inválido no backup; não remova o app")
        record["apks"].append({"file": dest.name, "bytes": len(data),
                               "sha256": hashlib.sha256(data).hexdigest()})
        tvtool.save_json(path, record)
    (folder / "SHA256SUMS").write_text("".join(f"{a['sha256']}  {a['file']}\n" for a in record["apks"]), encoding="utf-8")
    record["backup_complete"] = True
    tvtool.save_json(path, record)
    print(f"Backup completo: {len(record['apks'])} APK(s) em {folder}")
    print("O app não foi removido. O backup não inclui seus dados privados.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Backup incompleto: {exc}. Não avance para a remoção.", file=sys.stderr)
        sys.exit(1)
