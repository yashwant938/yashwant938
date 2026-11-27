#!/usr/bin/env python3
"""Interactive GitHub-Issue Sandbox runner for ArchGuard MCP & Clang++ -O0/-O2 diffs.

Security invariants:
- Never executes user code; Clang mode runs strictly `clang++ -S` (assembly only) with
  header allowlisting, directive filtering, input size caps, and a hard subprocess timeout.
- ArchGuard mode calls the hosted Streamable HTTP MCP endpoint over HTTPS JSON-RPC 2.0,
  with a deterministic offline Python fallback if the remote worker is unreachable.
"""

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request
from xml.sax.saxutils import escape


ARCHGUARD_MCP_URL = 'https://arch-guard-mcp.yashwant938.workers.dev/mcp'
MAX_PAYLOAD_CHARS = 3500
MAX_CPP_CHARS = 2500
MAX_CPP_LINES = 80

ALLOWED_CPP_HEADERS = frozenset({
    'cstdint', 'cstddef', 'algorithm', 'array', 'numeric', 'cmath',
    'bit', 'type_traits', 'limits', 'tuple', 'utility', 'concepts', 'span',
})

FORBIDDEN_CPP_PATTERNS = (
    re.compile(r'^\s*#\s*include\s*"', re.MULTILINE),
    re.compile(r'^\s*#\s*include\s*<[^>]*(\.\.|/|\\)', re.MULTILINE),
    re.compile(r'^\s*#\s*(embed|pragma|line)\b', re.MULTILINE),
    re.compile(r'\b(__asm__|__asm|asm)\b'),
    re.compile(r'\b(system|popen|execve|execvp|fork)\s*\('),
)


@dataclass(frozen=True)
class SandboxResult:
    mode: str          # 'ARCHGUARD_SQL' | 'ARCHGUARD_GRAPH' | 'CLANG_DIFF'
    badge_label: str   # e.g. 'ARCHGUARD MCP · SQL'
    accent: str        # hex accent color
    author: str
    issue_number: int
    ran_at: datetime
    headline: str      # concise primary result
    metric_pill: str   # e.g. 'BLOCK_DEPLOY · 2 CRITICAL' or '-88% OPS (25 → 3)'
    preview_lines: tuple[str, ...]
    comment_markdown: str
    ok: bool = True


def parse_issue_form(body: str) -> dict[str, str]:
    """Parse GitHub Issue Form markdown sections (`### Section Title\\n\\nvalue`)."""
    sections: dict[str, str] = {}
    current_key: str | None = None
    buf: list[str] = []
    for line in (body or '').splitlines():
        m = re.match(r'^###\s+(.+?)\s*$', line)
        if m:
            if current_key is not None:
                sections[current_key] = '\n'.join(buf).strip()
            current_key = m.group(1).strip().lower()
            buf = []
        elif current_key is not None:
            buf.append(line)
    if current_key is not None:
        sections[current_key] = '\n'.join(buf).strip()
    return sections


def _strip_code_fence(text: str) -> str:
    text = (text or '').strip()
    m = re.match(r'^```[a-zA-Z0-9_+-]*\s*\n(.*?)\n```\s*$', text, re.DOTALL)
    return m.group(1).strip() if m else text


def _call_archguard_mcp(tool_name: str, arguments: dict, timeout: int = 12) -> tuple[dict, int]:
    payload = json.dumps({
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'tools/call',
        'params': {'name': tool_name, 'arguments': arguments},
    }).encode('utf-8')
    req = urllib.request.Request(
        ARCHGUARD_MCP_URL,
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'yashwant938-profile-sandbox',
        },
        method='POST',
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        elapsed_ms = max(1, int(round((time.perf_counter() - t0) * 1000)))
    result = data.get('result') or {}
    if result.get('isError'):
        raise RuntimeError(str(result.get('content')))
    structured = result.get('structuredContent')
    if isinstance(structured, dict):
        return structured, elapsed_ms
    content = result.get('content') or []
    if content and isinstance(content[0], dict) and content[0].get('text'):
        return json.loads(content[0]['text']), elapsed_ms
    raise RuntimeError('Unexpected MCP response shape')


