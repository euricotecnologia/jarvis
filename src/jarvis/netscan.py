"""Ferramentas de recon de rede -- tudo em Python puro / comandos nativos do
Windows. NADA para instalar: sem nmap, sem whois.exe, sem openssl.

- varredura de portas: socket connect scan com threads
- WHOIS: consulta TCP porta 43 (IANA -> servidor do TLD -> servidor do dominio)
- TLS: modulo `ssl` da stdlib (getpeercert)
- DNS: `dnspython` (Python puro) quando disponivel, senao `nslookup`
- ping / tracert / arp: os proprios do Windows via subprocess
- portas locais / conexoes: psutil
"""

from __future__ import annotations

import concurrent.futures
import json
import re
import socket
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone

_UA = "jarvis-netscan/1.0"

# porta -> (servico, e_sensivel)
COMMON_PORTS: dict[int, str] = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 111: "RPCbind", 135: "MSRPC", 139: "NetBIOS",
    143: "IMAP", 161: "SNMP", 389: "LDAP", 443: "HTTPS", 445: "SMB",
    465: "SMTPS", 587: "SMTP", 636: "LDAPS", 993: "IMAPS", 995: "POP3S",
    1080: "SOCKS", 1433: "MSSQL", 1521: "Oracle", 2049: "NFS",
    2375: "Docker", 2376: "Docker TLS", 3000: "App/Grafana", 3306: "MySQL",
    3389: "RDP", 4444: "Metasploit?", 5000: "App/UPnP", 5432: "PostgreSQL",
    5601: "Kibana", 5900: "VNC", 5985: "WinRM", 5986: "WinRM TLS",
    6379: "Redis", 7001: "WebLogic", 8000: "HTTP alt", 8080: "HTTP proxy",
    8443: "HTTPS alt", 8888: "HTTP alt", 9000: "App", 9200: "Elasticsearch",
    11211: "Memcached", 27017: "MongoDB", 5555: "ADB",
}
# expostas a internet quase sempre sao risco:
RISKY_IF_PUBLIC = {21, 23, 135, 139, 445, 1433, 3306, 3389, 5432, 5900,
                   6379, 9200, 11211, 27017, 5985, 2375}

_WEB_PORTS = [80, 443, 8080, 8443, 8000, 8888, 3000, 5000, 9000]
_TOP_PORTS = sorted(COMMON_PORTS)


def _no_window() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


def _run(argv: list[str], timeout: float = 30.0) -> str:
    try:
        out = subprocess.run(
            argv, capture_output=True, timeout=timeout,
            creationflags=_no_window(), stdin=subprocess.DEVNULL,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return f"(falha ao rodar {argv[0]}: {exc})"
    raw = (out.stdout or b"") + (out.stderr or b"")
    for enc in ("utf-8", "cp850", "latin-1"):
        try:
            return raw.decode(enc).strip()
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace").strip()


# ---------------------------------------------------------------- portas
def resolve_ports_spec(spec: str | None) -> list[int]:
    spec = (spec or "comuns").strip().lower()
    if spec in ("", "comuns", "common", "top"):
        return list(_TOP_PORTS)
    if spec in ("web", "http"):
        return list(_WEB_PORTS)
    if spec in ("todas", "all", "1-65535"):
        return list(range(1, 65536))
    ports: list[int] = []
    for chunk in re.split(r"[,\s]+", spec):
        if not chunk:
            continue
        if "-" in chunk:
            a, _, b = chunk.partition("-")
            try:
                ports += list(range(int(a), int(b) + 1))
            except ValueError:
                continue
        else:
            try:
                ports.append(int(chunk))
            except ValueError:
                continue
    return [p for p in dict.fromkeys(ports) if 1 <= p <= 65535] or list(_TOP_PORTS)


@dataclass(frozen=True, slots=True)
class OpenPort:
    port: int
    service: str
    banner: str


def _probe_port(host: str, port: int, timeout: float) -> OpenPort | None:
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            banner = ""
            try:
                sock.settimeout(0.8)
                data = sock.recv(120)
                banner = data.decode("latin-1", "replace").strip()
            except OSError:
                pass
            return OpenPort(port, COMMON_PORTS.get(port, "?"), banner[:100])
    except OSError:
        return None


def scan_ports(
    host: str, spec: str | None = "comuns", *, timeout: float = 1.0,
    max_workers: int = 120, limit: int = 6000,
) -> dict:
    ports = resolve_ports_spec(spec)[:limit]
    ip = _resolve_first_ip(host)
    open_ports: list[OpenPort] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_probe_port, host, p, timeout): p for p in ports
        }
        for fut in concurrent.futures.as_completed(futures):
            result = fut.result()
            if result is not None:
                open_ports.append(result)
    open_ports.sort(key=lambda x: x.port)
    return {
        "host": host,
        "ip": ip,
        "checked": len(ports),
        "open": [
            {
                "port": p.port,
                "service": p.service,
                "banner": p.banner,
                "risky_if_public": p.port in RISKY_IF_PUBLIC,
            }
            for p in open_ports
        ],
    }


