from __future__ import annotations

from jarvis.config import AgentConfig
from jarvis.tools.agenda import (
    BuscarContato,
    ConsultarAgenda,
    SalvarCompromisso,
    SalvarContato,
)
from jarvis.tools.base import Tool
from jarvis.tools.filesystem import (
    AbrirPasta,
    AnexarArquivo,
    Apagar,
    BuscarArquivos,
    CriarPasta,
    EscreverArquivo,
    LerArquivo,
    ListarPasta,
    Mover,
    ProcurarTexto,
)
from jarvis.tools.browser import AbrirSite, GerenciarGuiasNavegador, PesquisarWeb
from jarvis.tools.calc import Calculadora
from jarvis.tools.code_assistant import (
    AnalisarRepositorio,
    DiagnosticarBug,
    EditarCodigoLocal,
    ExecutarTestesLocais,
)
from jarvis.tools.code_interpreter import InterpretadorCodigo
from jarvis.tools.filesystem_manager import (
    CompactarDescompactar,
    OrganizarPasta,
    PesquisarArquivosInteligente,
    RenomearArquivosLote,
)
from jarvis.tools.health import (
    BuscarCID,
    CalculadoraClinica,
    InteracoesMedicamentosas,
)
from jarvis.tools.media_control import (
    AjustarVolume,
    ControleReproducao,
    TocarMusicaOuVideo,
)
from jarvis.tools.memory_recall import (
    ConsultarHistoricoConversas,
    ConsultarMemoriaLongoPrazo,
)
from jarvis.tools.netsec_tools import InspecaoLocal, ReconRede
from jarvis.tools.screen_reader import LerEAnalisarTela
from jarvis.tools.shell import ExecutarComando
from jarvis.tools.ssh_tool import ExecutarNoServidor, ListarServidores
from jarvis.tools.system_control import (
    AbrirAplicativo,
    ControleConfiguracoesSistema,
    GerenciarJanelas,
)
from jarvis.tools.vision import TirarPrint, VerPelaWebcam
from jarvis.tools.web import BuscarNaWeb, LerPaginaWeb


def build_tools(config: AgentConfig, *, vision_enabled: bool = False) -> list[Tool]:
    """Monta a lista de ferramentas conforme as permissões ligadas."""
    tools: list[Tool] = [
        Calculadora(),
        ConsultarAgenda(),
        SalvarCompromisso(),
        BuscarContato(),
        SalvarContato(),
        # Lembrança Perfeita & Recall
        ConsultarHistoricoConversas(),
        ConsultarMemoriaLongoPrazo(),
        # Comandos do Sistema
        AbrirAplicativo(),
        GerenciarJanelas(),
        ControleConfiguracoesSistema(),
        # Controle de Mídia
        ControleReproducao(),
        AjustarVolume(),
        TocarMusicaOuVideo(),
        # Setor Saúde: conhecimento clínico offline (base PROMEDIS)
        InteracoesMedicamentosas(),
        BuscarCID(),
        CalculadoraClinica(),
        # Gerenciamento de Arquivos em Linguagem Natural
        OrganizarPasta(),
        PesquisarArquivosInteligente(),
        CompactarDescompactar(),
        RenomearArquivosLote(),
        # Leitura e Análise da Tela
        LerEAnalisarTela(),
        # Interpretador de Código
        InterpretadorCodigo(),
        # Assistente de Código Local
        AnalisarRepositorio(),
        DiagnosticarBug(),
        EditarCodigoLocal(),
        ExecutarTestesLocais(),
    ]
    if vision_enabled:
        tools.append(VerPelaWebcam())
        tools.append(TirarPrint())
    if config.filesystem_read:
        tools += [
            ListarPasta(),
            LerArquivo(),
            BuscarArquivos(),
            ProcurarTexto(),
            AbrirPasta(),
        ]
    if config.filesystem_write:
        tools += [
            EscreverArquivo(),
            AnexarArquivo(),
            CriarPasta(),
            Mover(),
            Apagar(),
        ]
    if config.shell:
        tools.append(ExecutarComando())
        # recon de rede em Python puro -- perfis com shell (Ciberseguranca/Dev)
        tools += [ReconRede(), InspecaoLocal()]
    if config.browser:
        tools += [
            AbrirSite(),
            PesquisarWeb(),
            GerenciarGuiasNavegador(),
            BuscarNaWeb(),
            LerPaginaWeb(),
        ]
    ssh_on = getattr(config, "ssh", False)
    # so-leitura: consultar os servidores cadastrados (pegar host/IP para recon).
    # Disponivel sempre que ha shell ou SSH -- e util no perfil Ciberseguranca.
    if ssh_on or config.shell:
        tools.append(ListarServidores())
    # shell remoto de verdade: so com a permissao SSH ligada.
    if ssh_on:
        tools.append(ExecutarNoServidor())
    return tools
