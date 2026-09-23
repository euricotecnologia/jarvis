"""Ações rápidas de segurança para o perfil Ciberseguranca.

Cada botão do painel monta uma instrução em linguagem natural e manda pro
agente (que ja tem shell local + `listar_servidores`). Nada roda aqui direto:
o agente executa, explica o resultado e o risco. Tudo em cima de alvos do
proprio usuario / autorizados.
"""

from __future__ import annotations

from dataclasses import dataclass, field

_AUTH = "[Teste de seguranca autorizado, em ativo proprio do usuario] "


@dataclass(frozen=True, slots=True)
class Field:
    key: str
    label: str
    placeholder: str = ""
    optional: bool = False
    default: str = ""


@dataclass(frozen=True, slots=True)
class SecurityAction:
    id: str
    label: str
    icon: str
    category: str
    description: str
    prompt: str
    fields: tuple[Field, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "icon": self.icon,
            "category": self.category,
            "description": self.description,
            "fields": [
                {
                    "key": f.key,
                    "label": f.label,
                    "placeholder": f.placeholder,
                    "optional": f.optional,
                    "default": f.default,
                }
                for f in self.fields
            ],
        }


_HOST = Field("alvo", "Alvo", "IP, dominio ou apelido do servidor salvo")
_DOMAIN = Field("dominio", "Dominio", "ex.: exemplo.com")
_IP = Field("ip", "Endereco IP", "ex.: 203.0.113.10")
_URL = Field("url", "URL", "https://exemplo.com")