def check_single_port(host: str, port: int, *, timeout: float = 3.0) -> dict:
    result = _probe_port(host, int(port), timeout)
    return {
        "host": host, "port": int(port),
        "open": result is not None,
        "service": (result.service if result else COMMON_PORTS.get(int(port), "?")),
        "banner": (result.banner if result else ""),
    }


# ---------------------------------------------------------------- DNS
def _resolve_first_ip(host: str) -> str:
    try:
        return socket.gethostbyname(host)
    except OSError:
        return ""


def dns_records(name: str) -> dict:
    name = name.strip().rstrip(".")
    out: dict[str, object] = {"name": name}
    try:
        import dns.resolver  # type: ignore

        resolver = dns.resolver.Resolver()
        resolver.lifetime = 6.0
        for rtype in ("A", "AAAA", "MX", "TXT", "NS", "CNAME", "SOA"):
            try:
                answers = resolver.resolve(name, rtype)
                out[rtype] = [str(r.to_text()).strip('"') for r in answers]
            except Exception:  # noqa: BLE001
                out[rtype] = []
        out["source"] = "dnspython"
        return out
    except Exception:  # noqa: BLE001 - sem dnspython: cai pro nslookup
        pass
    raw = _run(["nslookup", "-type=ANY", name], timeout=15)
    out["source"] = "nslookup"
    out["raw"] = raw
    ips = re.findall(r"Address(?:es)?:\s*([\d.]+)", raw)
    out["A"] = ips
    return out


def reverse_dns(ip: str) -> dict:
    ip = ip.strip()
    names: list[str] = []
    try:
        host, aliases, _ = socket.gethostbyaddr(ip)
        names = [host, *aliases]
    except OSError:
        pass
    return {"ip": ip, "names": names}


# ---------------------------------------------------------------- TLS
def tls_certificate(host: str, port: int = 443, *, timeout: float = 6.0) -> dict:
    host = host.strip()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False  # ainda valida a cadeia; so nao exige o hostname
    try:
        with socket.create_connection((host, port), timeout=timeout) as raw:
            with ctx.wrap_socket(raw, server_hostname=host) as tls:
                cert = tls.getpeercert() or {}
                der = tls.getpeercert(binary_form=True)
                proto, cipher = tls.version(), tls.cipher()
        trusted = True
    except ssl.SSLCertVerificationError:
        # certificado auto-assinado / CA desconhecida: pega mesmo assim
        nova = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        nova.check_hostname = False
        nova.verify_mode = ssl.CERT_NONE
        try:
            with socket.create_connection((host, port), timeout=timeout) as raw:
                with nova.wrap_socket(raw, server_hostname=host) as tls:
                    der = tls.getpeercert(binary_form=True)
                    proto, cipher = tls.version(), tls.cipher()
            cert = _decode_der(der)
            trusted = False
        except (OSError, ssl.SSLError) as exc:
            return {"host": host, "port": port, "error": str(exc)}
    except (OSError, ssl.SSLError) as exc:
        return {"host": host, "port": port, "error": str(exc)}

    not_after = cert.get("notAfter", "")
    return {
        "host": host, "port": port,
        "trusted_chain": trusted,
        "subject": _name_from_cert(cert.get("subject")),
        "issuer": _name_from_cert(cert.get("issuer")),
        "valid_from": cert.get("notBefore", ""),
        "valid_until": not_after,
        "days_left": _days_until(not_after) if not_after else None,
        "san": [v for k, v in cert.get("subjectAltName", ()) if k == "DNS"],
        "protocol": proto,
        "cipher": cipher[0] if cipher else "",
        "der_bytes": len(der) if der else 0,
    }


