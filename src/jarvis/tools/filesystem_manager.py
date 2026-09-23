from __future__ import annotations

import datetime
import os
import shutil
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jarvis.tools.base import Risk, Tool, ToolResult

if TYPE_CHECKING:
    from jarvis.tools.context import ToolContext

EXT_CATEGORIES: dict[str, str] = {
    # Imagens
    ".png": "Imagens", ".jpg": "Imagens", ".jpeg": "Imagens", ".gif": "Imagens",
    ".bmp": "Imagens", ".svg": "Imagens", ".webp": "Imagens", ".ico": "Imagens",
    # Documentos
    ".pdf": "Documentos", ".docx": "Documentos", ".doc": "Documentos", ".xlsx": "Documentos",
    ".xls": "Documentos", ".pptx": "Documentos", ".txt": "Documentos", ".csv": "Documentos",
    ".md": "Documentos", ".epub": "Documentos", ".odt": "Documentos",
    # Vídeos
    ".mp4": "Videos", ".mkv": "Videos", ".avi": "Videos", ".mov": "Videos",
    ".wmv": "Videos", ".flv": "Videos", ".webm": "Videos",
    # Músicas & Áudios
    ".mp3": "Musicas", ".wav": "Musicas", ".flac": "Musicas", ".aac": "Musicas",
    ".ogg": "Musicas", ".m4a": "Musicas",
    # Compactados
    ".zip": "Compactados", ".rar": "Compactados", ".7z": "Compactados",
    ".tar": "Compactados", ".gz": "Compactados",
    # Instaladores & Programas
    ".exe": "Programas", ".msi": "Programas", ".apk": "Programas",
    # Códigos & Desenvolvimento
    ".py": "Codigos", ".js": "Codigos", ".ts": "Codigos", ".html": "Codigos",
    ".css": "Codigos", ".qml": "Codigos", ".cpp": "Codigos", ".c": "Codigos",
    ".h": "Codigos", ".java": "Codigos", ".json": "Codigos", ".yml": "Codigos",
    ".yaml": "Codigos", ".sql": "Codigos", ".rs": "Codigos", ".go": "Codigos",
}


class OrganizarPasta(Tool):
    """Organiza os arquivos de uma pasta em subpastas por tipo ou por data."""

    name = "organizar_pasta"
    description = (
        "Organiza automaticamente os arquivos de uma pasta movendo-os para subpastas "
        "categorizadas por tipo (Imagens, Documentos, Vídeos, Músicas, Compactados, Códigos, Programas) "
        "ou por data (ano/mês). Use quando o usuário pedir 'organize minha pasta de downloads', "
        "'arrume meus arquivos', etc."
    )
    risk = Risk.WRITE
    parameters = {
        "type": "object",
        "properties": {
            "caminho_pasta": {
                "type": "string",
                "description": "Caminho da pasta a organizar (ex: 'C:/Users/.../Downloads', 'D:/Projetos', ou nome de pasta).",
            },
            "modo": {
                "type": "string",
                "enum": ["categoria", "data"],
                "description": "Modo de organização: 'categoria' (por tipo de arquivo) ou 'data' (por ano/mês de modificação). Padrão: 'categoria'.",
            },
        },
        "required": ["caminho_pasta"],
    }

    async def run(self, args: dict[str, Any], context: ToolContext) -> str:
        raw_path = str(args.get("caminho_pasta", "")).strip()
        modo = str(args.get("modo", "categoria")).strip().lower()

        folder = context.resolve_writable(raw_path)
        if not folder.is_dir():
            return f"O caminho '{folder}' não é uma pasta válida."

        moved_count = 0
        details: list[str] = []

        for item in list(folder.iterdir()):
            if item.is_dir() or item.name.startswith("."):
                continue

            target_subfolder = "Outros"
            if modo == "data":
                mtime = datetime.datetime.fromtimestamp(item.stat().st_mtime)
                target_subfolder = mtime.strftime("%Y-%m")
            else:
                ext = item.suffix.lower()
                target_subfolder = EXT_CATEGORIES.get(ext, "Outros")

            dest_dir = folder / target_subfolder
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file = dest_dir / item.name

            # Evita sobrescrever arquivos com o mesmo nome
            if dest_file.exists() and dest_file != item:
                stem = item.stem
                ext = item.suffix
                dest_file = dest_dir / f"{stem}_{int(datetime.datetime.now().timestamp())}{ext}"

            try:
                shutil.move(str(item), str(dest_file))
                moved_count += 1
                details.append(f"- {item.name} -> {target_subfolder}/")
            except Exception as exc:
                details.append(f"- Erro ao mover {item.name}: {exc}")

        if moved_count == 0:
            return f"A pasta '{folder.name}' não possui arquivos soltos para organizar."

        res = [f"Sucesso: {moved_count} arquivo(s) organizado(s) em '{folder.name}':"]
        res.extend(details[:15])
        if len(details) > 15:
            res.append(f"... e mais {len(details) - 15} arquivos.")
        return "\n".join(res)