def parse_architecture_payload(raw: str) -> list[dict[str, str]]:
    """Convert either `// file: path` blocks or `a.js -> b.js` edge lists into virtual source files."""
    text = _strip_code_fence(raw)[:MAX_PAYLOAD_CHARS]
    if not text:
        return []

    # Format 1: Explicit multi-file blocks (`// file: src/a.js` or `# file: a.py`)
    file_marker = re.compile(r'^(?://|#)\s*file:\s*([^\r\n]+)$', re.MULTILINE | re.IGNORECASE)
    matches = list(file_marker.finditer(text))
    if matches:
        files: list[dict[str, str]] = []
        for idx, m in enumerate(matches):
            path = m.group(1).strip().lstrip('./')[:80]
            start = m.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            if path:
                files.append({'path': path, 'content': content or '// empty'})
        return files

    # Format 2: Edge shorthand (`src/auth.js -> src/users.js`)
    edge_re = re.compile(r'^\s*([A-Za-z0-9_./-]+)\s*(?:->|=>)\s*([A-Za-z0-9_./-]+)\s*$')
    edges: list[tuple[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('//'):
            continue
        em = edge_re.match(line)
        if em:
            edges.append((em.group(1), em.group(2)))
    if edges:
        nodes: dict[str, list[str]] = {}
        for src, dst in edges:
            src_f = src if '.' in Path(src).name else f'{src}.js'
            dst_f = dst if '.' in Path(dst).name else f'{dst}.js'
            nodes.setdefault(src_f, []).append(dst_f)
            nodes.setdefault(dst_f, [])
        files = []
        for src_f, deps in nodes.items():
            imports = []
            for dst_f in deps:
                rel = os.path.relpath(dst_f, Path(src_f).parent.as_posix()).replace('\\', '/')
                if not rel.startswith('.'):
                    rel = f'./{rel}'
                imports.append(f"import '{rel}';")
            body = '\n'.join(imports) if imports else 'export const leaf = true;'
            files.append({'path': src_f, 'content': body})
        return files

    # Format 3: Single raw code snippet
    return [{'path': 'src/snippet.js', 'content': text}]


def _fallback_sql_audit(sql: str, dialect: str) -> dict:
    findings = []
    upper = sql.upper()
    if 'LOCK_TIMEOUT' not in upper:
        findings.append({
            'id': 'MIG-007', 'severity': 'MEDIUM', 'lockLevel': 'QUEUE_PILEUP_RISK',
            'title': 'Missing SET lock_timeout guard before DDL',
            'fix': "Add SET lock_timeout = '3s'; at top of migration.",
        })
    if re.search(r'CREATE\s+(?:UNIQUE\s+)?INDEX\b(?!\s+CONCURRENTLY)', upper):
        findings.append({
            'id': 'MIG-001', 'severity': 'CRITICAL', 'lockLevel': 'SHARE (blocks all writes)',
            'title': 'Blocking CREATE INDEX without CONCURRENTLY',
            'fix': 'Use CREATE INDEX CONCURRENTLY outside a transaction block.',
        })
    if re.search(r'ADD\s+COLUMN\b[^;]*NOT\s+NULL(?!\s+DEFAULT)', upper):
        findings.append({
            'id': 'MIG-003', 'severity': 'CRITICAL', 'lockLevel': 'ACCESS EXCLUSIVE',
            'title': 'ADD COLUMN NOT NULL without DEFAULT',
            'fix': 'Add nullable column, backfill in batches, then validate NOT NULL constraint.',
        })
    if re.search(r'DROP\s+COLUMN\b|RENAME\s+COLUMN\b', upper):
        findings.append({
            'id': 'MIG-002', 'severity': 'CRITICAL', 'lockLevel': 'ROLLING_DEPLOY_BREAK',
            'title': 'Destructive DROP/RENAME COLUMN breaks live pods',
            'fix': 'Stop reading/writing the column in app code first, then drop in phase 3.',
        })
    crit = sum(1 for f in findings if f['severity'] == 'CRITICAL')
    med = sum(1 for f in findings if f['severity'] == 'MEDIUM')
    verdict = 'BLOCK_DEPLOY' if crit else ('WARN' if med else 'SAFE_TO_DEPLOY')
    return {
        'dialect': dialect,
        'verdict': verdict,
        'severityCounts': {'CRITICAL': crit, 'HIGH': 0, 'MEDIUM': med, 'LOW': 0},
        'findings': findings,
        'expandContractPlan': {
            'recommendedHeader': "SET lock_timeout = '3s';\nSET statement_timeout = '30s';",
            'phase1Expand': ['Add nullable columns or CONCURRENTLY indexes safely.'],
            'phase2BackfillAndDualWrite': ['Deploy dual-write app code and backfill in 5,000-row batches.'],
            'phase3Contract': ['Validate constraints with NOT VALID -> VALIDATE, then drop legacy columns.'],
        },
    }


def _fallback_tarjan_scc(files: list[dict[str, str]]) -> dict:
    graph: dict[str, list[str]] = {f['path']: [] for f in files}
    for f in files:
        base_dir = Path(f['path']).parent
        for imp in re.findall(r"""from\s+['"]([^'"]+)['"]|import\s+['"]([^'"]+)['"]""", f['content']):
            target = imp[0] or imp[1]
            if target.startswith('.'):
                resolved = os.path.normpath((base_dir / target).as_posix()).replace('\\', '/')
                if resolved in graph:
                    graph[f['path']].append(resolved)

    index = 0
    indices: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    cycles: list[list[str]] = []

    def strongconnect(v: str) -> None:
        nonlocal index
        indices[v] = lowlink[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)
        for w in graph.get(v, []):
            if w not in indices:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], indices[w])
        if lowlink[v] == indices[v]:
            comp = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                cycles.append(list(reversed(comp)))

    for node in graph:
        if node not in indices:
            strongconnect(node)

    mermaid_lines = ['graph LR']
    for src, dsts in graph.items():
        s_id = re.sub(r'[^A-Za-z0-9_]', '_', src)
        for dst in dsts:
            d_id = re.sub(r'[^A-Za-z0-9_]', '_', dst)
            mermaid_lines.append(f'  {s_id}["{src}"] --> {d_id}["{dst}"]')
    score = max(0, 100 - len(cycles) * 25)
    return {
        'healthScore': score,
        'circularDependencies': cycles,
        'findings': [
            {'id': 'ARCH-001', 'severity': 'CRITICAL', 'title': f'Circular dependency: {" -> ".join(c + [c[0]])}'}
            for c in cycles
        ],
        'mermaidGraph': '\n'.join(mermaid_lines),
    }


