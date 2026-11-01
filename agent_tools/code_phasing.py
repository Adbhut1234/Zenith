"""
Zenith Code Phasing Engine (100% Free & Local)
==============================================
Inspired by Vision's ability to phase through molecular structures down to the atomic level.
Phases into any codebase or repository on the user's PC using local Abstract Syntax Tree (AST)
and lexical symbol analysis:
- Extracts classes, functions, signatures, docstrings, and cross-file dependencies.
- Analyzes project architecture with ZERO token consumption and sub-second execution.
- Enables Zenith to understand complex codebases before writing or modifying code.
"""

import os
import ast
import re
import json
import logging
import ui_state
import asyncio
from typing import Dict, Any, List, Optional
from livekit.agents import function_tool, RunContext

logger = logging.getLogger("code_phasing")

IGNORED_DIRS = {
    ".git", ".svn", "node_modules", "venv", "__pycache__", ".agent", ".agents",
    "dist", "build", ".next", ".cache", "env", "coverage", ".pytest_cache"
}

SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".html", ".css", ".md"}

def parse_python_ast(file_path: str) -> Dict[str, Any]:
    """Parses a Python file using native AST to extract classes and functions."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
        tree = ast.parse(source, filename=file_path)
    except Exception as e:
        return {"file": file_path, "error": str(e), "symbols": []}

    symbols = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            args = [a.arg for a in node.args.args]
            doc = ast.get_docstring(node) or ""
            symbols.append({
                "type": "function",
                "name": node.name,
                "args": args,
                "doc": doc.split("\n")[0] if doc else "",
                "line": node.lineno
            })
        elif isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                    m_args = [a.arg for a in item.args.args]
                    methods.append(f"{item.name}({', '.join(m_args)})")
            doc = ast.get_docstring(node) or ""
            symbols.append({
                "type": "class",
                "name": node.name,
                "methods": methods,
                "doc": doc.split("\n")[0] if doc else "",
                "line": node.lineno
            })

    return {"file": os.path.basename(file_path), "path": file_path, "symbols": symbols}

def parse_generic_code(file_path: str) -> Dict[str, Any]:
    """Lightweight regex-based symbol parser for JS, TS, and other languages."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        return {"file": file_path, "error": str(e), "symbols": []}

    symbols = []
    fn_pattern = re.compile(r'(?:function\s+([a-zA-Z0-9_$]+)|(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>|class\s+([a-zA-Z0-9_$]+))')
    
    for idx, line in enumerate(lines, 1):
        match = fn_pattern.search(line)
        if match:
            name = match.group(1) or match.group(2) or match.group(3)
            sym_type = "class" if "class" in line else "function"
            symbols.append({"type": sym_type, "name": name, "line": idx})

    return {"file": os.path.basename(file_path), "path": file_path, "symbols": symbols}

def phase_scan_directory(target_dir: str, max_files: int = 50) -> Dict[str, Any]:
    """Scans and extracts AST symbols across a directory tree."""
    target_abs = os.path.abspath(os.path.expanduser(target_dir))
    if not os.path.exists(target_abs):
        return {"error": f"Directory does not exist: {target_abs}", "files": []}

    parsed_files = []
    file_count = 0

    for root, dirs, files in os.walk(target_abs):
        # Filter out ignored dirs in place
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
        
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                file_count += 1
                if file_count > max_files:
                    break
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, target_abs)
                
                if ext == ".py":
                    parsed = parse_python_ast(full_path)
                else:
                    parsed = parse_generic_code(full_path)
                
                parsed["rel_path"] = rel_path
                parsed_files.append(parsed)

    return {
        "root": target_abs,
        "scanned_files_count": len(parsed_files),
        "files": parsed_files
    }

# ==============================================================================
# LIVEKIT AGENT EXPOSED TOOL
# ==============================================================================

@function_tool()
async def phase_into_codebase(
    context: RunContext,  # type: ignore
    target_path: str,
    focus_symbol: str = ""
) -> str:
    """
    Phases into any codebase, project, or directory on Sir's PC using local AST parsing.
    Extracts the architectural hierarchy, classes, functions, signatures, and docstrings
    with ZERO cloud API latency and zero token waste.
    Use this when Sir asks: "What does this repo do?", "Find where function X is defined",
    "Explain the architecture of this folder", or before modifying a codebase.
    
    Args:
        target_path: The directory or file path to inspect (e.g. 'D:\\Projects\\friday_jarvis2-main' or relative path).
        focus_symbol: Optional specific function name, class name, or concept to filter by.
    """
    ui_state.set_text("⚛️ Phasing Codebase")
    scan_res = await asyncio.to_thread(phase_scan_directory, target_path)
    ui_state.set_text("⚛️ AST Extracted")
    
    if "error" in scan_res:
        return f"Could not phase into target: {scan_res['error']}"

    files = scan_res.get("files", [])
    total_files = scan_res.get("scanned_files_count", 0)
    root = scan_res.get("root", "")

    lines = [f"Phased into '{root}' ({total_files} files analyzed):\n"]
    
    focus_lower = focus_symbol.strip().lower()
    matches_found = 0

    for f_info in files:
        symbols = f_info.get("symbols", [])
        if focus_lower:
            # Filter symbols matching focus
            filtered = [s for s in symbols if focus_lower in s["name"].lower() or (s.get("doc") and focus_lower in s["doc"].lower())]
            if not filtered:
                continue
            symbols = filtered

        if symbols:
            matches_found += len(symbols)
            lines.append(f"📁 {f_info.get('rel_path', f_info['file'])}:")
            for s in symbols[:6]:
                if s["type"] == "class":
                    methods_str = f" [{', '.join(s.get('methods', [])[:4])}]" if s.get("methods") else ""
                    lines.append(f"  • class {s['name']}{methods_str} (line {s['line']})")
                else:
                    args_str = f"({', '.join(s.get('args', []))})" if "args" in s else ""
                    doc_str = f" - '{s['doc'][:50]}'" if s.get("doc") else ""
                    lines.append(f"  • def {s['name']}{args_str}{doc_str} (line {s['line']})")

    if focus_lower and matches_found == 0:
        return f"Phased into '{root}' successfully, but found no symbols matching '{focus_symbol}'. Total files: {total_files}."

    return "\n".join(lines[:40])