class PesquisarArquivosInteligente(Tool):
    """Busca avançada de arquivos com múltiplos critérios combinados."""

    name = "pesquisar_arquivos_inteligente"
    description = (
        "Pesquisa arquivos em uma pasta usando filtros flexíveis: "
        "termo no nome, extensões permitidas, tamanho mínimo/máximo em MB, dias de modificação recente, "
        "ou texto contido dentro dos arquivos."
    )
    risk = Risk.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "caminho_pasta": {
                "type": "string",
                "description": "Pasta inicial onde pesquisar (padrão: diretório atual do usuário).",
            },
            "termo_nome": {
                "type": "string",
                "description": "Texto ou padrão no nome do arquivo (ex: 'relatorio', 'foto', 'projeto').",
            },
            "extensoes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Lista de extensões a filtrar (ex: ['.pdf', '.docx', '.png']).",
            },
            "tamanho_min_mb": {
                "type": "number",
                "description": "Tamanho mínimo do arquivo em Megabytes (MB).",
            },
            "tamanho_max_mb": {
                "type": "number",
                "description": "Tamanho máximo do arquivo em Megabytes (MB).",
            },
            "modificado_ultimos_dias": {
                "type": "integer",
                "description": "Filtrar apenas arquivos modificados nos últimos N dias.",
            },
            "texto_conteudo": {
                "type": "string",
                "description": "Texto a buscar dentro do conteúdo de arquivos de texto/código.",
            },
        },
    }

    async def run(self, args: dict[str, Any], context: ToolContext) -> str:
        raw_path = str(args.get("caminho_pasta", ".")).strip() or "."
        folder = context.resolve_readable(raw_path)
        if not folder.is_dir():
            return f"A pasta '{folder}' não foi encontrada."

        name_term = str(args.get("termo_nome", "")).strip().lower()
        exts = [e.lower() if e.startswith(".") else f".{e.lower()}" for e in args.get("extensoes") or []]
        min_mb = float(args.get("tamanho_min_mb", 0.0))
        max_mb = float(args.get("tamanho_max_mb", 999999.0))
        days = args.get("modificado_ultimos_dias")
        content_term = str(args.get("texto_conteudo", "")).strip().lower()

        now = datetime.datetime.now().timestamp()
        found: list[dict[str, Any]] = []

        for root, _, files in os.walk(str(folder)):
            for f in files:
                fpath = Path(root) / f
                # Filtro por nome
                if name_term and name_term not in f.lower():
                    continue
                # Filtro por extensão
                if exts and fpath.suffix.lower() not in exts:
                    continue
                # Filtro por tamanho
                try:
                    stat = fpath.stat()
                    size_mb = stat.st_size / (1024 * 1024)
                    if size_mb < min_mb or size_mb > max_mb:
                        continue
                    # Filtro por data
                    if days is not None:
                        age_days = (now - stat.st_mtime) / (24 * 3600)
                        if age_days > int(days):
                            continue
                except OSError:
                    continue

                # Filtro por conteúdo
                if content_term:
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as file_handle:
                            text_head = file_handle.read(100000)
                            if content_term not in text_head.lower():
                                continue
                    except Exception:
                        continue

                found.append({
                    "path": str(fpath),
                    "name": f,
                    "size_mb": size_mb,
                    "mtime": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M"),
                })
                if len(found) >= 30:
                    break
            if len(found) >= 30:
                break

        if not found:
            return f"Nenhum arquivo encontrado com os filtros informados na pasta '{folder.name}'."

        lines = [f"Encontrados {len(found)} arquivo(s):"]
        for item in found:
            lines.append(f"- {item['name']} ({item['size_mb']:.2f} MB | {item['mtime']}) -> {item['path']}")
        return "\n".join(lines)