def run_archguard_sandbox(body: str, author: str, issue_number: int) -> SandboxResult:
    now = datetime.now(timezone.utc)
    sections = parse_issue_form(body)
    mode_raw = sections.get('audit mode', '').lower()
    dialect = (sections.get('sql dialect (for sql mode)', '') or 'postgres').strip().lower()
    if dialect not in ('postgres', 'mysql', 'sqlite'):
        dialect = 'postgres'
    payload = _strip_code_fence(
        sections.get('sql ddl or dependency edges / code snippet', '') or body
    )[:MAX_PAYLOAD_CHARS]

    is_graph_mode = 'graph' in mode_raw or 'tarjan' in mode_raw or 'architecture' in mode_raw
    if not mode_raw and ('->' in payload or '// file:' in payload.lower()):
        is_graph_mode = True

    if is_graph_mode:
        files = parse_architecture_payload(payload)
        source_label = 'Live Cloudflare Worker (`arch-guard-mcp.yashwant938.workers.dev/mcp`)'
        try:
            data, latency_ms = _call_archguard_mcp('audit_code_snippet', {'files': files})
            source_label = f'Live Cloudflare Worker (`200 OK · {latency_ms}ms`)'
        except Exception:
            data = _fallback_tarjan_scc(files)
            source_label = 'Offline Deterministic Tarjan Fallback'

        score = int(data.get('healthScore', data.get('score', 100)))
        cycles = data.get('circularDependencies') or data.get('cycles') or []
        findings = data.get('findings') or []
        mermaid = data.get('mermaidGraph') or data.get('mermaid') or ''

        rows = [
            f"| `{f.get('id', 'ARCH')}` | **{f.get('severity', 'INFO')}** | {f.get('title', f.get('message', ''))} |"
            for f in findings[:10]
        ]
        table = (
            '| Rule | Severity | Finding |\n| :--- | :---: | :--- |\n' + '\n'.join(rows)
            if rows else '_Zero architectural violations or dependency cycles detected._'
        )
        mermaid_block = f'\n### Dependency Graph (Tarjan SCC)\n```mermaid\n{mermaid}\n```\n' if mermaid else ''
        comment = (
            f'## ⚡ ArchGuard MCP — Architecture & Dependency Audit\n\n'
            f'- **Engine:** {source_label}\n'
            f'- **Files Analyzed:** `{len(files)}` · **Health Score:** `{score}/100` · **Tarjan SCC Cycles:** `{len(cycles)}`\n\n'
            f'{table}\n{mermaid_block}\n'
            f'<sub>Triggered by @{author} · Connect directly via MCP: `https://arch-guard-mcp.yashwant938.workers.dev/mcp`</sub>\n'
        )
        preview = [
            f'$ mcp call audit_code_snippet ({len(files)} files)',
            f'score: {score}/100 | cycles: {len(cycles)} | findings: {len(findings)}',
        ]
        for f in findings[:2]:
            preview.append(f"[{f.get('severity', 'INFO')}] {str(f.get('title', ''))[:58]}")
        while len(preview) < 4:
            preview.append('status: verified deterministic graph output')
        return SandboxResult(
            mode='ARCHGUARD_GRAPH',
            badge_label='ARCHGUARD MCP · TARJAN SCC',
            accent='#A78BFA',
            author=author,
            issue_number=issue_number,
            ran_at=now,
            headline=f'Audited {len(files)} modules · {len(cycles)} SCC cycle(s) · {len(findings)} finding(s)',
            metric_pill=f'SCORE {score}/100 · {len(cycles)} CYCLES',
            preview_lines=tuple(preview[:4]),
            comment_markdown=comment,
        )

    # SQL DDL Migration Audit
    source_label = 'Live Cloudflare Worker (`arch-guard-mcp.yashwant938.workers.dev/mcp`)'
    try:
        data, latency_ms = _call_archguard_mcp(
            'check_migration_safety', {'sql': payload, 'dialect': dialect}
        )
        source_label = f'Live Cloudflare Worker (`200 OK · {latency_ms}ms`)'
    except Exception:
        data = _fallback_sql_audit(payload, dialect)
        source_label = 'Offline Deterministic DDL Guardian Fallback'

    verdict = str(data.get('verdict', 'ANALYZED'))
    counts = data.get('severityCounts') or {}
    crit = int(counts.get('CRITICAL', 0))
    high = int(counts.get('HIGH', 0))
    med = int(counts.get('MEDIUM', 0))
    findings = data.get('findings') or []
    plan = data.get('expandContractPlan') or {}

    rows = [
        f"| `{f.get('id', 'MIG')}` | **{f.get('severity', '')}** | `{f.get('lockLevel', '—')}` | {f.get('title', '')} |"
        for f in findings[:10]
    ]
    table = (
        '| Rule | Severity | Lock / Risk | Finding |\n| :--- | :---: | :--- | :--- |\n' + '\n'.join(rows)
        if rows else '_No blocking locks or rolling-deploy breaks detected._'
    )
    p1 = '\n'.join(plan.get('phase1Expand') or ['-- Safe additive DDL'])
    p2 = '\n'.join(f'-- {line}' for line in (plan.get('phase2BackfillAndDualWrite') or ['Dual-write & batched backfill']))
    p3 = '\n'.join(plan.get('phase3Contract') or ['-- Validate constraints & contract'])
    hdr = plan.get('recommendedHeader') or "SET lock_timeout = '3s';"

    comment = (
        f'## ⚡ ArchGuard MCP — Zero-Downtime SQL Migration Audit (`{dialect}`)\n\n'
        f'- **Engine:** {source_label}\n'
        f'- **Verdict:** `{verdict}` · **Critical:** `{crit}` · **High:** `{high}` · **Medium:** `{med}`\n\n'
        f'{table}\n\n'
        f'### Recommended 3-Phase Expand-Contract Plan\n'
        f'```sql\n{hdr}\n\n-- Phase 1 (Expand)\n{p1}\n\n-- Phase 2 (Dual-Write & Backfill)\n{p2}\n\n-- Phase 3 (Contract)\n{p3}\n```\n\n'
        f'<sub>Triggered by @{author} · Connect directly via MCP: `https://arch-guard-mcp.yashwant938.workers.dev/mcp`</sub>\n'
    )

    preview = [
        f'$ mcp call check_migration_safety ({dialect})',
        f'verdict: {verdict} | critical={crit} high={high} med={med}',
    ]
    for f in findings[:2]:
        preview.append(f"[{f.get('id', 'MIG')}] {str(f.get('title', ''))[:58]}")
    while len(preview) < 4:
        preview.append('plan: 3-phase expand-contract emitted')

    pill = f'{verdict} · {crit} CRITICAL' if crit else f'{verdict} · {len(findings)} CHECKS'
    return SandboxResult(
        mode='ARCHGUARD_SQL',
        badge_label='ARCHGUARD MCP · SQL DDL',
        accent='#E5A93C',
        author=author,
        issue_number=issue_number,
        ran_at=now,
        headline=f'Audited {dialect} DDL · {crit} critical lock(s) flagged',
        metric_pill=pill,
        preview_lines=tuple(preview[:4]),
        comment_markdown=comment,
    )


