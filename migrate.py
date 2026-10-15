#!/usr/bin/env python3
"""Spouštění imapsync přes Docker Compose podle JSON konfigurace."""
import argparse
from contextlib import contextmanager
import fcntl
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def read_accounts(path):
    with path.open(encoding="utf-8") as handle:
        accounts = json.load(handle)
    if not isinstance(accounts, list):
        raise ValueError("Konfigurace musí být JSON seznam schránek.")
    identifiers = set()
    for account in accounts:
        if not isinstance(account, dict):
            raise ValueError("Každá schránka musí být JSON objekt.")
        identifier = account.get("id", "")
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", identifier):
            raise ValueError("id musí mít 1–64 znaků: písmena, číslice, _ nebo -.")
        if identifier in identifiers:
            raise ValueError(f"Duplicitní id: {identifier}")
        identifiers.add(identifier)
        if set(account) - {"id", "enabled", "source", "target", "automap", "addheader", "folder_map", "separator2"}:
            raise ValueError(f"{identifier}: neznámé položky konfigurace.")
        for key in ("enabled", "automap", "addheader"):
            if key in account and type(account[key]) is not bool:
                raise ValueError(f"{identifier}: {key} musí být true nebo false.")
        mapping = account.get("folder_map", {})
        if not isinstance(mapping, dict):
            raise ValueError(f"{identifier}: folder_map musí být objekt zdroj: cíl.")
        for source, target in mapping.items():
            if any(not isinstance(value, str) or not value.strip() or "=" in value
                   or any(ord(c) < 32 for c in value) for value in (source, target)):
                raise ValueError(f"{identifier}: neplatný název složky ve folder_map.")
        separator = account.get("separator2")
        if separator is not None and (not isinstance(separator, str) or len(separator) != 1
                                      or ord(separator) < 32):
            raise ValueError(f"{identifier}: separator2 musí být jeden znak.")
        for side in ("source", "target"):
            endpoint = account.get(side)
            if not isinstance(endpoint, dict):
                raise ValueError(f"{identifier}: chybí objekt {side}.")
            if set(endpoint) - {"host", "port", "user", "password_file"}:
                raise ValueError(f"{identifier}/{side}: neznámé položky; heslo patří do souboru.")
            for key in ("host", "user", "password_file"):
                value = endpoint.get(key)
                if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 for c in value):
                    raise ValueError(f"{identifier}/{side}: neplatné {key}.")
            port = endpoint.get("port", 993)
            if type(port) is not int or not 1 <= port <= 65535:
                raise ValueError(f"{identifier}/{side}: neplatný port.")
            name = endpoint["password_file"]
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
                raise ValueError(f"{identifier}/{side}: password_file musí být samotný název souboru.")
    return accounts


def validate_passwords(account):
    for side in ("source", "target"):
        endpoint = account[side]
        host = endpoint["host"].lower().rstrip(".")
        if host == "example.com" or host.endswith(".example.com"):
            raise ValueError(f"{account['id']}/{side}: nahraďte ukázkový server skutečným.")
        path = ROOT / "passwords" / endpoint["password_file"]
        if path.is_symlink() or not path.is_file() or not path.stat().st_size:
            raise ValueError(f"Chybí neprázdný soubor s heslem: {path}")
        if path.stat().st_mode & 0o077:
            raise ValueError(f"Omezte přístup k heslu příkazem chmod 600 {shlex.quote(str(path))}")


def mapping_options(account):
    options = ["--automap" if account.get("automap", False) else "--noautomap",
               "--addheader" if account.get("addheader", False) else "--noaddheader",
               "--nosyncduplicates"]
    if account.get("separator2") is not None:
        options.extend(["--sep2", account["separator2"]])
    for source, target in account.get("folder_map", {}).items():
        options.extend(["--f1f2", f"{source}={target}"])
    return options