def _decode_der(der: bytes | None) -> dict:
    """Parseia um certificado DER usando so a stdlib (via arquivo temporario)."""
    if not der:
        return {}
    import tempfile

    try:
        pem = ssl.DER_cert_to_PEM_cert(der)
        with tempfile.NamedTemporaryFile(
            "w", suffix=".pem", delete=False, encoding="ascii"
        ) as handle:
            handle.write(pem)
            path = handle.name
        try:
            return ssl._ssl._test_decode_cert(path)  # type: ignore[attr-defined]
        finally:
            import os

            os.unlink(path)
    except Exception:  # noqa: BLE001
        return {}


def _name_from_cert(field) -> str:
    if not field:
        return ""
    parts = []
    for rdn in field:
        for key, value in rdn:
            parts.append(f"{key}={value}")
    return ", ".join(parts)


def _days_until(value: str) -> int | None:
    for fmt in ("%b %d %H:%M:%S %Y %Z", "%b %d %H:%M:%S %Y GMT"):
        try:
            dt = datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
            return (dt - datetime.now(timezone.utc)).days
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------- HTTP
_SECURITY_HEADERS = (
    "strict-transport-security", "content-security-policy",
    "x-frame-options", "x-content-type-options", "referrer-policy",
    "permissions-policy", "cross-origin-opener-policy",
)


def http_headers(url: str, *, timeout: float = 12.0) -> dict:
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    request = urllib.request.Request(url, headers={"User-Agent": _UA}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            status = resp.status
            final = resp.geturl()
    except urllib.error.HTTPError as exc:
        headers = {k.lower(): v for k, v in (exc.headers or {}).items()}
        status, final = exc.code, url
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {"url": url, "error": str(exc)}

    present = [h for h in _SECURITY_HEADERS if h in headers]
    missing = [h for h in _SECURITY_HEADERS if h not in headers]
    return {
        "url": url, "final_url": final, "status": status,
        "server": headers.get("server", ""),
        "powered_by": headers.get("x-powered-by", ""),
        "security_headers_present": present,
        "security_headers_missing": missing,
        "all_headers": headers,
    }


# ---------------------------------------------------------------- WHOIS
def whois_query(domain: str, *, timeout: float = 10.0) -> dict:
    domain = domain.strip().lower().rstrip(".")
    tld = domain.rsplit(".", 1)[-1]
    chain: list[str] = []
    try:
        text = _whois_ask("whois.iana.org", tld, timeout)
        chain.append("whois.iana.org")
        m = re.search(r"whois:\s*(\S+)", text, re.IGNORECASE)
        server = m.group(1) if m else None
        if server:
            text = _whois_ask(server, domain, timeout)
            chain.append(server)
            # alguns TLD referenciam o whois do registrar
            m2 = re.search(r"Registrar WHOIS Server:\s*(\S+)", text, re.IGNORECASE)
            if m2 and m2.group(1).lower() not in {c.lower() for c in chain}:
                try:
                    more = _whois_ask(m2.group(1), domain, timeout)
                    if len(more) > 40:
                        text = more
                        chain.append(m2.group(1))
                except OSError:
                    pass
    except OSError as exc:
        return {"domain": domain, "error": str(exc), "servers": chain}
    return {
        "domain": domain,
        "servers": chain,
        "registrar": _grab(text, r"Registrar:\s*(.+)"),
        "created": _grab(text, r"Crematio?n Date:\s*(.+)|Created(?: On)?:\s*(.+)"),
        "expires": _grab(text, r"(?:Registry )?Expir\w+ Date:\s*(.+)|Expir\w+:\s*(.+)"),
        "name_servers": re.findall(r"Name Server:\s*(\S+)", text, re.IGNORECASE),
        "raw": text[:4000],
    }


def _whois_ask(server: str, query: str, timeout: float) -> str:
    with socket.create_connection((server, 43), timeout=timeout) as sock:
        sock.sendall((query + "\r\n").encode("utf-8"))
        chunks = []
        sock.settimeout(timeout)
        while True:
            try:
                data = sock.recv(4096)
            except OSError:
                break
            if not data:
                break
            chunks.append(data)
    return b"".join(chunks).decode("utf-8", "replace")


def _grab(text: str, pattern: str) -> str:
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return ""
    return next((g.strip() for g in m.groups() if g), "").strip()


# ---------------------------------------------------------------- IP / geo
def public_ip() -> dict:
    for url in ("https://api.ipify.org", "https://ifconfig.me/ip",
                "https://icanhazip.com"):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=8) as resp:
                ip = resp.read().decode("ascii", "replace").strip()
            if re.fullmatch(r"[0-9a-fA-F:.]+", ip):
                geo = geoip(ip)
                return {"ip": ip, "geo": geo}
        except (urllib.error.URLError, OSError):
            continue
    return {"error": "nao consegui descobrir o IP publico (sem internet?)"}


