"""Painel do sistema: especificações, processos, discos, energia e manutenção.

psutil cobre quase tudo; alguns detalhes (memória, placa-mae) vem de uma
chamada ao PowerShell/CIM. Nada aqui lanca exceção para a interface.
"""

from __future__ import annotations

import ctypes
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import psutil
except Exception:  # noqa: BLE001
    psutil = None  # type: ignore[assignment]

_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# Processos que não devem ser finalizados pela interface.
PROTECTED_PROCESSES = {
    "system", "system idle process", "registry", "smss.exe", "csrss.exe",
    "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe", "svchost.exe",
    "dwm.exe", "explorer.exe", "fontdrvhost.exe", "spoolsv.exe", "ntoskrnl.exe",
    "memory compression", "audiodg.exe", "sihost.exe", "ctfmon.exe",
    "taskhostw.exe", "runtimebroker.exe", "wudfhost.exe",
}
# PIDs do próprio Jarvis (preenchido em runtime) para nunca se auto-finalizar.
_SELF_PIDS = {os.getpid()}
try:
    _SELF_PIDS.add(os.getppid())
except (AttributeError, OSError):
    pass


def _is_protected(name: str, pid: int) -> bool:
    return pid <= 4 or pid in _SELF_PIDS or name.lower() in PROTECTED_PROCESSES