def validate_cpp_snippet(code: str) -> str | None:
    """Return an error reason if the C++ snippet violates sandbox safety rules, else None."""
    if not code.strip():
        return 'Empty C++ snippet.'
    if len(code) > MAX_CPP_CHARS:
        return f'Snippet exceeds {MAX_CPP_CHARS} characters.'
    if len(code.splitlines()) > MAX_CPP_LINES:
        return f'Snippet exceeds {MAX_CPP_LINES} lines.'
    for pat in FORBIDDEN_CPP_PATTERNS:
        if pat.search(code):
            return 'Blocked directive or unsafe construct (custom #include paths, #pragma, #embed, inline asm, or process calls are disallowed).'
    for inc in re.findall(r'^\s*#\s*include\s*<([^>]+)>', code, re.MULTILINE):
        if inc.strip() not in ALLOWED_CPP_HEADERS:
            return f'Header `<{inc.strip()}>` is not in the sandbox allowlist.'
    return None


def clean_assembly(asm_text: str) -> tuple[list[str], int]:
    """Strip assembler metadata directives and return readable lines + instruction count."""
    cleaned: list[str] = []
    inst_count = 0
    for raw in asm_text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or stripped.startswith('//'):
            continue
        # Drop assembler metadata directives (keep labels and real instructions)
        if stripped.startswith('.') and not stripped.endswith(':'):
            continue
        if stripped.startswith('.Lfunc_') or stripped.startswith('.Ltmp'):
            continue
        cleaned.append(line)
        if not stripped.endswith(':'):
            inst_count += 1
    return cleaned, inst_count