class CompactarDescompactar(Tool):
    """Compacta ou descompacta arquivos e pastas em formato ZIP."""

    name = "compactar_descompactar"
    description = (
        "Compacta arquivos/pastas em um arquivo .zip ou extrai o conteúdo de um arquivo .zip."
    )
    risk = Risk.WRITE
    parameters = {
        "type": "object",
        "properties": {
            "acao": {
                "type": "string",
                "enum": ["compactar", "descompactar"],
                "description": "'compactar' para criar arquivo .zip ou 'descompactar' para extrair.",
            },
            "origem": {
                "type": "string",
                "description": "Arquivo ou pasta de origem a compactar ou arquivo .zip a extrair.",
            },
            "destino": {
                "type": "string",
                "description": "Caminho do arquivo .zip resultante (ao compactar) ou pasta de destino (ao descompactar).",
            },
        },
        "required": ["acao", "origem"],
    }

    async def run(self, args: dict[str, Any], context: ToolContext) -> str:
        acao = str(args.get("acao", "")).strip().lower()
        origem = context.resolve_writable(str(args.get("origem", "")).strip())

        if not origem.exists():
            return f"Origem '{origem}' não encontrada."

        if acao == "compactar":
            dest_raw = str(args.get("destino", "")).strip()
            if not dest_raw:
                dest_zip = origem.with_suffix(".zip") if origem.is_file() else origem.parent / f"{origem.name}.zip"
            else:
                dest_zip = context.resolve_writable(dest_raw)
                if not str(dest_zip).endswith(".zip"):
                    dest_zip = dest_zip.with_suffix(".zip")

            with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                if origem.is_file():
                    zf.write(origem, arcname=origem.name)
                else:
                    for root, _, files in os.walk(str(origem)):
                        for f in files:
                            full = Path(root) / f
                            rel = full.relative_to(origem)
                            zf.write(full, arcname=str(rel))

            return f"Arquivo compactado com sucesso em: {dest_zip}"

        elif acao == "descompactar":
            if not origem.is_file() or not zipfile.is_zipfile(origem):
                return f"'{origem.name}' não é um arquivo .zip válido."

            dest_raw = str(args.get("destino", "")).strip()
            dest_dir = context.resolve_writable(dest_raw) if dest_raw else origem.parent / origem.stem
            dest_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(origem, "r") as zf:
                zf.extractall(dest_dir)

            return f"Arquivo '{origem.name}' extraído com sucesso na pasta: {dest_dir}"

        return f"Ação '{acao}' não suportada. Use 'compactar' ou 'descompactar'."


class RenomearArquivosLote(Tool):
    """Renomeia múltiplos arquivos em uma pasta seguindo regras de prefixo, sufixo ou substituição."""

    name = "renomear_arquivos_lote"
    description = (
        "Renomeia arquivos em lote dentro de uma pasta: "
        "adicionar prefixo, sufixo, numerar sequencialmente ou substituir termos no nome."
    )
    risk = Risk.WRITE
    parameters = {
        "type": "object",
        "properties": {
            "caminho_pasta": {
                "type": "string",
                "description": "Pasta onde estão os arquivos a renomear.",
            },
            "filtro_extensao": {
                "type": "string",
                "description": "Extensão a filtrar (ex: '.png', '.pdf') ou vazio para todos.",
            },
            "prefixo": {
                "type": "string",
                "description": "Texto a adicionar no início do nome.",
            },
            "sufixo": {
                "type": "string",
                "description": "Texto a adicionar no final do nome (antes da extensão).",
            },
            "substituir_de": {
                "type": "string",
                "description": "Texto a ser procurado e substituído.",
            },
            "substituir_para": {
                "type": "string",
                "description": "Novo texto que substituirá o termo procurado.",
            },
            "numerar_sequencial": {
                "type": "boolean",
                "description": "Se verdadeiro, adiciona numeração sequencial (ex: Foto_01, Foto_02).",
            },
        },
        "required": ["caminho_pasta"],
    }

    async def run(self, args: dict[str, Any], context: ToolContext) -> str:
        raw_path = str(args.get("caminho_pasta", "")).strip()
        folder = context.resolve_writable(raw_path)
        if not folder.is_dir():
            return f"A pasta '{folder}' não foi encontrada."

        ext_filter = str(args.get("filtro_extensao", "")).strip().lower()
        if ext_filter and not ext_filter.startswith("."):
            ext_filter = f".{ext_filter}"

        prefix = str(args.get("prefixo", ""))
        suffix = str(args.get("sufixo", ""))
        sub_de = str(args.get("substituir_de", ""))
        sub_para = str(args.get("substituir_para", ""))
        numerar = bool(args.get("numerar_sequencial", False))

        renamed = 0
        details: list[str] = []

        files = [f for f in sorted(folder.iterdir()) if f.is_file() and not f.name.startswith(".")]
        if ext_filter:
            files = [f for f in files if f.suffix.lower() == ext_filter]

        for i, item in enumerate(files, start=1):
            stem = item.stem
            ext = item.suffix

            if sub_de:
                stem = stem.replace(sub_de, sub_para)
            if numerar:
                stem = f"{stem}_{i:02d}"
            if prefix:
                stem = f"{prefix}{stem}"
            if suffix:
                stem = f"{stem}{suffix}"

            new_name = f"{stem}{ext}"
            new_path = folder / new_name

            if new_path != item and not new_path.exists():
                try:
                    item.rename(new_path)
                    renamed += 1
                    details.append(f"- {item.name} -> {new_name}")
                except Exception as exc:
                    details.append(f"- Erro em {item.name}: {exc}")

        if renamed == 0:
            return "Nenhum arquivo precisou ser renomeado."

        res = [f"Sucesso: {renamed} arquivo(s) renomeado(s):"]
        res.extend(details[:15])
        return "\n".join(res)