ACTIONS: tuple[SecurityAction, ...] = (
    SecurityAction(
        "ping", "Ping", "\U0001F4E1", "Rede",
        "Ve se o host responde e a latencia.",
        _AUTH + "Faca um ping em {alvo} (4 pacotes). Diga se responde, a "
        "latencia media/min/max e se houve perda de pacotes. Se for um apelido "
        "de servidor cadastrado, resolva o IP antes com listar_servidores.",
        (_HOST,),
    ),
    SecurityAction(
        "traceroute", "Tracar rota", "\U0001F9ED", "Rede",
        "Mostra o caminho ate o host, salto a salto.",
        _AUTH + "Trace a rota (tracert) ate {alvo} e liste os saltos com a "
        "latencia. Aponte em que ponto a latencia sobe muito ou some.",
        (_HOST,),
    ),
    SecurityAction(
        "portas", "Verificar portas abertas", "\U0001F513", "Portas",
        "Varredura das portas comuns do alvo.",
        _AUTH + "Verifique quais portas estao abertas em {alvo} (portas: "
        "{portas}). Use o shell LOCAL (Test-NetConnection ou nmap se estiver "
        "instalado - NAO instale). Para cada porta aberta, diga o servico "
        "tipico e se e arriscado deixar exposta. Nao faca nada intrusivo.",
        (
            _HOST,
            Field(
                "portas", "Portas", "comuns, web, todas ou lista 22,80,443",
                optional=True, default="comuns",
            ),
        ),
    ),
    SecurityAction(
        "porta_especifica", "Testar uma porta", "\U0001F50C", "Portas",
        "Checa uma unica porta e o servico.",
        _AUTH + "Teste se a porta {porta} de {alvo} esta aberta e, se der, qual "
        "servico/banner responde.",
        (_HOST, Field("porta", "Porta", "ex.: 22")),
    ),
    SecurityAction(
        "portas_locais", "Portas em escuta (neste PC)", "\U0001F6E1", "Local",
        "O que este computador esta expondo.",
        _AUTH + "Liste as portas que ESTE PC esta escutando e o processo dono "
        "de cada uma. Aponte qualquer uma que normalmente nao deveria estar "
        "aberta numa maquina pessoal.",
    ),
    SecurityAction(
        "conexoes", "Conexoes de rede ativas", "\U0001F517", "Local",
        "netstat com os processos donos.",
        _AUTH + "Liste as conexoes de rede ativas deste PC (netstat -ano) com "
        "o nome do processo dono. Destaque conexoes de saida para IPs/portas "
        "incomuns.",
    ),
    SecurityAction(
        "dns", "Resolver DNS", "\U0001F310", "Rede",
        "Registros A, AAAA, MX, TXT, NS do dominio.",
        _AUTH + "Resolva os registros DNS de {dominio}: A, AAAA, MX, TXT, NS, "
        "CNAME. Comente o que cada um revela (provedor de e-mail, CDN, SPF/DMARC "
        "etc.).",
        (_DOMAIN,),
    ),
    SecurityAction(
        "dns_reverso", "DNS reverso", "\U0001F501", "Rede",
        "De um IP para o nome de host.",
        _AUTH + "Faca o DNS reverso (PTR) de {ip} e diga que host aparece.",
        (_IP,),
    ),
    SecurityAction(
        "whois", "WHOIS do dominio", "\U0001F4C7", "Rede",
        "Dono, registrador e datas do dominio.",
        _AUTH + "Consulte o WHOIS de {dominio}: organizacao dona, registrador, "
        "data de criacao e de expiracao, servidores de nome. Avise se estiver "
        "perto de expirar.",
        (_DOMAIN,),
    ),
    SecurityAction(
        "http_headers", "Cabecalhos HTTP", "\U0001F4C4", "Web",
        "Cabecalhos de seguranca do site.",
        _AUTH + "Baixe os cabecalhos HTTP de {url} (siga redirecionamentos). "
        "Aponte quais cabecalhos de seguranca estao presentes ou FALTANDO "
        "(HSTS, Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, "
        "Referrer-Policy, Permissions-Policy) e o servidor/tecnologia expostos "
        "no cabecalho Server/X-Powered-By.",
        (_URL,),
    ),
    SecurityAction(
        "ssl", "Checar SSL/TLS", "\U0001F512", "Web",
        "Certificado, validade e algoritmo.",
        _AUTH + "Verifique o certificado TLS de {alvo} na porta 443: emissor, "
        "para quem foi emitido (CN/SAN), data de validade, algoritmo de "
        "assinatura e versoes de TLS aceitas. Avise se expira em menos de 30 "
        "dias ou se aceita protocolos antigos.",
        (_HOST,),
    ),
    SecurityAction(
        "rede_local", "Dispositivos na rede local", "\U0001F4F6", "Local",
        "Quem esta conectado no seu Wi-Fi/LAN.",
        _AUTH + "Descubra os dispositivos ativos na minha rede local ({faixa}). "
        "Use a tabela ARP e/ou um ping sweep leve. Liste IP, MAC e, se der, o "
        "fabricante pelo MAC. Aponte dispositivos que voce nao reconhece.",
        (
            Field(
                "faixa", "Faixa de rede", "vazio = detectar automatico",
                optional=True, default="automatico",
            ),
        ),
    ),
    SecurityAction(
        "meu_ip", "Meu IP publico", "\U0001F30D", "Rede",
        "IP externo, provedor e o que ele expoe.",
        _AUTH + "Descubra meu IP publico e o provedor (ISP/ASN) usando um "
        "servico publico. Diga se ha portas obvias expostas para a internet "
        "(so consulta publica, sem varredura pesada).",
    ),
    SecurityAction(
        "geoip", "Geolocalizar IP", "\U0001F4CD", "Rede",
        "Pais, provedor e organizacao de um IP.",
        _AUTH + "Descubra a localizacao aproximada (pais/cidade), o provedor "
        "(ISP/ASN) e a organizacao do IP {ip} usando fontes publicas.",
        (_IP,),
    ),
    SecurityAction(
        "firewall", "Estado do firewall", "\U0001F9F1", "Local",
        "Perfis e regras de entrada do Windows.",
        _AUTH + "Verifique o Firewall do Windows: quais perfis (dominio/privado/"
        "publico) estao ativos e as regras de ENTRADA mais permissivas que "
        "estao habilitadas. Aponte regras arriscadas (portas abertas para "
        "qualquer origem).",
    ),
    SecurityAction(
        "analise", "Analisar seguranca (completo)", "\U0001F50D", "Completo",
        "Panorama do alvo e riscos priorizados.",
        _AUTH + "Faca uma analise de seguranca de {alvo}, so com tecnicas "
        "leves e NAO intrusivas: portas comuns abertas + servico de cada uma, "
        "cabecalhos HTTP se houver site, certificado TLS, e registros DNS "
        "relevantes. No fim, resuma os riscos em ordem de prioridade (alto/"
        "medio/baixo) e de uma recomendacao pratica para cada um.",
        (_HOST,),
    ),
    SecurityAction(
        "latencia", "Qualidade da conexao", "\U0001F4CA", "Rede",
        "Latencia, jitter e perda da sua internet.",
        _AUTH + "Meca a qualidade da minha conexao: faca ping para alvos "
        "conhecidos (ex.: 1.1.1.1, 8.8.8.8, o gateway) por ~10 pacotes e "
        "relate latencia media, jitter e perda de pacotes.",
    ),
)

_BY_ID = {a.id: a for a in ACTIONS}


def security_actions() -> list[dict[str, object]]:
    return [a.as_dict() for a in ACTIONS]


def get_action(action_id: str) -> SecurityAction | None:
    return _BY_ID.get((action_id or "").strip())