def build_command(account, mode):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    filename = f"{account['id']}-{mode}-{stamp}.log"
    command = ["docker", "compose", "--project-directory", str(ROOT),
               "-f", str(ROOT / "docker-compose.yml"), "run", "--rm", "-T",
               "imapsync", "imapsync"]
    for index, side in enumerate(("source", "target"), 1):
        endpoint = account[side]
        command.extend([f"--host{index}", endpoint["host"],
                        f"--port{index}", str(endpoint.get("port", 993)),
                        f"--user{index}", endpoint["user"],
                        f"--passfile{index}", f"/data/passwords/{endpoint['password_file']}",
                        f"--ssl{index}", f"--sslargs{index}", "SSL_verify_mode=1"])
    command.extend(["--log", "--logdir", "/logs", "--logfile", filename])
    command.extend(mapping_options(account))
    if mode == "check":
        command.append("--justlogin")
    elif mode == "sizes":
        command.append("--justfoldersizes")
    elif mode in ("folders", "folders-dry-run"):
        command.append("--justfolders")
    if mode in ("plan", "dry-run", "folders-dry-run"):
        command.append("--dry")
    return command


MODES = {
    "check": "Kontrola přihlášení k oběma schránkám",
    "sizes": "Seznam složek, počty zpráv a velikosti",
    "dry-run": "Zkušební průchod bez přenosu zpráv",
    "folders-dry-run": "Náhled vytvoření a mapování složek bez změn",
    "folders": "Skutečně vytvořit složky, nepřenášet zprávy",
    "sync": "Skutečná migrace zpráv",
    "plan": "Pouze zobrazit příkaz, bez připojení",
}
WRITING_MODES = {"folders", "sync"}


class Cancelled(Exception):
    pass


def ask(prompt, default=""):
    try:
        answer = input(prompt).strip()
    except EOFError:
        raise Cancelled() from None
    if answer.lower() in {"q", "quit", "konec"}:
        raise Cancelled()
    return answer or default


def parse_selection(answer, accounts):
    if answer.lower() in {"vse", "vše", "all", "*"}:
        return list(accounts)
    tokens = answer.replace(",", " ").split()
    if not tokens or any(not token.isdigit() for token in tokens):
        raise ValueError("Zadejte čísla oddělená čárkou/mezerou nebo vše.")
    indices = {int(token) for token in tokens}
    if any(index < 1 or index > len(accounts) for index in indices):
        raise ValueError("Číslo účtu je mimo zobrazený seznam.")
    return [account for index, account in enumerate(accounts, 1) if index in indices]


def use_arrow_menu():
    return sys.stdin.isatty() and sys.stdout.isatty() and os.environ.get("TERM", "dumb") != "dumb"


def arrow_choice(title, items, **options):
    from terminal_menu import MenuCancelled, choose
    try:
        return choose(title, items, **options)
    except MenuCancelled:
        raise Cancelled() from None


def select_interactively(accounts):
    if not accounts:
        raise ValueError("accounts.json neobsahuje žádné účty.")
    if use_arrow_menu():
        labels = [f"{a['id']}: {a['source']['user']} ({a['source']['host']}) → "
                  f"{a['target']['user']} ({a['target']['host']})" for a in accounts]
        indices = arrow_choice("Výběr účtů — pouze pro tento běh, JSON se nemění",
                               labels, multiple=True, selected={0} if len(accounts) == 1 else set())
        return [accounts[index] for index in indices]
    print("\nÚčty z konfigurace (q = konec):")
    for index, account in enumerate(accounts, 1):
        source, target = account["source"], account["target"]
        status = "" if account.get("enabled", False) else " [mimo automatické --all]"
        print(f"  {index}. {account['id']}{status}")
        print(f"     {source['user']} @ {source['host']} → {target['user']} @ {target['host']}")
    print("Ruční výběr platí jen pro tento běh; JSON se nemění.")
    default = "1" if len(accounts) == 1 else ""
    prompt = "Vyberte účty: číslo, více čísel nebo vše" + (" [1]" if default else "") + ": "
    while True:
        try:
            return parse_selection(ask(prompt, default), accounts)
        except ValueError as error:
            print(error)


def select_mode():
    if use_arrow_menu():
        modes = list(MODES)
        index = arrow_choice("Co chcete spustit?", list(MODES.values()),
                             default=modes.index("dry-run"))
        return modes[index]
    print("\nCo chcete spustit?")
    modes = list(MODES)
    for index, mode in enumerate(modes, 1):
        print(f"  {index}. {MODES[mode]}" + (" [výchozí]" if mode == "dry-run" else ""))
    while True:
        value = ask("Vyberte režim [3]: ", "3")
        if value.isdigit() and 1 <= int(value) <= len(modes):
            return modes[int(value) - 1]
        print("Zadejte číslo režimu nebo q pro konec.")


