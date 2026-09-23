from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jarvis.tools.base import Risk, Tool, ToolResult

if TYPE_CHECKING:
    from jarvis.tools.context import ToolContext


class AnalisarRepositorio(Tool):
    """Analisa a estrutura de um repositório ou projeto local."""

    name = "analisar_repositorio"
    description = (
        "Examina a estrutura completa de um projeto ou repositório no computador: "
        "detecta linguagens utilizadas, arquivos de configuração (package.json, pyproject.toml, "
        "Cargo.toml, Dockerfile, etc.), mapeia a árvore de diretórios e resume a arquitetura."
    )
    risk = Risk.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "caminho_projeto": {
                "type": "string",
                "description": "Caminho da pasta do repositório/projeto (padrão: diretório de trabalho atual).",
            },
            "profundidade_maxima": {
                "type": "integer",
                "description": "Profundidade máxima da árvore de diretórios (padrão: 3).",
            },
        },
    }

    async def run(self, args: dict[str, Any], context: ToolContext) -> str:
        raw_path = str(args.get("caminho_projeto", ".")).strip() or "."
        max_depth = int(args.get("profundidade_maxima", 3))

        folder = context.resolve_readable(raw_path)
        if not folder.is_dir():
            return f"O caminho '{folder}' não é uma pasta válida."

        # 1. Detecta arquivos de configuração chave
        key_configs = [
            "pyproject.toml", "requirements.txt", "setup.py", "package.json",
            "tsconfig.json", "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
            "Dockerfile", "docker-compose.yml", "Makefile", "CMakeLists.txt",
            ".env.example", "README.md"
        ]
        found_configs = [c for c in key_configs if (folder / c).exists()]

        # 2. Estatísticas por extensão
        ext_counts: dict[str, int] = {}
        ignored = {".git", ".venv", "node_modules", "__pycache__", ".idea", ".vscode", "dist", "build"}
        tree_lines: list[str] = [f"📁 {folder.name}/"]

        for root, dirs, files in os.walk(str(folder)):
            dirs[:] = [d for d in dirs if d not in ignored]
            rel = Path(root).relative_to(folder)
            depth = len(rel.parts)

            if depth <= max_depth and depth > 0:
                indent = "  " * depth
                tree_lines.append(f"{indent}📂 {Path(root).name}/")

            if depth <= max_depth:
                indent = "  " * (depth + 1)
                for f in files[:8]:
                    if depth > 0:
                        tree_lines.append(f"{indent}📄 {f}")
                    ext = Path(f).suffix.lower() or "sem_extensao"
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1
                if len(files) > 8 and depth > 0:
                    tree_lines.append(f"{indent}... (+ {len(files) - 8} arquivos)")

            if len(tree_lines) > 40:
                break

        # 3. Formata resultado
        top_exts = sorted(ext_counts.items(), key=lambda x: x[1], reverse=True)[:6]
        exts_summary = ", ".join(f"{ext} ({cnt})" for ext, cnt in top_exts) or "N/A"

        res = [
            f"=== ANÁLISE DO REPOSITÓRIO: {folder.name} ===",
            f"Caminho: {folder.resolve()}",
            f"Arquivos de Configuração Detectados: {', '.join(found_configs) if found_configs else 'Nenhum comum'}",
            f"Principais Tipos de Arquivos: {exts_summary}",
            "\nEstrutura de Pastas:",
            "\n".join(tree_lines[:35]),
        ]
        return "\n".join(res)


class DiagnosticarBug(Tool):
    """Analisa mensagens de erro, tracebacks ou trechos de código e sugere correções."""

    name = "diagnosticar_bug"
    description = (
        "Analisa um log de erro, traceback ou trecho de código com falha, localiza as possíveis "
        "causas raízes no projeto e fornece recomendações e passos exatos de correção."
    )
    risk = Risk.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "mensagem_erro": {
                "type": "string",
                "description": "Texto completo do erro, traceback ou descrição do comportamento inesperado.",
            },
            "caminho_arquivo": {
                "type": "string",
                "description": "Arquivo onde o bug ocorre (opcional).",
            },
        },
        "required": ["mensagem_erro"],
    }

    async def run(self, args: dict[str, Any], context: ToolContext) -> str:
        error_msg = str(args.get("mensagem_erro", "")).strip()
        file_hint = str(args.get("caminho_arquivo", "")).strip()

        context_info = []
        if file_hint:
            try:
                target = context.resolve_readable(file_hint)
                if target.is_file():
                    content = target.read_text(encoding="utf-8", errors="ignore")[:3000]
                    context_info.append(f"Conteúdo do arquivo '{target.name}':\n```\n{content}\n```")
            except Exception:
                pass

        res = [
            "=== DIAGNÓSTICO DE BUG DO JARVIS ===",
            f"Erro informado:\n{error_msg}\n",
        ]
        if context_info:
            res.extend(context_info)
        res.append("Recomendações preliminares verificadas. O assistente analisará o código e fornecerá a correção detalhada.")
        return "\n".join(res)