def build_prompt(action_id: str, params: dict[str, str] | None) -> str:
    action = get_action(action_id)
    if action is None:
        raise KeyError(f"acao de seguranca desconhecida: {action_id!r}")
    values = {key: str(value).strip() for key, value in (params or {}).items()}
    for f in action.fields:
        if not values.get(f.key):
            if f.optional:
                values[f.key] = f.default
            else:
                raise ValueError(f"Preencha o campo '{f.label}'.")
    try:
        return action.prompt.format(**values)
    except KeyError as exc:  # placeholder sem valor
        raise ValueError(f"Falta a informacao {exc}.") from exc


# ---------------------------------------------------------------- execucao
def _fill(action, params):
    values = {k: str(v).strip() for k, v in (params or {}).items()}
    for f in action.fields:
        if not values.get(f.key):
            if f.optional:
                values[f.key] = f.default
            elif f.key == "faixa":
                values[f.key] = "automatico"
            else:
                raise ValueError(f"Preencha o campo '{f.label}'.")
    return values


def run_action(action_id: str, params: dict[str, str] | None) -> str:
    """Roda a acao de verdade (netscan) e devolve um relatorio em texto.

    Nao levanta em falha de rede -- o erro entra no relatorio pro modelo ler.
    """
    action = get_action(action_id)
    if action is None:
        raise KeyError(action_id)
    v = _fill(action, params)
    from jarvis import netscan as ns

    try:
        if action_id == "ping":
            r = ns.ping(v["alvo"])
            return (f"ping {r['host']}\nresponde: {r.get('reachable')}\n"
                    f"perda: {r.get('loss_pct') or '?'}%  |  latencia media: "
                    f"{r.get('avg_ms') or '?'} ms\n\n{r['raw'][:1500]}")
        if action_id == "traceroute":
            return f"tracert {v['alvo']}\n\n{ns.traceroute(v['alvo'])['raw'][:3000]}"
        if action_id == "portas":
            r = ns.scan_ports(v["alvo"], v.get("portas", "comuns"))
            return _fmt_scan(r)
        if action_id == "porta_especifica":
            r = ns.check_single_port(v["alvo"], int(v["porta"]))
            return (f"{r['host']}:{r['port']} -> "
                    f"{'ABERTA' if r['open'] else 'fechada/filtrada'} "
                    f"({r['service']})" + (f"\nbanner: {r['banner']}"
                                           if r["banner"] else ""))
        if action_id == "portas_locais":
            return _fmt_listeners(ns.local_listeners())
        if action_id == "conexoes":
            return _fmt_conns(ns.active_connections())
        if action_id == "dns":
            return _fmt_dns(ns.dns_records(v["dominio"]))
        if action_id == "dns_reverso":
            r = ns.reverse_dns(v["ip"])
            return f"PTR de {r['ip']}: " + (", ".join(r["names"]) or "(nenhum)")
        if action_id == "whois":
            return _fmt_whois(ns.whois_query(v["dominio"]))
        if action_id == "http_headers":
            return _fmt_headers(ns.http_headers(v["url"]))
        if action_id == "ssl":
            return _fmt_tls(ns.tls_certificate(v["alvo"]))
        if action_id == "rede_local":
            return ("Tabela ARP da rede local (dispositivos que este PC ja "
                    f"falou):\n\n{ns.arp_table()['raw'][:3000]}")
        if action_id == "meu_ip":
            r = ns.public_ip()
            if "error" in r:
                return r["error"]
            g = r.get("geo", {})
            return (f"IP publico: {r['ip']}\nprovedor: {g.get('isp','?')} "
                    f"({g.get('asn','?')})\nlocal: {g.get('city','?')}, "
                    f"{g.get('country','?')}")
        if action_id == "geoip":
            g = ns.geoip(v["ip"])
            if "error" in g:
                return f"{v['ip']}: {g['error']}"
            return (f"{g['ip']}\npais: {g['country']}  regiao: {g['region']}  "
                    f"cidade: {g['city']}\nISP: {g['isp']}\norg: {g['org']}\n"
                    f"ASN: {g['asn']}")
        if action_id == "firewall":
            return f"Firewall do Windows:\n\n{ns.firewall_status()['raw'][:2500]}"
        if action_id == "latencia":
            alvos = ["1.1.1.1", "8.8.8.8"]
            linhas = []
            for a in alvos:
                r = ns.ping(a, count=6)
                linhas.append(f"{a}: perda {r.get('loss_pct') or '?'}% "
                              f"latencia {r.get('avg_ms') or '?'} ms")
            return "Qualidade da conexao:\n" + "\n".join(linhas)
        if action_id == "analise":
            return _full_analysis(ns, v["alvo"])
    except Exception as exc:  # noqa: BLE001 - vira contexto pro modelo
        return f"(a coleta falhou: {exc})"
    return "(acao sem coletor deterministico)"


