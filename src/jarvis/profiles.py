"""Perfis de uso do assistente.

Um perfil e um preset que liga/desliga um conjunto de permissões do agente e
troca a "persona" (trecho do prompt do sistema). O usuário alterna pelo seletor
no topo do chat. Adicionar um perfil novo = so acrescentar em PROFILES.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class UsageProfile:
    id: str
    name: str
    icon: str
    tagline: str
    description: str
    persona: str
    # permissões do agente aplicadas ao escolher o perfil
    agent_enabled: bool = True
    filesystem_read: bool = True
    filesystem_write: bool = False
    shell: bool = False
    browser: bool = True
    ssh: bool = False  # ferramentas executar_no_servidor / listar_servidores
    needs_folder: bool = False  # exige escolher uma pasta de trabalho
    capabilities: tuple[str, ...] = field(default_factory=tuple)

    def permission_prefs(self, *, folder: str = "") -> dict[str, object]:
        prefs: dict[str, object] = {
            "agent_enabled": self.agent_enabled,
            "agent_fs_read": self.filesystem_read,
            "agent_fs_write": self.filesystem_write,
            "agent_shell": self.shell,
            "agent_browser": self.browser,
            "agent_ssh": self.ssh,
        }
        if self.needs_folder:
            prefs["agent_allowed_roots"] = [folder] if folder else []
        else:
            prefs["agent_allowed_roots"] = []
        return prefs

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "tagline": self.tagline,
            "description": self.description,
            "needsFolder": self.needs_folder,
            "capabilities": list(self.capabilities),
        }


_NORMAL = UsageProfile(
    id="normal",
    name="Uso normal",
    icon="🏠",
    tagline="Dia a dia, uso continuo",
    description=(
        "Assistente pessoal para o cotidiano: responder perguntas, pesquisar na "
        "web, agenda, contatos, ler arquivos e enxergar pela webcam. Não altera "
        "arquivos nem roda comandos."
    ),
    persona=(
        "MODO: Uso normal. Você e o assistente do dia a dia do usuário. Seja "
        "rápido, direto e proativo. Pode pesquisar na web, consultar a agenda e "
        "os contatos, ler arquivos e abrir sites. NÃO altera arquivos, NÃO roda "
        "comandos de sistema. Se a tarefa exigir isso, sugira trocar para o "
        "perfil 'Desenvolvimento'."
    ),
    filesystem_write=False,
    shell=False,
    browser=True,
    capabilities=(
        "Pesquisa na web e leitura de páginas",
        "Agenda, compromissos e contatos",
        "Leitura de arquivos e pastas",
        "Visão pela webcam / captura de tela",
    ),
)

_SECURITY = UsageProfile(
    id="seguranca",
    name="Cibersegurança",
    icon="🛡️",
    tagline="Pesquisa e testes autorizados",
    description=(
        "Apoio a pesquisa e testes de segurança AUTORIZADOS (seu ambiente, "
        "laboratório, CTF, estudo): reconhecimento e varredura de portas, "
        "análise de rede e de logs, ferramentas de linha de comando, OSINT. "
        "Consulta os servidores cadastrados para pegar o IP, mas NÃO abre "
        "shell remoto (pra isso, use Desenvolvimento)."
    ),
    persona=(
        "MODO: Ciberseguranca. O usuário faz pesquisa e testes de segurança "
        "AUTORIZADOS - no próprio ambiente, em laboratório, CTF ou para estudo. "
        "Ajude com: reconhecimento e enumeração, VARREDURA DE PORTAS e detecção "
        "de serviços, análise de trafego e de logs, leitura e explicação de "
        "código/vulnerabilidades, hardening e defesa, OSINT em fontes públicas. "
        "Para recon de rede use SEMPRE as ferramentas 'recon_rede' (ping, "
        "traceroute, portas, dns, whois, tls, http, geoip...) e 'inspecao_local' "
        "(portas em escuta, conexões, firewall) - elas já vêm prontas, em Python "
        "puro, NÃO precisa de nmap/whois/openssl nem instalar nada. Para mirar um "
        "servidor do usuário, chame 'listar_servidores' primeiro para pegar o IP. "
        "Só caia no shell ('executar_comando') se a ferramenta não cobrir o caso. "
        "Voce NÃO tem shell remoto ('executar_no_servidor' não existe aqui) - se "
        "o usuário quiser rodar algo DENTRO da VPS, peça para trocar para o "
        "perfil 'Desenvolvimento'. "
        "NÃO ajude com: ataque a alvos de terceiros sem autorização, negação de "
        "serviço, malware ofensivo, coleta de credenciais para uso malicioso, "
        "evasão de detecção com fim malicioso."
    ),
    filesystem_write=False,
    shell=True,
    browser=True,
    capabilities=(
        "Varredura de portas e recon (Test-NetConnection, nmap, nslookup...)",
        "Consulta os servidores cadastrados para pegar o IP",
        "Pesquisa na web e OSINT em fontes públicas",
        "Sem shell remoto e sem escrita em disco",
    ),
)

_DEV = UsageProfile(
    id="desenvolvimento",
    name="Desenvolvimento",
    icon="💻",
    tagline="Criar sites, apps e sistemas",
    description=(
        "Para construir software. Você escolhe uma pasta de trabalho e o agente "
        "ganha permissão TOTAL dentro dela: criar, editar, mover e apagar "
        "arquivos, rodar comandos (build, testes, git, gerenciadores de pacote). "
        "Fora dessa pasta, nada e alterado."
    ),
    persona=(
        "MODO: Desenvolvimento. O usuário esta construindo software (sites, "
        "apps, sistemas) na pasta de trabalho: {folder}. Você tem permissão "
        "TOTAL dentro dessa pasta - criar, editar, mover e apagar arquivos e "
        "rodar comandos (build, testes, git, npm/pip/etc.). Trabalhe como um "
        "engenheiro cuidadoso: leia o código existente antes de mudar, siga o "
        "estilo do projeto, rode os testes depois de alterar, faca commits "
        "claros. NUNCA escreva ou apague nada fora da pasta de trabalho. "
        "Para acessar um servidor remoto (VPS) use SEMPRE a ferramenta "
        "'executar_no_servidor' (o cliente SSH ja vem pronto em tools/ssh) - "
        "NUNCA rode 'ssh'/'scp' pelo shell nem instale putty, plink ou "
        "OpenSSH. Se nao houver servidor cadastrado, peca ao usuário para "
        "cadastrar em Configurações > Permissões > Servidores."
    ),
    filesystem_write=True,
    shell=True,
    browser=True,
    ssh=True,
    needs_folder=True,
    capabilities=(
        "Criar, editar, mover e apagar arquivos na pasta escolhida",
        "Rodar comandos: build, testes, git, npm/pip...",
        "Acesso SSH a servidores cadastrados (cliente embutido)",
        "Pesquisa na web e leitura de documentação",
        "Restrito a pasta de trabalho",
    ),
)

PROFILES: dict[str, UsageProfile] = {
    _NORMAL.id: _NORMAL,
    _SECURITY.id: _SECURITY,
    _DEV.id: _DEV,
}
DEFAULT_PROFILE = _NORMAL.id
ORDER = (_NORMAL.id, _SECURITY.id, _DEV.id)


def get_profile(profile_id: str) -> UsageProfile:
    return PROFILES.get((profile_id or "").strip(), PROFILES[DEFAULT_PROFILE])


def profile_choices() -> list[dict[str, object]]:
    return [PROFILES[pid].as_dict() for pid in ORDER]


def compose_system_prompt(
    base_prompt: str, profile: UsageProfile, *, folder: str = ""
) -> str:
    """Junta o prompt base do config com a persona do perfil ativo."""
    persona = profile.persona.replace("{folder}", folder or "(nenhuma pasta escolhida)")
    return f"{base_prompt.strip()}\n\n{persona}"
