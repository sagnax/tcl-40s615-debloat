#!/usr/bin/env python3
"""Inventário e desativação reversível por ADB, sem dependências Python externas."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PACKAGE = re.compile(r"[a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z0-9_]+)+\Z")
STATES = {0: "default-state", 1: "enable", 2: "disable", 3: "disable-user", 4: "disable-until-used"}
HOME_ORIGINAL = "com.google.android.tvlauncher/.MainActivity"
HOME_TARGET = "me.efesser.flauncher/.MainActivity"
ALEXA_OPS = ("RUN_IN_BACKGROUND", "RUN_ANY_IN_BACKGROUND")
# Proteção conservadora adicional à revisão humana do manifesto.
PROTECTED = re.compile(
    r"(?:^android$|^com\.android\.|^com\.google\.android\.(?:gms|gsf|webview|"
    r"packageinstaller|permissioncontroller|tv\.remote|tv\.frameworkpackagestubs)(?:\.|$)|"
    r"^com\.tcl\.(?:tv|system\.server|partnercustomizer|initsetup|autopair|t_solo|suspension)$|"
    r"cast|chromecast|mediashell|remote|bluetooth|inputmethod|settings|systemui|provider|"
    r"permission|packageinstaller|network|wifi|drm|widevine|hdmi|cec|audio|"
    r"updat|firmware|launcher|livetv|tvinput)", re.I)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")


def identity_matches(saved, current):
    """Mesmo firmware e aparelho; aceita IP novo quando há serial físico válido."""
    if not saved.get("fingerprint") or saved.get("fingerprint") != current.get("fingerprint"):
        return False
    old = saved.get("hardware_serial", "").strip()
    new = current.get("hardware_serial", "").strip()
    valid = lambda value: bool(value) and value.lower() != "unknown" and set(value) != {"0"}
    if valid(old) and valid(new):
        return old == new
    return bool(saved.get("serial")) and saved.get("serial") == current.get("serial")


def require_identity(tv, data):
    if not identity_matches(data.get("identity", {}), tv.identity) or data.get("user") != tv.user:
        raise ValueError("Registro pertence a outro aparelho, firmware ou usuário")


def resolved_home(tv):
    lines = tv.shell("cmd", "package", "resolve-activity", "--brief", "--user", str(tv.user),
                     "-a", "android.intent.action.MAIN", "-c", "android.intent.category.HOME").strip().splitlines()
    if not lines or "/" not in lines[-1]:
        raise ValueError("Não foi possível resolver HOME")
    return lines[-1]


def enabled_state(dump, user):
    line = re.search(rf"^\s*User {user}:\s*(.*)$", dump, re.M)
    if not line or not re.search(r"\binstalled=true\b", line[1]):
        raise ValueError(f"Pacote não instalado para usuário {user}")
    match = re.search(r"\benabled=(\d+)\b", line[1])
    if not match or int(match[1]) not in STATES:
        raise ValueError("Estado enabled desconhecido; nenhuma alteração permitida")
    return int(match[1])


def manifest_packages(data):
    entries = data["packages"]
    if not isinstance(entries, list):
        raise ValueError("packages deve ser uma lista")
    result = []
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError("Cada entrada precisa de package e reason")
        pkg = item.get("package", "")
        if not isinstance(pkg, str) or not PACKAGE.fullmatch(pkg):
            raise ValueError(f"Nome de pacote inválido: {pkg!r}")
        if PROTECTED.search(pkg):
            raise ValueError(f"Pacote protegido: {pkg}")
        if not isinstance(item.get("reason"), str) or not item["reason"].strip():
            raise ValueError(f"Falta justificativa para {pkg}")
        if pkg in [x["package"] for x in result]:
            raise ValueError(f"Pacote repetido: {pkg}")
        result.append(item)
    return result


class TV:
    def __init__(self, args):
        local = ROOT / ".tools/platform-tools" / ("adb.exe" if os.name == "nt" else "adb")
        self.adb = args.adb or (str(local) if local.exists() else shutil.which("adb"))
        if not self.adb:
            raise ValueError("ADB ausente; consulte README.md")
        if not args.serial:
            raise ValueError("Informe --serial; seleção automática de dispositivo é proibida")
        self.serial = args.serial
        self.user = args.user
        self.run("get-state")
        if self.shell("am", "get-current-user").strip() != str(self.user):
            raise ValueError("Usuário ativo diferente de --user; confirme antes de continuar")
        self.identity = {
            "serial": self.serial,
            "hardware_serial": self.shell("getprop", "ro.serialno").strip(),
            "fingerprint": self.shell("getprop", "ro.build.fingerprint").strip(),
        }
        if not self.identity["fingerprint"]:
            raise ValueError("Não foi possível identificar o firmware")

    def run(self, *args, timeout=45):
        proc = subprocess.run([self.adb, "-s", self.serial, *args], capture_output=True,
                              text=True, timeout=timeout)
        if proc.returncode:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
        return proc.stdout

    def shell(self, *args):
        return self.run("shell", shlex.join(args))

    def state(self, package):
        if not PACKAGE.fullmatch(package):
            raise ValueError("Pacote inválido")
        return enabled_state(self.shell("dumpsys", "package", package), self.user)

    def set_state(self, package, state):
        self.shell("pm", STATES[state], "--user", str(self.user), package)
        if self.state(package) != state:
            raise RuntimeError(f"Falha ao verificar estado de {package}")


def inventory(tv, args):
    folder = ROOT / "reports" / timestamp()
    folder.mkdir(parents=True, mode=0o700)
    commands = {
        "properties": ("getprop",),
        "packages": ("pm", "list", "packages", "-f", "-U", "--user", str(tv.user)),
        "disabled": ("pm", "list", "packages", "-d", "--user", str(tv.user)),
        "package_details": ("dumpsys", "package"),
        "memory": ("dumpsys", "meminfo"),
        "cpu": ("dumpsys", "cpuinfo"),
        "storage": ("df", "-h", "/data"),
        "processes": ("ps", "-A"),
        "home": ("cmd", "package", "resolve-activity", "--brief", "--user", str(tv.user),
                 "-a", "android.intent.action.MAIN", "-c", "android.intent.category.HOME"),
    }
    result = {"identity": tv.identity, "user": tv.user, "errors": {}}
    for name, cmd in commands.items():
        try:
            (folder / (name + ".txt")).write_text(tv.shell(*cmd))
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            result["errors"][name] = str(exc)
    save_json(folder / "inventory.json", result)
    print(folder)


def apply(tv, args):
    entries = manifest_packages(read_json(args.manifest))
    # Preflight completo antes da primeira alteração.
    changes = [{**entry, "before": tv.state(entry["package"]), "status": "planned"}
               for entry in entries]
    journal = {"identity": tv.identity, "user": tv.user, "changes": changes}
    print(json.dumps(journal, indent=2, ensure_ascii=False))
    if not args.execute or not changes:
        print("Nenhuma alteração aplicada.")
        return
    path = ROOT / "reports" / (timestamp() + "-journal.json")
    save_json(path, journal)
    print(f"Registro para restauração: {path}", flush=True)
    for change in changes:
        if tv.state(change["package"]) != change["before"]:
            raise RuntimeError("Estado mudou desde o preflight; execução interrompida")
        change["status"] = "pending"
        save_json(path, journal)
        try:
            tv.set_state(change["package"], 3)
            change["status"] = "applied"
        except Exception as exc:
            change["error"] = str(exc)
            save_json(path, journal)
            raise
        save_json(path, journal)


def restore(tv, args):
    data = read_json(args.journal)
    require_identity(tv, data)
    changes = [c for c in reversed(data["changes"]) if c["status"] in ("pending", "applied")]
    for c in changes:
        if not PACKAGE.fullmatch(c["package"]) or c["before"] not in STATES:
            raise ValueError("Registro inválido")
        state = tv.state(c["package"])
        if state not in (3, c["before"]):
            raise ValueError(f"Estado alterado externamente: {c['package']}")
    for c in changes:
        print(f"Restaurar {c['package']} → {STATES[c['before']]}")
        if args.execute:
            tv.set_state(c["package"], c["before"])
            c["status"] = "restored"
            save_json(args.journal, data)
    if not args.execute:
        print("Simulação; use --execute para restaurar.")


def home(tv, args):
    """Troca específica Google TV Launcher -> FLauncher, com registro anterior."""
    before = resolved_home(tv)
    if before == HOME_TARGET:
        print("FLauncher já é HOME. Nenhuma alteração aplicada.")
        return
    if before != HOME_ORIGINAL:
        raise ValueError("HOME diferente do caso testado; consulte docs/03-launcher.md")
    if tv.state("me.efesser.flauncher") not in (0, 1):
        raise ValueError("Instale e teste FLauncher antes da troca")
    before_state = tv.state("com.google.android.tvlauncher")
    if before_state not in (0, 1):
        raise ValueError("Estado inesperado do launcher original")
    services = tv.shell("settings", "get", "secure", "enabled_accessibility_services").strip()
    data = {"identity": tv.identity, "user": tv.user, "before_home": before,
            "after_home": HOME_TARGET, "before_google_state": before_state,
            "before_accessibility": services, "status": "prepared"}
    print("Plano: selecionar FLauncher, desativar Google Launcher e retirar somente a interceptação Projectivy.")
    if not args.execute:
        print("Simulação. Teste o controle no FLauncher antes de executar.")
        return
    path = ROOT / "reports" / (timestamp() + "-home.json")
    save_json(path, data)
    print(f"Registro para restauração: {path}", flush=True)
    try:
        output = tv.shell("am", "start", "-W", "-n", HOME_TARGET)
        if not re.search(r"^Status:\s*ok\s*$", output, re.M):
            raise RuntimeError("FLauncher não abriu: " + output.strip())
        remaining = ":".join(x for x in services.split(":") if not x.startswith("com.spocky.projengmenu/"))
        if remaining != services:
            tv.shell("settings", "put", "secure", "enabled_accessibility_services", remaining)
        data["status"] = "switch-pending"
        save_json(path, data)
        tv.set_state("com.google.android.tvlauncher", 3)
        tv.shell("cmd", "package", "set-home-activity", "--user", str(tv.user), HOME_TARGET)
        tv.shell("input", "keyevent", "KEYCODE_HOME")
        if resolved_home(tv) != HOME_TARGET:
            raise RuntimeError("HOME não passou a ser FLauncher")
        data["status"] = "applied"
        save_json(path, data)
    except Exception as exc:
        data["error"] = str(exc)
        try:
            tv.set_state("com.google.android.tvlauncher", before_state)
            tv.shell("cmd", "package", "set-home-activity", "--user", str(tv.user), before)
            if services == "null":
                tv.shell("settings", "delete", "secure", "enabled_accessibility_services")
            else:
                tv.shell("settings", "put", "secure", "enabled_accessibility_services", services)
            tv.shell("input", "keyevent", "KEYCODE_HOME")
            data["status"] = "rolled-back"
        except Exception as recovery:
            data["recovery_error"] = str(recovery)
            print(f"Reversão incompleta: reconecte ADB e use restore-home {path}", file=sys.stderr)
        save_json(path, data)
        raise


def restore_home(tv, args):
    """Reverte a troca de HOME específica registrada nesta TV."""
    data = read_json(args.journal)
    require_identity(tv, data)
    before = data["before_home"]
    after = data["after_home"]
    if before != "com.google.android.tvlauncher/.MainActivity" or after != "me.efesser.flauncher/.MainActivity":
        raise ValueError("Registro não corresponde à troca de launcher implementada")
    current = tv.shell("cmd", "package", "resolve-activity", "--brief", "--user", str(tv.user),
                       "-a", "android.intent.action.MAIN", "-c", "android.intent.category.HOME").strip().splitlines()[-1]
    if current not in (before, after):
        raise ValueError("Outro launcher foi selecionado depois; revise antes de restaurar")
    old_services = data["before_accessibility"]
    reduced = ":".join(x for x in old_services.split(":") if not x.startswith("com.spocky.projengmenu/"))
    current_services = tv.shell("settings", "get", "secure", "enabled_accessibility_services").strip()
    if current_services not in (old_services, reduced, "null" if not reduced else reduced):
        raise ValueError("Acessibilidade alterada posteriormente; revise antes de restaurar")
    original_state = data["before_google_state"]
    if original_state not in (0, 1) or tv.state("com.google.android.tvlauncher") not in (3, original_state):
        raise ValueError("Estado inesperado do launcher original")
    print(f"Restaurar HOME {before}, estado {STATES[original_state]} e acessibilidade anterior.")
    if not args.execute:
        print("Simulação; use --execute para restaurar.")
        return
    # Primeiro disponibilizar o launcher original; só então selecioná-lo.
    tv.set_state("com.google.android.tvlauncher", original_state)
    tv.shell("cmd", "package", "set-home-activity", "--user", str(tv.user), before)
    if old_services == "null":
        tv.shell("settings", "delete", "secure", "enabled_accessibility_services")
    else:
        tv.shell("settings", "put", "secure", "enabled_accessibility_services", old_services)
    tv.shell("input", "keyevent", "KEYCODE_HOME")
    data["status"] = "restored"
    save_json(args.journal, data)


def restore_app(tv, args):
    """Reinstala para o usuário um APK de sistema preservado com uninstall -k."""
    data = read_json(args.journal)
    require_identity(tv, data)
    package = data["package"]
    if not PACKAGE.fullmatch(package) or data["before_state"] not in STATES:
        raise ValueError("Registro inválido")
    if data["operation"] != f"pm uninstall -k --user {tv.user}":
        raise ValueError("Operação de origem desconhecida")
    dump = tv.shell("dumpsys", "package", package)
    line = re.search(rf"^\s*User {tv.user}:.*$", dump, re.M)
    if not line or not re.search(r"\binstalled=(true|false)\b", line[0]):
        raise ValueError("APK preservado não encontrado para este usuário")
    print(f"Reinstalar {package} para usuário {tv.user} e restaurar estado {data['before_state']}.")
    if not args.execute:
        print("Simulação; use --execute para restaurar.")
        return
    tv.shell("cmd", "package", "install-existing", "--user", str(tv.user), package)
    tv.set_state(package, data["before_state"])
    data["status"] = "restored"
    save_json(args.journal, data)


def appop_mode(text, operation):
    if "Uid mode:" in text:
        raise ValueError("Modo AppOps definido por UID; não alterar automaticamente")
    match = re.search(rf"(?m)^\s*{re.escape(operation)}:\s*(allow|ignore|deny|default|foreground)\b", text)
    if not match:
        match = re.search(r"Default mode:\s*(allow|ignore|deny|default|foreground)\b", text)
    if not match:
        raise ValueError("Modo AppOps desconhecido; nenhuma política presumida")
    return match[1]


def op_get(tv, operation):
    return appop_mode(tv.shell("cmd", "appops", "get", "--user", str(tv.user), "com.tcl.smartalexa", operation), operation)


def op_set(tv, operation, mode):
    tv.shell("cmd", "appops", "set", "--user", str(tv.user), "com.tcl.smartalexa", operation, mode)
    if op_get(tv, operation) != mode:
        raise RuntimeError("AppOps não confirmou " + operation)


def alexa(tv, args):
    tv.state("com.tcl.smartalexa")
    changes = [{"operation": op, "before": op_get(tv, op), "after": "ignore", "status": "planned"}
               for op in ALEXA_OPS]
    print(json.dumps(changes, indent=2))
    if not args.execute:
        print("Simulação; o microfone não é alterado por este comando.")
        return
    path = ROOT / "reports" / (timestamp() + "-alexa.json")
    data = {"identity": tv.identity, "user": tv.user, "package": "com.tcl.smartalexa", "changes": changes}
    save_json(path, data)
    print(f"Registro para restauração: {path}", flush=True)
    for change in changes:
        if op_get(tv, change["operation"]) != change["before"]:
            raise RuntimeError("AppOps mudou desde a simulação; execução interrompida")
        change["status"] = "pending"
        save_json(path, data)
        op_set(tv, change["operation"], "ignore")
        change["status"] = "applied"
        save_json(path, data)
    tv.shell("am", "force-stop", "com.tcl.smartalexa")


def restore_alexa(tv, args):
    data = read_json(args.journal)
    require_identity(tv, data)
    if data.get("package") != "com.tcl.smartalexa":
        raise ValueError("Registro AppOps não pertence ao Alexa")
    changes = [c for c in reversed(data["changes"]) if c["status"] in ("pending", "applied")]
    for change in changes:
        if change["operation"] not in ALEXA_OPS or change["before"] not in ("allow", "ignore", "deny", "default", "foreground"):
            raise ValueError("Registro AppOps inválido")
        if op_get(tv, change["operation"]) not in (change["before"], "ignore"):
            raise ValueError("Política alterada posteriormente; revise antes de restaurar")
    for change in changes:
        print(f"Restaurar {change['operation']} → {change['before']}")
        if args.execute:
            op_set(tv, change["operation"], change["before"])
            change["status"] = "restored"
            save_json(args.journal, data)
    if not args.execute:
        print("Simulação; use --execute para restaurar.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb")
    parser.add_argument("--serial", required=True)
    parser.add_argument("--user", type=int, default=0)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inventory")
    p = sub.add_parser("home")
    p.add_argument("--execute", action="store_true")
    p = sub.add_parser("alexa")
    p.add_argument("--execute", action="store_true")
    p = sub.add_parser("restore-alexa")
    p.add_argument("journal")
    p.add_argument("--execute", action="store_true")
    p = sub.add_parser("apply")
    p.add_argument("manifest")
    p.add_argument("--execute", action="store_true")
    p = sub.add_parser("restore")
    p.add_argument("journal")
    p.add_argument("--execute", action="store_true")
    p = sub.add_parser("restore-home")
    p.add_argument("journal")
    p.add_argument("--execute", action="store_true")
    p = sub.add_parser("restore-app")
    p.add_argument("journal")
    p.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        tv = TV(args)
        {"inventory": inventory, "apply": apply, "restore": restore,
         "home": home, "alexa": alexa, "restore-alexa": restore_alexa,
         "restore-home": restore_home, "restore-app": restore_app}[args.command](tv, args)
    except (ValueError, KeyError, OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