def _fmt_scan(r: dict) -> str:
    head = f"Varredura de {r['host']}" + (f" ({r['ip']})" if r["ip"] else "")
    head += f" -- {r['checked']} portas checadas"
    if not r["open"]:
        return head + "\nNenhuma porta aberta nas checadas."
    lines = [head, "PORTAS ABERTAS:"]
    for p in r["open"]:
        risk = "  [!] arriscada se exposta na internet" if p["risky_if_public"] else ""
        banner = f"  banner: {p['banner']}" if p["banner"] else ""
        lines.append(f"  {p['port']}/tcp  {p['service']}{risk}{banner}")
    return "\n".join(lines)


def _fmt_listeners(r: dict) -> str:
    if "raw" in r:
        return "Portas em escuta (netstat):\n\n" + r["raw"][:3000]
    lines = ["Portas que ESTE PC esta escutando:"]
    for row in r["listeners"]:
        lines.append(f"  {row['addr']:<24} {row.get('process') or '?'} "
                     f"(pid {row.get('pid')})")
    return "\n".join(lines)


def _fmt_conns(r: dict) -> str:
    if "raw" in r:
        return "Conexoes ativas (netstat):\n\n" + r["raw"][:3000]
    lines = ["Conexoes de rede ativas:"]
    for row in r["connections"]:
        lines.append(f"  {row['local']:<22} -> {row['remote']:<22} "
                     f"{row.get('process') or '?'}")
    return "\n".join(lines)


def _fmt_dns(r: dict) -> str:
    if r.get("source") == "nslookup":
        return f"DNS de {r['name']} (nslookup):\n\n{r.get('raw','')[:2500]}"
    lines = [f"DNS de {r['name']}:"]
    for rtype in ("A", "AAAA", "CNAME", "MX", "NS", "TXT", "SOA"):
        vals = r.get(rtype) or []
        if vals:
            lines.append(f"  {rtype}: " + " ; ".join(vals[:8]))
    return "\n".join(lines)


def _fmt_whois(r: dict) -> str:
    if "error" in r:
        return f"WHOIS de {r['domain']}: {r['error']}"
    lines = [
        f"WHOIS de {r['domain']}  (servidores: {', '.join(r['servers'])})",
        f"  registrador: {r.get('registrar') or '?'}",
        f"  criado: {r.get('created') or '?'}",
        f"  expira: {r.get('expires') or '?'}",
    ]
    if r.get("name_servers"):
        lines.append("  name servers: " + ", ".join(r["name_servers"][:6]))
    lines.append("\n--- bruto ---\n" + r.get("raw", "")[:2000])
    return "\n".join(lines)


def _fmt_headers(r: dict) -> str:
    if "error" in r:
        return f"{r['url']}: {r['error']}"
    lines = [
        f"HTTP {r['status']}  {r['url']}",
        f"  servidor: {r.get('server') or '(oculto)'}",
    ]
    if r.get("powered_by"):
        lines.append(f"  x-powered-by: {r['powered_by']}")
    lines.append("  cabecalhos de seguranca PRESENTES: "
                 + (", ".join(r["security_headers_present"]) or "nenhum"))
    lines.append("  cabecalhos de seguranca FALTANDO: "
                 + (", ".join(r["security_headers_missing"]) or "nenhum"))
    return "\n".join(lines)


def _fmt_tls(r: dict) -> str:
    if "error" in r:
        return f"TLS {r['host']}:{r['port']}: {r['error']}"
    lines = [
        f"Certificado TLS de {r['host']}:{r['port']}",
        f"  emissor: {r.get('issuer') or '?'}",
        f"  para: {r.get('subject') or '?'}",
        f"  SAN: {', '.join(r.get('san') or []) or '?'}",
        f"  valido ate: {r.get('valid_until') or '?'}  "
        f"(faltam {r.get('days_left')} dias)",
        f"  cadeia confiavel: {r.get('trusted_chain')}",
        f"  protocolo: {r.get('protocol')}  cifra: {r.get('cipher')}",
    ]
    return "\n".join(lines)


def _full_analysis(ns, alvo: str) -> str:
    blocks = ["=== ANALISE DE " + alvo + " ==="]
    blocks.append(_fmt_scan(ns.scan_ports(alvo, "comuns")))
    try:
        blocks.append(_fmt_tls(ns.tls_certificate(alvo)))
    except Exception:  # noqa: BLE001
        pass
    try:
        blocks.append(_fmt_headers(ns.http_headers(alvo)))
    except Exception:  # noqa: BLE001
        pass
    try:
        dom = alvo if not alvo.replace(".", "").isdigit() else ""
        if dom:
            blocks.append(_fmt_dns(ns.dns_records(dom)))
    except Exception:  # noqa: BLE001
        pass
    return "\n\n".join(blocks)