def _compile_to_asm(clang_bin: str, src_path: Path, opt_flag: str) -> tuple[bool, str]:
    cmd = [
        clang_bin,
        '-std=c++20',
        opt_flag,
        '-S',
        '-fno-asynchronous-unwind-tables',
        '-fno-exceptions',
        '-fno-rtti',
        '-masm=intel',
        '-fconstexpr-steps=10000',
        '-ftemplate-depth=32',
        '-o', '-',
        str(src_path),
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=6,
        check=False,
    )
    if proc.returncode != 0:
        return False, (proc.stderr or 'Compilation failed')[:1200]
    return True, proc.stdout


def run_clang_sandbox(body: str, author: str, issue_number: int) -> SandboxResult:
    now = datetime.now(timezone.utc)
    sections = parse_issue_form(body)
    opt_level = (sections.get('optimization level to compare against -o0', '') or '-O2').strip()
    if opt_level not in ('-O2', '-O3'):
        opt_level = '-O2'
    code = _strip_code_fence(sections.get('c++20 function snippet (max 80 lines)', '') or body)

    err = validate_cpp_snippet(code)
    if err:
        comment = (
            f'## 🔬 Clang++ Sandbox — Input Rejected by Safety Guard\n\n'
            f'**Reason:** {err}\n\n'
            f'Allowed headers: {", ".join(f"`<{h}>`" for h in sorted(ALLOWED_CPP_HEADERS))}.\n'
        )
        return SandboxResult(
            mode='CLANG_DIFF',
            badge_label=f'CLANG++ · -O0 → {opt_level}',
            accent='#60A5FA',
            author=author,
            issue_number=issue_number,
            ran_at=now,
            headline='Sandbox safety guard blocked disallowed directive',
            metric_pill='GUARD BLOCKED',
            preview_lines=('$ clang++ -std=c++20 -S -masm=intel', err[:64], '', ''),
            comment_markdown=comment,
            ok=False,
        )

    clang_bin = shutil.which('clang++')
    if not clang_bin:
        raise RuntimeError('clang++ not found on PATH')

    with tempfile.TemporaryDirectory(prefix='clang_sandbox_') as tmpdir:
        src = Path(tmpdir) / 'snippet.cpp'
        src.write_text(code + '\n', encoding='utf-8')
        ok0, out0 = _compile_to_asm(clang_bin, src, '-O0')
        ok1, out1 = _compile_to_asm(clang_bin, src, opt_level) if ok0 else (False, out0)

    if not ok0 or not ok1:
        diag = out0 if not ok0 else out1
        comment = (
            f'## 🔬 Clang++ Sandbox — Compilation Diagnostic\n\n'
            f'```text\n{diag}\n```\n'
        )
        return SandboxResult(
            mode='CLANG_DIFF',
            badge_label=f'CLANG++ · -O0 → {opt_level}',
            accent='#60A5FA',
            author=author,
            issue_number=issue_number,
            ran_at=now,
            headline='Compilation failed with diagnostics',
            metric_pill='COMPILE ERROR',
            preview_lines=('$ clang++ -std=c++20 -S', diag.splitlines()[0][:64] if diag else 'error', '', ''),
            comment_markdown=comment,
            ok=False,
        )

    lines0, count0 = clean_assembly(out0)
    lines1, count1 = clean_assembly(out1)
    delta_pct = int(round(((count0 - count1) / max(1, count0)) * 100))
    sign_txt = f'-{delta_pct}%' if delta_pct >= 0 else f'+{abs(delta_pct)}%'
    o0_block = '\n'.join(lines0[:45])
    opt_block = '\n'.join(lines1[:45])

    comment = (
        f'## 🔬 Clang++ x86-64 Assembly Diff (`-O0` vs `{opt_level}`)\n\n'
        f'| Pass | x86-64 Instructions | Reduction |\n'
        f'| :--- | :---: | :---: |\n'
        f'| `clang++ -std=c++20 -O0` | `{count0}` | baseline |\n'
        f'| `clang++ -std=c++20 {opt_level}` | `{count1}` | **`{sign_txt}`** |\n\n'
        f'### Optimized Assembly (`{opt_level}`)\n'
        f'```x86asm\n{opt_block}\n```\n\n'
        f'<details><summary>Unoptimized Baseline (<code>-O0</code>)</summary>\n\n'
        f'```x86asm\n{o0_block}\n```\n\n</details>\n\n'
        f'<sub>Compiled strictly with `-S` (assembly emission only; never linked or executed) · Triggered by @{author}</sub>\n'
    )

    preview = [f'$ clang++ -std=c++20 {opt_level} -S -masm=intel']
    for ln in lines1[:3]:
        preview.append(ln.strip()[:62])
    while len(preview) < 4:
        preview.append('ret')

    return SandboxResult(
        mode='CLANG_DIFF',
        badge_label=f'CLANG++ · -O0 → {opt_level}',
        accent='#60A5FA',
        author=author,
        issue_number=issue_number,
        ran_at=now,
        headline=f'Compiled C++20 to x86-64 · {count0} → {count1} instructions ({sign_txt})',
        metric_pill=f'{sign_txt} OPS ({count0} → {count1})',
        preview_lines=tuple(preview[:4]),
        comment_markdown=comment,
        ok=True,
    )