def geoip(ip: str) -> dict:
    ip = ip.strip()
    url = f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,isp,org,as,query"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {"ip": ip, "error": str(exc)}
    if data.get("status") != "success":
        return {"ip": ip, "error": data.get("message", "consulta falhou")}
    return {
        "ip": data.get("query", ip),
        "country": data.get("country", ""),
        "region": data.get("regionName", ""),
        "city": data.get("city", ""),
        "isp": data.get("isp", ""),
        "org": data.get("org", ""),
        "asn": data.get("as", ""),
    }


# ---------------------------------------------------------------- Windows nativo
def ping(host: str, count: int = 4) -> dict:
    flag = "-n" if sys.platform == "win32" else "-c"
    raw = _run(["ping", flag, str(count), host], timeout=count * 4 + 10)
    loss = _grab(raw, r"\(?(\d+)\s*%\s*(?:de\s+)?(?:perda|loss|packet loss)")
    avg = _grab(raw, r"(?:M[ée]dia|Average|avg)\s*[=/]\s*(\d+(?:[.,]\d+)?)\s*ms")
    reachable = bool(re.search(r"TTL=|bytes from|ttl=", raw, re.IGNORECASE))
    return {
        "host": host, "reachable": reachable,
        "loss_pct": loss, "avg_ms": avg, "raw": raw,
    }


def traceroute(host: str, max_hops: int = 20) -> dict:
    cmd = (["tracert", "-d", "-h", str(max_hops), host]
           if sys.platform == "win32"
           else ["traceroute", "-n", "-m", str(max_hops), host])
    return {"host": host, "raw": _run(cmd, timeout=max_hops * 3 + 15)}


def arp_table() -> dict:
    return {"raw": _run(["arp", "-a"], timeout=15)}


def _psutil():
    try:
        import psutil  # type: ignore

        return psutil
    except Exception:  # noqa: BLE001
        return None


def local_listeners() -> dict:
    psutil = _psutil()
    if psutil is None:
        return {"raw": _run(["netstat", "-ano"], timeout=15), "source": "netstat"}
    rows = []
    for conn in psutil.net_connections(kind="inet"):
        if conn.status != psutil.CONN_LISTEN:
            continue
        name = ""
        try:
            if conn.pid:
                name = psutil.Process(conn.pid).name()
        except Exception:  # noqa: BLE001
            pass
        rows.append({
            "addr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "",
            "pid": conn.pid, "process": name,
        })
    rows.sort(key=lambda r: (r["addr"]))
    return {"listeners": rows, "source": "psutil"}


def active_connections() -> dict:
    psutil = _psutil()
    if psutil is None:
        return {"raw": _run(["netstat", "-ano"], timeout=15), "source": "netstat"}
    rows = []
    for conn in psutil.net_connections(kind="inet"):
        if conn.status not in (psutil.CONN_ESTABLISHED, "SYN_SENT"):
            continue
        name = ""
        try:
            if conn.pid:
                name = psutil.Process(conn.pid).name()
        except Exception:  # noqa: BLE001
            pass
        rows.append({
            "local": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "",
            "remote": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "",
            "pid": conn.pid, "process": name,
        })
    return {"connections": rows[:200], "source": "psutil"}


def firewall_status() -> dict:
    if sys.platform != "win32":
        return {"raw": "(firewall: so no Windows)"}
    raw = _run(
        ["powershell", "-NoProfile", "-Command",
         "Get-NetFirewallProfile | Select-Object Name,Enabled,"
         "DefaultInboundAction,DefaultOutboundAction | Format-Table -AutoSize"],
        timeout=20,
    )
    if not raw or "Enabled" not in raw:
        raw = _run(["netsh", "advfirewall", "show", "allprofiles", "state"], timeout=15)
    return {"raw": raw}