def _run(args: list[str], timeout: float = 6.0) -> str:
    try:
        return subprocess.run(
            args, capture_output=True, text=True, timeout=timeout,
            creationflags=_NO_WINDOW,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def _fmt_bytes(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024.0:
            return f"{num:.0f} {unit}" if unit in ("B", "KB") else f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"


def _fmt_uptime(seconds: float) -> str:
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def _powershell_hardware() -> dict[str, Any]:
    if sys.platform != "win32":
        return {}
    script = (
        "$ErrorActionPreference='SilentlyContinue';"
        "$cpu=Get-CimInstance Win32_Processor|Select-Object -First 1;"
        "$mem=Get-CimInstance Win32_PhysicalMemory;"
        "$bb=Get-CimInstance Win32_BaseBoard|Select-Object -First 1;"
        "$bios=Get-CimInstance Win32_BIOS|Select-Object -First 1;"
        "$os=Get-CimInstance Win32_OperatingSystem;"
        "[pscustomobject]@{"
        "cpu=$cpu.Name;"
        "cpu_mhz=$cpu.MaxClockSpeed;"
        "mem_speed=($mem|Measure-Object -Property Speed -Maximum).Maximum;"
        "mem_sticks=($mem|Measure-Object).Count;"
        "board=(\"{0} {1}\" -f $bb.Manufacturer,$bb.Product);"
        "bios=$bios.SMBIOSBIOSVersion;"
        "os_build=$os.BuildNumber;"
        "os_caption=$os.Caption"
        "}|ConvertTo-Json -Compress"
    )
    raw = _run(["powershell", "-NoProfile", "-Command", script], timeout=12.0)
    try:
        return json.loads(raw) if raw.strip() else {}
    except (ValueError, TypeError):
        return {}


def _gpu_details() -> dict[str, Any]:
    binary = shutil.which("nvidia-smi")
    if not binary:
        return {}
    out = _run([
        binary,
        "--query-gpu=name,driver_version,temperature.gpu,power.draw,power.limit,"
        "memory.total,memory.used,utilization.gpu",
        "--format=csv,noheader,nounits",
    ], timeout=4.0)
    line = out.splitlines()[0] if out.strip() else ""
    parts = [piece.strip() for piece in line.split(",")]
    if len(parts) < 8:
        return {}

    def num(value: str) -> float | None:
        try:
            return float(value)
        except ValueError:
            return None

    temp, draw, limit = num(parts[2]), num(parts[3]), num(parts[4])
    total, used, util = num(parts[5]), num(parts[6]), num(parts[7])
    result = {"name": parts[0].replace("NVIDIA ", ""), "driver": parts[1]}
    result["temp"] = f"{temp:.0f} C" if temp is not None else "--"
    if draw is not None and limit is not None:
        result["power"] = f"{draw:.0f} / {limit:.0f} W"
    else:
        result["power"] = "--"
    if total is not None and used is not None:
        result["memory"] = f"{used / 1024:.1f} / {total / 1024:.1f} GB"
    else:
        result["memory"] = "--"
    result["usage"] = f"{util:.0f}%" if util is not None else "--"
    return result


def full_specs() -> dict[str, Any]:
    """Especificações de hardware e software. Chamada sob demanda (não a cada 2s)."""
    if psutil is None:
        return {"available": False, "hardware": [], "system": [], "gpu": []}
    hw = _powershell_hardware()
    freq = psutil.cpu_freq()
    vmem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    boot = datetime.fromtimestamp(psutil.boot_time())

    cpu_name = hw.get("cpu") or platform.processor() or "CPU"
    base_ghz = (hw.get("cpu_mhz") or 0) / 1000.0
    cur_ghz = (freq.current / 1000.0) if freq and freq.current else 0.0

    def row(label: str, value: Any) -> dict[str, str]:
        return {"k": label, "v": str(value)}

    hardware = [
        row("Processador", cpu_name),
        row("Nucleos / Threads", f"{psutil.cpu_count(logical=False)} nucleos, {psutil.cpu_count(logical=True)} threads"),
        row("Frequencia", f"{cur_ghz:.2f} GHz agora" + (f" (base {base_ghz:.1f} GHz)" if base_ghz else "")),
        row("Memória RAM", f"{_fmt_bytes(vmem.total)}"
            + (f" - {hw['mem_sticks']} pente(s)" if hw.get("mem_sticks") else "")
            + (f" @ {hw['mem_speed']} MHz" if hw.get("mem_speed") else "")),
        row("Memória em uso", f"{_fmt_bytes(vmem.used)} ({vmem.percent:.0f}%)"),
        row("Arquivo de paginação",
            f"{_fmt_bytes(swap.used)} / {_fmt_bytes(swap.total)}" if swap.total else "desativado"),
    ]
    if hw.get("board"):
        hardware.append(row("Placa-mae", hw["board"].strip()))
    if hw.get("bios"):
        hardware.append(row("BIOS", hw["bios"]))

    system = [
        row("Sistema", hw.get("os_caption") or f"{platform.system()} {platform.release()}"),
        row("Build", hw.get("os_build") or platform.version()),
        row("Arquitetura", platform.machine()),
        row("Computador", platform.node()),
        row("Ligado ha", _fmt_uptime(time.time() - psutil.boot_time())),
        row("Último boot", boot.strftime("%d/%m/%Y %H:%M")),
        row("Python", platform.python_version()),
    ]

    gpu = _gpu_details()
    gpu_rows = []
    if gpu:
        gpu_rows = [
            row("Modelo", gpu["name"]),
            row("Driver", gpu["driver"]),
            row("Temperatura", gpu["temp"]),
            row("Consumo", gpu["power"]),
            row("Memória de video", gpu["memory"]),
            row("Uso agora", gpu["usage"]),
        ]

    return {"available": True, "hardware": hardware, "system": system, "gpu": gpu_rows}


# -- processos -----------------------------------------------------------
def list_processes(sort_by: str = "cpu", limit: int = 40) -> list[dict[str, Any]]:
    if psutil is None:
        return []
    procs = list(psutil.process_iter(["pid", "name", "username"]))
    for proc in procs:
        try:
            proc.cpu_percent(None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    time.sleep(0.3)
    cores = psutil.cpu_count(logical=True) or 1
    rows: list[dict[str, Any]] = []
    for proc in procs:
        if proc.pid <= 4:
            continue
        try:
            with proc.oneshot():
                cpu = proc.cpu_percent(None) / cores
                mem = proc.memory_info().rss
                name = proc.name()
                user = (proc.username() or "").split("\\")[-1]
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            continue
        if name.lower() == "system idle process":
            continue
        rows.append({
            "pid": proc.pid,
            "name": name,
            "user": user,
            "cpu": round(cpu, 1),
            "cpuText": f"{cpu:.1f}%",
            "memBytes": mem,
            "memText": _fmt_bytes(mem),
            "protected": _is_protected(name, proc.pid),
        })
    key = "memBytes" if sort_by == "memory" else "cpu"
    rows.sort(key=lambda item: item[key], reverse=True)
    return rows[:limit]


def kill_process(pid: int) -> dict[str, Any]:
    if psutil is None:
        return {"ok": False, "message": "psutil indisponível."}
    try:
        proc = psutil.Process(pid)
        name = proc.name()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return {"ok": False, "message": "Processo não encontrado."}
    if _is_protected(name, pid):
        return {"ok": False, "message": f"'{name}' e um processo protegido; não vou finalizar."}
    try:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except psutil.TimeoutExpired:
            proc.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
        return {"ok": False, "message": f"Não consegui finalizar: {exc}"}
    return {"ok": True, "message": f"'{name}' (PID {pid}) finalizado."}


# -- discos --------------------------------------------------------------
def _dir_size(path: Path, *, budget_seconds: float = 4.0) -> int:
    total = 0
    deadline = time.monotonic() + budget_seconds
    stack = [path]
    while stack and time.monotonic() < deadline:
        current = stack.pop()
        try:
            for entry in os.scandir(current):
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat().st_size
                    elif entry.is_dir(follow_symlinks=False):
                        stack.append(Path(entry.path))
                except OSError:
                    continue
        except OSError:
            continue
    return total


def _recycle_bin_size() -> tuple[int, int]:
    if sys.platform != "win32":
        return 0, 0
    try:
        SHQUERYRBINFO = ctypes.c_uint64 * 3

        class INFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint32),
                ("i64Size", ctypes.c_int64),
                ("i64NumItems", ctypes.c_int64),
            ]

        info = INFO()
        info.cbSize = ctypes.sizeof(INFO)
        res = ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info))
        if res == 0:
            return int(info.i64Size), int(info.i64NumItems)
    except Exception:  # noqa: BLE001
        pass
    return 0, 0