def render_sandbox_svg(res: SandboxResult, mobile: bool = False) -> str:
    ts = res.ran_at.strftime('%Y-%m-%d %H:%M UTC')
    issue_ref = f'@{res.author} · Issue #{res.issue_number}' if res.issue_number > 0 else f'@{res.author} · Baseline Run'
    is_alert = 'BLOCK' in res.metric_pill.upper() or 'ERROR' in res.metric_pill.upper()
    pill_bg = '#2A1D12' if is_alert else '#102922'
    pill_stroke = '#7C4D1E' if is_alert else '#1E5D47'
    pill_fg = '#FBBF24' if is_alert else '#34D399'
    if not mobile:
        w, h = 1200, 224
        term_lines = []
        for idx, line in enumerate(res.preview_lines[:4]):
            y = 114 + idx * 22
            fill = '#34D399' if idx == 0 else ('#E5A93C' if idx == 1 else '#CBD5E1')
            term_lines.append(
                f'<text x="644" y="{y}" fill="{fill}" font-family="Consolas, \'JetBrains Mono\', monospace" font-size="11">{escape(line[:58])}</text>'
            )
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="sb-title sb-desc">
  <title id="sb-title">Latest Interactive Profile Sandbox Experiment</title>
  <desc id="sb-desc">{escape(res.badge_label)} triggered by {escape(issue_ref)}: {escape(res.headline)}.</desc>
  <defs>
    <pattern id="sb-grid" width="28" height="28" patternUnits="userSpaceOnUse">
      <path d="M 28 0 L 0 0 0 28" fill="none" stroke="#161B24" stroke-width="1"/>
    </pattern>
  </defs>
  <rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="14" fill="#0B0E14" stroke="#252C3A" stroke-width="2"/>
  <rect x="2" y="2" width="{w - 4}" height="{h - 4}" rx="13" fill="url(#sb-grid)"/>
  <g font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif">
    <!-- Top Header Strip -->
    <rect x="28" y="20" width="1144" height="36" rx="8" fill="#101520" stroke="#242D40"/>
    <circle cx="46" cy="38" r="4" fill="#34D399"/>
    <text x="60" y="42" fill="#E2E8F0" font-family="Consolas, 'JetBrains Mono', monospace" font-size="11" font-weight="700" letter-spacing="1.2">INTERACTIVE PROFILE SANDBOX // LATEST VISITOR RUN</text>
    <text x="1154" y="42" fill="#64748B" font-family="Consolas, 'JetBrains Mono', monospace" font-size="10.5" text-anchor="end">{escape(ts)}</text>

    <!-- Left Metadata Card -->
    <rect x="28" y="68" width="584" height="134" rx="10" fill="#111724" stroke="#253047"/>
    <rect x="28" y="68" width="4" height="134" rx="2" fill="{res.accent}"/>
    <rect x="46" y="84" width="214" height="22" rx="11" fill="#182235" stroke="{res.accent}" stroke-opacity="0.6"/>
    <text x="153" y="99" fill="{res.accent}" font-family="Consolas, 'JetBrains Mono', monospace" font-size="10" font-weight="700" text-anchor="middle">{escape(res.badge_label)}</text>
    <rect x="372" y="84" width="224" height="22" rx="11" fill="{pill_bg}" stroke="{pill_stroke}"/>
    <text x="484" y="99" fill="{pill_fg}" font-family="Consolas, 'JetBrains Mono', monospace" font-size="10" font-weight="700" text-anchor="middle">{escape(res.metric_pill[:28])}</text>

    <text x="46" y="138" fill="#F8FAFC" font-size="16" font-weight="700">{escape(res.headline[:62])}</text>
    <text x="46" y="164" fill="#94A3B8" font-family="Consolas, 'JetBrains Mono', monospace" font-size="11.5">Triggered by {escape(issue_ref)}</text>
    <text x="46" y="186" fill="#64748B" font-size="11.5">Click a sandbox button below to trigger your own live ArchGuard MCP or Clang++ run (~15s).</text>

    <!-- Right Terminal Preview Card -->
    <rect x="626" y="68" width="546" height="134" rx="10" fill="#0A0E16" stroke="#232D42"/>
    <circle cx="646" cy="84" r="3.5" fill="#EF4444" opacity="0.8"/>
    <circle cx="659" cy="84" r="3.5" fill="#E5A93C" opacity="0.8"/>
    <circle cx="672" cy="84" r="3.5" fill="#34D399" opacity="0.8"/>
    <text x="1156" y="88" fill="#475569" font-family="Consolas, 'JetBrains Mono', monospace" font-size="9.5" text-anchor="end">LIVE OUTPUT PREVIEW</text>
    <line x1="626" y1="96" x2="1172" y2="96" stroke="#1B2335"/>
    {''.join(term_lines)}
  </g>