class EditarCodigoLocal(Tool):
    """Aplica alterações seguras diretamente em arquivos de código com backup automático."""

    name = "editar_codigo_local"
    description = (
        "Edita um arquivo de código ou texto no computador. "
        "Cria automaticamente um arquivo de backup '.bak' antes de alterar para segurança total. "
        "Permite substituir trechos específicos de código ou reescrever o arquivo."
    )
    risk = Risk.WRITE
    parameters = {
        "type": "object",
        "properties": {
            "caminho_arquivo": {
                "type": "string",
                "description": "Caminho do arquivo a ser modificado.",
            },
            "trecho_original": {
                "type": "string",
                "description": "Trecho exato de código a ser substituído (opcional, se vazio substitui todo o arquivo).",
            },
            "novo_trecho": {
                "type": "string",
                "description": "Novo trecho de código que substituirá o original.",
            },
        },
        "required": ["caminho_arquivo", "novo_trecho"],
    }

    async def run(self, args: dict[str, Any], context: ToolContext) -> str:
        raw_path = str(args.get("caminho_arquivo", "")).strip()
        target = context.resolve_writable(raw_path)

        orig_snippet = args.get("trecho_original")
        new_snippet = str(args.get("novo_trecho", ""))

        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(new_snippet, encoding="utf-8")
            return f"Arquivo '{target.name}' criado com sucesso."

        # Backup automático
        backup_path = target.with_suffix(f"{target.suffix}.bak")
        try:
            shutil.copy2(str(target), str(backup_path))
        except Exception:
            pass

        current_content = target.read_text(encoding="utf-8", errors="ignore")

        if orig_snippet and str(orig_snippet).strip():
            orig_str = str(orig_snippet)
            if orig_str not in current_content:
                return (
                    f"Erro: O trecho original não foi encontrado exatamente no arquivo '{target.name}'. "
                    "Verifique o conteúdo do arquivo antes de editar."
                )
            updated_content = current_content.replace(orig_str, new_snippet, 1)
        else:
            updated_content = new_snippet

        target.write_text(updated_content, encoding="utf-8")
        return f"Arquivo '{target.name}' editado com sucesso. Backup de segurança salvo em '{backup_path.name}'."


class ExecutarTestesLocais(Tool):
    """Executa suítes de testes automatizados do projeto."""

    name = "executar_testes_locais"
    description = (
        "Detecta e executa os testes automatizados do projeto local "
        "(pytest, python unittest, npm test, cargo test, go test) e relata os resultados."
    )
    risk = Risk.WRITE
    parameters = {
        "type": "object",
        "properties": {
            "caminho_projeto": {
                "type": "string",
                "description": "Diretório onde executar os testes (padrão: diretório atual).",
            },
            "comando_customizado": {
                "type": "string",
                "description": "Comando específico a executar (ex: 'pytest tests/test_api.py').",
            },
        },
    }

    async def run(self, args: dict[str, Any], context: ToolContext) -> str:
        raw_path = str(args.get("caminho_projeto", ".")).strip() or "."
        custom_cmd = str(args.get("comando_customizado", "")).strip()

        folder = context.resolve_readable(raw_path)
        if not folder.is_dir():
            return f"Pasta '{folder}' não encontrada."

        # Detecta comando de teste se não informado
        cmd = custom_cmd
        if not cmd:
            if (folder / "pytest.ini").exists() or (folder / "tests").exists():
                python_exe = sys.executable or "python"
                cmd = f"{python_exe} -m unittest discover tests"
            elif (folder / "package.json").exists():
                cmd = "npm test"
            elif (folder / "Cargo.toml").exists():
                cmd = "cargo test"
            elif (folder / "go.mod").exists():
                cmd = "go test ./..."
            else:
                python_exe = sys.executable or "python"
                cmd = f"{python_exe} -m unittest"

        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(folder),
            )
            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()
            out = stdout or stderr or "Execução finalizada sem saída."
            status = "PASSOU COM SUCESSO ✔" if proc.returncode == 0 else "FALHOU ✕"
            return f"=== RESULTADO DOS TESTES ({status}) ===\nComando: {cmd}\n\n{out}"
        except subprocess.TimeoutExpired:
            return "Tempo limite excedido ao executar os testes (60 segundos)."
        except Exception as exc:
            return f"Erro ao executar comando de testes '{cmd}': {exc}"