def disks() -> dict[str, Any]:
    if psutil is None:
        return {"volumes": [], "temp": {}, "recycle": {}}
    volumes = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except OSError:
            continue
        volumes.append({
            "device": part.device,
            "fstype": part.fstype,
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "percent": usage.percent,
            "totalText": _fmt_bytes(usage.total),
            "usedText": _fmt_bytes(usage.used),
            "freeText": _fmt_bytes(usage.free),
        })
    temp_dir = Path(os.environ.get("TEMP") or os.environ.get("TMP") or "/tmp")
    temp_size = _dir_size(temp_dir) if temp_dir.is_dir() else 0
    rb_size, rb_items = _recycle_bin_size()
    return {
        "volumes": volumes,
        "temp": {"path": str(temp_dir), "size": temp_size, "sizeText": _fmt_bytes(temp_size)},
        "recycle": {"size": rb_size, "items": rb_items, "sizeText": _fmt_bytes(rb_size)},
    }


def clean_temp() -> dict[str, Any]:
    temp_dir = Path(os.environ.get("TEMP") or os.environ.get("TMP") or "")
    if not temp_dir.is_dir():
        return {"ok": False, "message": "Pasta de temporarios não encontrada."}
    freed = 0
    removed = 0
    for entry in list(temp_dir.iterdir()):
        try:
            size = entry.stat().st_size if entry.is_file() else _dir_size(entry, budget_seconds=1.0)
        except OSError:
            size = 0
        try:
            if entry.is_file() or entry.is_symlink():
                entry.unlink()
            else:
                shutil.rmtree(entry)
            freed += size
            removed += 1
        except OSError:
            continue  # em uso -> ignora
    return {
        "ok": True,
        "message": f"{removed} item(ns) removido(s), {_fmt_bytes(freed)} liberado(s).",
    }