</svg>
'''

    # Mobile layout
    w, h = 600, 316
    term_lines = []
    for idx, line in enumerate(res.preview_lines[:4]):
        y = 224 + idx * 19
        fill = '#34D399' if idx == 0 else ('#E5A93C' if idx == 1 else '#CBD5E1')
        term_lines.append(
            f'<text x="40" y="{y}" fill="{fill}" font-family="Consolas, \'JetBrains Mono\', monospace" font-size="10.5">{escape(line[:56])}</text>'
        )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="sbm-title sbm-desc">
  <title id="sbm-title">Latest Interactive Profile Sandbox Experiment</title>
  <desc id="sbm-desc">{escape(res.badge_label)}: {escape(res.headline)}.</desc>
  <rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="14" fill="#0B0E14" stroke="#252C3A" stroke-width="2"/>
  <g font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif">
    <rect x="22" y="18" width="556" height="34" rx="8" fill="#101520" stroke="#242D40"/>
    <circle cx="38" cy="35" r="3.5" fill="#34D399"/>
    <text x="50" y="39" fill="#E2E8F0" font-family="Consolas, monospace" font-size="10.5" font-weight="700">SANDBOX // LATEST VISITOR RUN</text>
    <text x="564" y="39" fill="#64748B" font-family="Consolas, monospace" font-size="9.5" text-anchor="end">{escape(ts)}</text>

    <rect x="22" y="64" width="556" height="114" rx="10" fill="#111724" stroke="#253047"/>
    <rect x="22" y="64" width="4" height="114" rx="2" fill="{res.accent}"/>
    <text x="38" y="88" fill="{res.accent}" font-family="Consolas, monospace" font-size="10" font-weight="700">{escape(res.badge_label)}</text>
    <text x="562" y="88" fill="#34D399" font-family="Consolas, monospace" font-size="10" font-weight="700" text-anchor="end">{escape(res.metric_pill[:28])}</text>
    <text x="38" y="120" fill="#F8FAFC" font-size="14.5" font-weight="700">{escape(res.headline[:56])}</text>
    <text x="38" y="148" fill="#94A3B8" font-family="Consolas, monospace" font-size="11">Triggered by {escape(issue_ref)}</text>

    <rect x="22" y="190" width="556" height="108" rx="10" fill="#0A0E16" stroke="#232D42"/>
    {''.join(term_lines)}
  </g>
</svg>
'''


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=('archguard', 'clang'), required=True)
    parser.add_argument('--author', default=os.environ.get('ISSUE_AUTHOR', 'yashwant938'))
    parser.add_argument('--issue-number', type=int, default=int(os.environ.get('ISSUE_NUMBER', '0') or '0'))
    parser.add_argument('--body-file', type=Path, default=None)
    parser.add_argument('--comment-out', type=Path, default=None)
    parser.add_argument(
        '--svg-out',
        type=Path,
        default=Path(__file__).resolve().parents[1] / 'assets' / 'sandbox-latest.svg',
    )
    args = parser.parse_args(argv)

    body = (
        args.body_file.read_text(encoding='utf-8')
        if args.body_file
        else os.environ.get('ISSUE_BODY', '')
    )
    author = re.sub(r'[^A-Za-z0-9_-]', '', args.author)[:39] or 'visitor'

    if args.kind == 'archguard':
        result = run_archguard_sandbox(body, author, args.issue_number)
    else:
        result = run_clang_sandbox(body, author, args.issue_number)

    if args.comment_out:
        args.comment_out.parent.mkdir(parents=True, exist_ok=True)
        args.comment_out.write_text(result.comment_markdown, encoding='utf-8', newline='\n')

    if result.ok:
        outputs = {
            args.svg_out: render_sandbox_svg(result, mobile=False),
            args.svg_out.with_name('sandbox-latest-mobile.svg'): render_sandbox_svg(result, mobile=True),
        }
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix('.svg.tmp')
            tmp.write_text(content, encoding='utf-8', newline='\n')
            tmp.replace(path)

    print(f'Sandbox {result.mode}: ok={result.ok} | {result.metric_pill} | {result.headline}')


if __name__ == '__main__':
    main()
