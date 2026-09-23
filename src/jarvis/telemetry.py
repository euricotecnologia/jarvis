"""Telemetria local do computador: CPU, memória, GPU, rede, disco e segurança.

Tudo roda offline. `psutil` cobre CPU/memória/rede/disco; a GPU vem do
`nvidia-smi` quando existe (silencioso quando não existe). Nada aqui pode
lancar exceção para a interface: em caso de falha os campos ficam zerados.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any

try:  # psutil e dependencia do extra [gui]; degrada se faltar
    import psutil
except Exception:  # noqa: BLE001
    psutil = None  # type: ignore[assignment]


_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


@dataclass(frozen=True, slots=True)
class Metric:
    """Um cartao do painel: rotulo curto + percentual + duas linhas de detalhe."""

    percent: float = 0.0
    primary: str = "--"
    secondary: str = ""
    label: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "percent": round(self.percent, 1),
            "primary": self.primary,
            "secondary": self.secondary,
            "label": self.label,
        }


@dataclass(frozen=True, slots=True)
class SystemStats:
    cpu: Metric = field(default_factory=Metric)
    memory: Metric = field(default_factory=Metric)
    gpu: Metric = field(default_factory=Metric)
    network: Metric = field(default_factory=Metric)
    storage: Metric = field(default_factory=Metric)
    security: Metric = field(default_factory=Metric)
    uptime: str = "--"
    processes: int = 0
    net_down_mbps: float = 0.0
    net_up_mbps: float = 0.0
    health: float = 0.0
    efficiency: float = 0.0
    performance: float = 0.0
    available: bool = False

    def as_dict(self) -> dict[str, Any]:
        data = {key: value for key, value in asdict(self).items()}
        for key in ("cpu", "memory", "gpu", "network", "storage", "security"):
            data[key] = getattr(self, key).as_dict()
        data["uptime"] = self.uptime
        data["processes"] = self.processes
        data["net_down_mbps"] = round(self.net_down_mbps, 1)
        data["net_up_mbps"] = round(self.net_up_mbps, 1)
        data["health"] = round(self.health)
        data["efficiency"] = round(self.efficiency)
        data["performance"] = round(self.performance)
        data["available"] = self.available
        return data


def _fmt_bytes(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(num) < 1024.0:
            return f"{num:.1f} {unit}" if unit not in ("B", "KB") else f"{num:.0f} {unit}"
        num /= 1024.0
    return f"{num:.1f} EB"


def _fmt_uptime(seconds: float) -> str:
    seconds = max(0, int(seconds))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes = seconds // 60
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _query_gpu() -> Metric | None:
    """Le a GPU NVIDIA via nvidia-smi. Devolve None quando não ha GPU/driver."""
    executable = shutil.which("nvidia-smi")
    if not executable:
        return None
    try:
        output = subprocess.run(
            [
                executable,
                "--query-gpu=utilization.gpu,memory.used,memory.total,name",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2.5,
            creationflags=_NO_WINDOW,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    line = output.splitlines()[0] if output else ""
    parts = [piece.strip() for piece in line.split(",")]
    if len(parts) < 4:
        return None
    try:
        util = float(parts[0])
        used_mib = float(parts[1])
        total_mib = float(parts[2])
    except ValueError:
        return None
    name = parts[3].replace("NVIDIA ", "").replace("GeForce ", "").strip()
    used_gb = used_mib / 1024.0
    total_gb = max(total_mib / 1024.0, 0.1)
    return Metric(
        percent=util,
        primary=f"{util:.0f}%",
        secondary=f"{used_gb:.1f} / {total_gb:.1f} GB",
        label=name or "GPU",
    )


def _firewall_active() -> bool | None:
    if sys.platform != "win32":
        return None
    try:
        output = subprocess.run(
            ["netsh", "advfirewall", "show", "currentprofile", "state"],
            capture_output=True,
            text=True,
            timeout=2.0,
            creationflags=_NO_WINDOW,
        ).stdout.upper()
    except (OSError, subprocess.SubprocessError):
        return None
    for marker in ("ON", "LIGADO", "ENABLED", "ATIV", "SIM"):
        if marker in output:
            return True
    if "OFF" in output or "DESLIGADO" in output or "DESATIV" in output:
        return False
    return None


class SystemMonitor:
    """Amostra o sistema. `sample()` e barato (>=1s entre chamadas ideal)."""

    def __init__(self) -> None:
        self._last_net: tuple[float, float, float] | None = None
        self._gpu_cache: Metric | None = None
        self._gpu_checked_at = 0.0
        self._security_cache: Metric | None = None
        self._security_checked_at = 0.0
        if psutil is not None:
            try:
                psutil.cpu_percent(interval=None)  # primeira leitura zera o contador
            except Exception:  # noqa: BLE001
                pass

    # -- rede ---------------------------------------------------------------
    def _network(self) -> tuple[Metric, float, float]:
        assert psutil is not None
        now = time.monotonic()
        counters = psutil.net_io_counters()
        sent, recv = float(counters.bytes_sent), float(counters.bytes_recv)
        down = up = 0.0
        if self._last_net is not None:
            prev_t, prev_sent, prev_recv = self._last_net
            dt = max(now - prev_t, 1e-3)
            up = max(0.0, (sent - prev_sent) * 8 / 1e6 / dt)
            down = max(0.0, (recv - prev_recv) * 8 / 1e6 / dt)
        self._last_net = (now, sent, recv)
        # 0-100% relativo a uma linha de 200 Mbps para animar a barra.
        percent = min(100.0, max(down, up) / 200.0 * 100.0)
        return Metric(
            percent=percent,
            primary=f"\u2193 {down:.1f} Mbps",
            secondary=f"\u2191 {up:.1f} Mbps",
            label="REDE",
        ), down, up

    # -- gpu (cache de 3s) ------------------------------------------------
    def _gpu(self) -> Metric:
        now = time.monotonic()
        if self._gpu_cache is None or now - self._gpu_checked_at > 3.0:
            self._gpu_cache = _query_gpu()
            self._gpu_checked_at = now
        if self._gpu_cache is None:
            return Metric(primary="sem GPU", secondary="dedicada", label="GPU")
        return self._gpu_cache

    # -- segurança (cache de 30s) --------------------------------------------
    def _security(self) -> Metric:
        now = time.monotonic()
        if self._security_cache is None or now - self._security_checked_at > 30.0:
            active = _firewall_active()
            if active is None:
                self._security_cache = Metric(
                    percent=100.0, primary="ATIVA", secondary="Sistema local", label="SEGURANCA"
                )
            elif active:
                self._security_cache = Metric(
                    percent=100.0,
                    primary="ATIVA",
                    secondary="Firewall e Proteção",
                    label="SEGURANCA",
                )
            else:
                self._security_cache = Metric(
                    percent=35.0,
                    primary="ATENCAO",
                    secondary="Firewall desligado",
                    label="SEGURANCA",
                )
            self._security_checked_at = now
        return self._security_cache

    def sample(self) -> SystemStats:
        if psutil is None:
            return SystemStats(available=False)

        try:
            cpu_percent = float(psutil.cpu_percent(interval=None))
            freq = psutil.cpu_freq()
            ghz = (freq.current / 1000.0) if freq and freq.current else 0.0
            cores = psutil.cpu_count(logical=True) or 0
            cpu = Metric(
                percent=cpu_percent,
                primary=f"{cpu_percent:.0f}%",
                secondary=(f"{ghz:.2f} GHz" if ghz else f"{cores} nucleos"),
                label="CPU",
            )

            vmem = psutil.virtual_memory()
            mem = Metric(
                percent=float(vmem.percent),
                primary=f"{vmem.percent:.0f}%",
                secondary=f"{vmem.used / 1e9:.1f} / {vmem.total / 1e9:.1f} GB",
                label="MEMORIA",
            )

            usage = psutil.disk_usage(_primary_disk())
            storage = Metric(
                percent=float(usage.percent),
                primary=f"{usage.used / 1e12:.1f} / {usage.total / 1e12:.1f} TB"
                if usage.total >= 1e12
                else f"{usage.used / 1e9:.0f} / {usage.total / 1e9:.0f} GB",
                secondary=f"{usage.percent:.0f}% em uso",
                label="ARMAZENAMENTO",
            )

            network, down, up = self._network()
            gpu = self._gpu()
            security = self._security()

            uptime = _fmt_uptime(time.time() - psutil.boot_time())
            processes = len(psutil.pids())

            performance = max(0.0, 100.0 - cpu_percent * 0.7 - gpu.percent * 0.3)
            efficiency = max(0.0, 100.0 - mem.percent * 0.6 - cpu_percent * 0.4)
            health = max(
                0.0,
                100.0
                - max(0.0, cpu_percent - 80)
                - max(0.0, mem.percent - 85)
                - max(0.0, storage.percent - 90)
                - (0 if security.percent >= 100 else 15),
            )

            return SystemStats(
                cpu=cpu,
                memory=mem,
                gpu=gpu,
                network=network,
                storage=storage,
                security=security,
                uptime=uptime,
                processes=processes,
                net_down_mbps=down,
                net_up_mbps=up,
                health=min(100.0, health),
                efficiency=min(100.0, efficiency),
                performance=min(100.0, performance),
                available=True,
            )
        except Exception:  # noqa: BLE001 - a UI nunca pode quebrar por telemetria
            return SystemStats(available=False)


def _primary_disk() -> str:
    if sys.platform == "win32":
        return "C:\\"
    return "/"