def review_selection(selected, mode):
    print(f"\nRežim: {MODES[mode]}")
    for account in selected:
        print(f"  {account['id']}: {account['source']['host']} → {account['target']['host']}")
        mapping = account.get("folder_map", {})
        if mapping:
            for source, target in mapping.items():
                print(f"    {source} → {target}")
        print("    Automatické mapování: " + ("ano" if account.get("automap", False) else "ne"))
    print("Logy: " + str(ROOT / "logs"))
    if use_arrow_menu():
        title = "Provést skutečné změny v cílové schránce?" if mode in WRITING_MODES else "Spustit vybranou úlohu?"
        index = arrow_choice(title + " Účty: " + ", ".join(a["id"] for a in selected),
                             ["Zrušit", "Spustit: " + MODES[mode]],
                             default=0 if mode in WRITING_MODES else 1)
        if index != 1:
            raise Cancelled()
        return
    if mode in WRITING_MODES:
        print("Tento režim provede skutečné změny v cílové schránce.")
        answer = ask("Spustit? [a/N]: ", "n")
    else:
        answer = ask("Spustit? [A/n]: ", "a")
    if answer.lower() not in {"a", "ano", "y", "yes"}:
        raise Cancelled()


@contextmanager
def migration_lock():
    # The same lock covers single-account runs and batches; OS releases it on exit.
    with (ROOT / ".migration.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("V tomto projektu už běží jiná úloha. Vyčkejte na její dokončení.") from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def run_accounts(selected, mode):
    if mode == "plan":
        for account in selected:
            print(shlex.join(build_command(account, mode)))
        return 0
    # Validate the whole selection before connecting to its first mailbox.
    for account in selected:
        validate_passwords(account)
    if not shutil.which("docker"):
        raise ValueError("Docker není dostupný. Spusťte Docker Desktop a ověřte instalaci.")
    with migration_lock():
        subprocess.run(["docker", "compose", "-f", str(ROOT / "docker-compose.yml"),
                        "config", "--quiet"], check=True, cwd=ROOT)
        (ROOT / "logs").mkdir(exist_ok=True)
        for account in selected:
            command = build_command(account, mode)
            print(f"\n{account['id']}: {MODES[mode]}", flush=True)
            result = subprocess.run(command, cwd=ROOT)
            if result.returncode:
                print(f"{account['id']}: chyba {result.returncode}; dávka zastavena.", file=sys.stderr)
                return result.returncode if result.returncode > 0 else 1
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     epilog="Bez výběru účtu se v terminálu otevře průvodce. q = konec.")
    parser.add_argument("--config", type=Path, default=ROOT / "accounts.json",
                        help="JSON soubor; relativní cesta se počítá od aktuálního adresáře")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--account", help="id jedné schránky (ruční výběr i při enabled: false)")
    selection.add_argument("--all", action="store_true", help="všechny schránky s enabled: true")
    parser.add_argument("--mode", choices=tuple(MODES),
                        help="bez průvodce je výchozí plan; průvodce nabízí dry-run")
    args = parser.parse_args()
    accounts = read_accounts(args.config)
    interactive = not args.account and not args.all
    if interactive:
        if not sys.stdin.isatty():
            parser.error("Průvodce vyžaduje terminál. Pro přímé spuštění použijte --account nebo --all a --mode.")
        selected = select_interactively(accounts)
        mode = args.mode or select_mode()
        review_selection(selected, mode)
    else:
        selected = [a for a in accounts if a["id"] == args.account] if args.account else [
            a for a in accounts if a.get("enabled", False)]
        mode = args.mode or "plan"
    if not selected:
        raise ValueError("Výběr je prázdný. Ověřte id, konfiguraci a u --all také enabled.")
    return run_accounts(selected, mode)


if __name__ == "__main__":
    os.umask(0o077)
    try:
        sys.exit(main())
    except (Cancelled, KeyboardInterrupt):
        print("\nZrušeno uživatelem.", file=sys.stderr)
        sys.exit(130)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Chyba: {error}", file=sys.stderr)
        sys.exit(1)