def empty_recycle_bin() -> dict[str, Any]:
    if sys.platform != "win32":
        return {"ok": False, "message": "So no Windows."}
    try:
        # 0x07 = sem confirmação, sem progresso, sem som
        res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x07)
        if res in (0, -2147418113):  # S_OK ou "ja vazia"
            return {"ok": True, "message": "Lixeira esvaziada."}
        return {"ok": False, "message": f"Falha ao esvaziar (código {res})."}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"Falha: {exc}"}


# -- energia -----------------------------------------------------------
def power_status() -> dict[str, Any]:
    result: dict[str, Any] = {"hasBattery": False}
    if psutil is not None:
        battery = psutil.sensors_battery()
        if battery is not None:
            result["hasBattery"] = True
            result["percent"] = round(battery.percent)
            result["plugged"] = bool(battery.power_plugged)
            secs = battery.secsleft
            if secs is not None and secs >= 0:
                result["remaining"] = _fmt_uptime(secs)
            else:
                result["remaining"] = "carregando" if battery.power_plugged else "--"
    plans, active = _power_plans()
    result["plans"] = plans
    result["activePlan"] = active
    return result


def _power_plans() -> tuple[list[dict[str, str]], str]:
    if sys.platform != "win32":
        return [], ""
    import re

    out = _run(["powercfg", "/list"], timeout=5.0)
    plans: list[dict[str, str]] = []
    active = ""
    for match in re.finditer(
        r"([0-9a-f]{8}-[0-9a-f-]{27,})\s*\(([^)]+)\)(\s*\*)?", out, re.IGNORECASE
    ):
        guid, name, star = match.group(1), match.group(2).strip(), match.group(3)
        plans.append({"guid": guid, "name": name})
        if star:
            active = guid
    return plans, active


def set_power_plan(guid: str) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"ok": False, "message": "So no Windows."}
    import re

    if not re.fullmatch(r"[0-9a-f-]{30,}", guid, re.IGNORECASE):
        return {"ok": False, "message": "Plano invalido."}
    _run(["powercfg", "/setactive", guid], timeout=5.0)
    _, active = _power_plans()
    if active.lower() == guid.lower():
        return {"ok": True, "message": "Plano de energia alterado."}
    return {"ok": False, "message": "Não consegui alterar o plano."}


# -- ações rápidas -----------------------------------------------------
_QUICK_ACTIONS: dict[str, tuple[str, list[str]]] = {
    "flush_dns": ("Cache de DNS limpo.", ["ipconfig", "/flushdns"]),
    "restart_explorer": ("Explorer reiniciado.", []),
    "task_manager": ("", ["taskmgr"]),
    "windows_settings": ("", ["cmd", "/c", "start", "ms-settings:"]),
    "control_panel": ("", ["control"]),
    "windows_update": ("", ["cmd", "/c", "start", "ms-settings:windowsupdate"]),
}


def run_quick_action(action_id: str) -> dict[str, Any]:
    if action_id == "restart_explorer":
        _run(["taskkill", "/f", "/im", "explorer.exe"], timeout=5.0)
        try:
            subprocess.Popen(["explorer.exe"], creationflags=_NO_WINDOW)
        except OSError:
            pass
        return {"ok": True, "message": "Explorer reiniciado."}
    entry = _QUICK_ACTIONS.get(action_id)
    if entry is None:
        return {"ok": False, "message": "Ação desconhecida."}
    message, args = entry
    if not args:
        return {"ok": False, "message": "Ação indisponível."}
    try:
        if action_id == "flush_dns":
            _run(args, timeout=8.0)
        else:
            subprocess.Popen(args, creationflags=_NO_WINDOW)
    except OSError as exc:
        return {"ok": False, "message": f"Falha: {exc}"}
    return {"ok": True, "message": message or "Aberto."}
