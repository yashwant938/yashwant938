#!/usr/bin/env python3
"""Generate dark-mode Live Upstream OSS & Edge Telemetry SVG panels (desktop + mobile)."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape


UPSTREAM_REPOS = (
    ('qualcomm/eld', 'LLVM / ELF Linker', '#60A5FA'),
    ('deepset-ai/haystack-core-integrations', 'GenAI / Haystack', '#E5A93C'),
    ('IBM/mcp-context-forge', 'MCP Gateway', '#A78BFA'),
    ('strands-agents/harness-sdk', 'Agent SDK / MCP', '#2DD4BF'),
    ('react-chatbotify/react-chatbotify', 'Security / UI', '#34D399'),
)

ARCHGUARD_HEALTH_URL = 'https://arch-guard-mcp.yashwant938.workers.dev/health'
CONTEXTFORGE_HEALTH_URL = 'https://context-forge-mcp.yashwant938.workers.dev/health'
SYSDESIGN_URL = 'https://system-design-guide.yashwant938.workers.dev'
MCP_REGISTRY_URL = (
    'https://registry.modelcontextprotocol.io/v0.1/servers/'
    'io.github.yashwant938%2Farch-guard-mc/versions/latest'
)


@dataclass(frozen=True)
class RepoPRSummary:
    repo: str
    domain: str
    accent: str
    merged_count: int
    open_count: int
    additions: int
    deletions: int
    latest_pr: int | None
    latest_state: str
    diff_available: bool = True


@dataclass(frozen=True)
class EdgeProbe:
    name: str
    host: str
    ok: bool
    status_code: int
    latency_ms: int
    detail: str
    accent: str


@dataclass(frozen=True)
class RegistryStatus:
    server_id: str
    version: str
    status: str
    transport: str
    ok: bool


@dataclass(frozen=True)
class TelemetrySnapshot:
    username: str
    synced_at: datetime
    repos: tuple[RepoPRSummary, ...]
    probes: tuple[EdgeProbe, ...]
    registry: RegistryStatus

    @property
    def total_merged(self) -> int:
        return sum(r.merged_count for r in self.repos)

    @property
    def total_open(self) -> int:
        return sum(r.open_count for r in self.repos)

    @property
    def total_additions(self) -> int:
        return sum(r.additions for r in self.repos if r.merged_count > 0)

    @property
    def total_deletions(self) -> int:
        return sum(r.deletions for r in self.repos if r.merged_count > 0)

    @property
    def any_diff_available(self) -> bool:
        return any(r.merged_count > 0 and r.diff_available and (r.additions > 0 or r.deletions > 0) for r in self.repos)


def _github_headers(token: str | None) -> dict[str, str]:
    headers = {
        'User-Agent': 'yashwant938-profile-telemetry',
        'Accept': 'application/vnd.github+json',
    }
    if token:
        headers['Authorization'] = f'Bearer {token}'
    return headers


def _http_get_json(url: str, headers: dict[str, str], timeout: int = 20) -> tuple[int, int, dict]:
    req = urllib.request.Request(url, headers=headers)
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode('utf-8')
        elapsed_ms = max(1, int(round((time.perf_counter() - t0) * 1000)))
        return resp.status, elapsed_ms, json.loads(raw)


def _http_probe(url: str, timeout: int = 15) -> tuple[int, int, str]:
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'yashwant938-profile-telemetry'},
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(16384).decode('utf-8', errors='replace')
            elapsed_ms = max(1, int(round((time.perf_counter() - t0) * 1000)))
            return resp.status, elapsed_ms, body
    except urllib.error.HTTPError as err:
        elapsed_ms = max(1, int(round((time.perf_counter() - t0) * 1000)))
        return err.code, elapsed_ms, ''
    except Exception:
        elapsed_ms = max(1, int(round((time.perf_counter() - t0) * 1000)))
        return 0, elapsed_ms, ''


def fetch_pr_diff_stats(repo: str, number: int, token: str | None) -> tuple[int, int, bool]:
    url = f'https://api.github.com/repos/{repo}/pulls/{number}'
    try:
        _, _, data = _http_get_json(url, _github_headers(token), timeout=15)
        return int(data.get('additions', 0)), int(data.get('deletions', 0)), True
    except Exception:
        return 0, 0, False


def fetch_upstream_prs(username: str, token: str | None = None) -> tuple[RepoPRSummary, ...]:
    query = urllib.parse.urlencode({
        'q': f'type:pr author:{username} -user:{username}',
        'per_page': 100,
        'sort': 'updated',
    })
    url = f'https://api.github.com/search/issues?{query}'
    _, _, payload = _http_get_json(url, _github_headers(token), timeout=25)
    items = payload.get('items', [])

    tracked = {repo: [] for repo, _, _ in UPSTREAM_REPOS}
    for item in items:
        repo_url = item.get('repository_url', '')
        repo_name = repo_url.split('/repos/', 1)[-1] if '/repos/' in repo_url else ''
        if repo_name not in tracked:
            continue
        is_merged = bool((item.get('pull_request') or {}).get('merged_at'))
        state = item.get('state', '')
        if not is_merged and state != 'open':
            continue
        tracked[repo_name].append({
            'number': int(item['number']),
            'merged': is_merged,
            'open': state == 'open',
            'updated_at': item.get('updated_at', ''),
        })

    # Fetch exact +additions / -deletions for merged PRs (plus bounded open PRs for repos
    # with no merges yet) so verified upstream diff stats stay accurate and never inflate
    # from huge lockfile/generated diffs on WIP branches.
    pr_jobs: list[tuple[str, int, bool]] = []
    for repo_name, prs in tracked.items():
        merged_prs = [p for p in prs if p['merged']]
        if merged_prs:
            for p in merged_prs:
                pr_jobs.append((repo_name, p['number'], True))
        else:
            for p in prs[:3]:
                pr_jobs.append((repo_name, p['number'], False))

    diff_map: dict[tuple[str, int], tuple[int, int, bool]] = {}
    if pr_jobs:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(fetch_pr_diff_stats, repo_name, number, token): (repo_name, number)
                for repo_name, number, _ in pr_jobs
            }
            for fut, key in futures.items():
                diff_map[key] = fut.result()

    summaries: list[RepoPRSummary] = []
    for repo_name, domain, accent in UPSTREAM_REPOS:
        prs = sorted(tracked[repo_name], key=lambda p: (p['updated_at'], p['number']), reverse=True)
        merged_count = sum(1 for p in prs if p['merged'])
        open_count = sum(1 for p in prs if p['open'])
        additions = 0
        deletions = 0
        any_ok = False
        target_prs = [p for p in prs if p['merged']] if merged_count else prs[:3]
        for p in target_prs:
            add, dele, ok = diff_map.get((repo_name, p['number']), (0, 0, False))
            if ok:
                # Ignore outlier generated/lockfile diffs on unmerged PRs.
                if not p['merged'] and (add + dele) > 25000:
                    continue
                any_ok = True
                additions += add
                deletions += dele
        latest_pr = prs[0]['number'] if prs else None
        latest_state = 'MERGED' if (prs and prs[0]['merged']) else ('OPEN' if prs else 'IDLE')
        summaries.append(RepoPRSummary(
            repo=repo_name,
            domain=domain,
            accent=accent,
            merged_count=merged_count,
            open_count=open_count,
            additions=additions,
            deletions=deletions,
            latest_pr=latest_pr,
            latest_state=latest_state,
            diff_available=any_ok,
        ))
    return tuple(summaries)


def probe_edge_infra() -> tuple[tuple[EdgeProbe, ...], RegistryStatus]:
    # Probe ArchGuard MCP Worker
    ag_code, ag_ms, ag_body = _http_probe(ARCHGUARD_HEALTH_URL)
    ag_ok = ag_code == 200
    ag_detail = 'Streamable HTTP · Zero Auth'
    if ag_ok and ag_body:
        try:
            data = json.loads(ag_body)
            proto = data.get('protocolVersion', '2025-03-26')
            tools = data.get('tools', 6)
            res = data.get('resources', 4)
            prompts = data.get('prompts', 3)
            ag_detail = f'MCP {proto} · {tools} HTTP tools · {res} res · {prompts} prompts'
        except Exception:
            pass

    # Probe ContextForge MCP Worker
    cf_code, cf_ms, cf_body = _http_probe(CONTEXTFORGE_HEALTH_URL)
    cf_ok = cf_code == 200
    cf_detail = 'Streamable HTTP · Token Compressor & RAG Packer'
    if cf_ok and cf_body:
        try:
            data = json.loads(cf_body)
            proto = data.get('protocolVersion', '2025-03-26')
            tools = data.get('tools', 6)
            res = data.get('resources', 4)
            prompts = data.get('prompts', 3)
            cf_detail = f'MCP {proto} · {tools} HTTP tools · {res} res · {prompts} prompts'
        except Exception:
            pass

    # Probe System Design Atlas Worker
    sd_code, sd_ms, _ = _http_probe(SYSDESIGN_URL)
    sd_ok = sd_code == 200
    sd_detail = 'Cloudflare Edge · 14 modules · 100 lessons · 6 labs'

    probes = (
        EdgeProbe(
            name='ArchGuard MCP Worker',
            host='arch-guard-mcp.yashwant938.workers.dev/mcp',
            ok=ag_ok,
            status_code=ag_code,
            latency_ms=ag_ms,
            detail=ag_detail,
            accent='#34D399',
        ),
        EdgeProbe(
            name='ContextForge MCP Worker',
            host='context-forge-mcp.yashwant938.workers.dev/mcp',
            ok=cf_ok,
            status_code=cf_code,
            latency_ms=cf_ms,
            detail=cf_detail,
            accent='#E5A93C',
        ),
        EdgeProbe(
            name='System Design Atlas',
            host='system-design-guide.yashwant938.workers.dev',
            ok=sd_ok,
            status_code=sd_code,
            latency_ms=sd_ms,
            detail=sd_detail,
            accent='#60A5FA',
        ),
    )

    # Probe Official MCP Registry
    reg_code, _, reg_body = _http_probe(MCP_REGISTRY_URL)
    reg_ok = False
    version = '1.0.0'
    status = 'ACTIVE'
    transport = 'streamable-http'
    server_id = 'io.github.yashwant938/arch-guard-mc'
    if reg_code == 200 and reg_body:
        try:
            reg = json.loads(reg_body)
            srv = reg.get('server') or {}
            meta = (reg.get('_meta') or {}).get('io.modelcontextprotocol.registry/official') or {}
            server_id = str(srv.get('name') or server_id)
            version = str(srv.get('version') or version)
            status = str(meta.get('status') or 'active').upper()
            remotes = srv.get('remotes') or []
            if remotes and isinstance(remotes, list):
                transport = str(remotes[0].get('type') or transport)
            reg_ok = True
        except Exception:
            pass

    registry = RegistryStatus(
        server_id=server_id,
        version=version,
        status=status,
        transport=transport,
        ok=reg_ok,
    )
    return probes, registry


def _fmt_num(value: int) -> str:
    if value >= 10000:
        return f'{value / 1000:.1f}k'
    return f'{value:,}'


def _short_repo(repo: str, max_len: int = 38) -> str:
    if len(repo) <= max_len:
        return repo
    owner, name = repo.split('/', 1)
    keep = max(8, max_len - len(owner) - 2)
    return f'{owner}/{name[:keep]}…'


def render_telemetry_svg(snapshot: TelemetrySnapshot, mobile: bool = False) -> str:
    synced_label = snapshot.synced_at.strftime('%Y-%m-%d %H:%M UTC')
    if mobile:
        return _render_mobile(snapshot, synced_label)
    return _render_desktop(snapshot, synced_label)


def _render_desktop(snapshot: TelemetrySnapshot, synced_label: str) -> str:
    w, h = 1200, 444
    diff_summary = (
        f'+{_fmt_num(snapshot.total_additions)} / -{_fmt_num(snapshot.total_deletions)}'
        if snapshot.any_diff_available
        else 'LIVE API SYNC'
    )
    active_repos = sum(1 for r in snapshot.repos if r.merged_count or r.open_count)

    rows_svg: list[str] = []
    for idx, r in enumerate(snapshot.repos):
        y = 196 + idx * 42
        bg_fill = '#121722' if idx % 2 == 0 else '#0F141E'
        pr_tag = f'#{r.latest_pr}' if r.latest_pr else '—'
        diff_text = (
            f'+{_fmt_num(r.additions)} / -{_fmt_num(r.deletions)}'
            if r.diff_available and (r.additions or r.deletions)
            else ('in review' if r.open_count else 'synced')
        )
        # Merged & Open status pills
        merged_pill = ''
        if r.merged_count > 0:
            merged_pill = (
                f'<rect x="336" y="{y + 9}" width="84" height="20" rx="10" fill="#0F2B22" stroke="#1E5D47"/>'
                f'<text x="378" y="{y + 23}" fill="#34D399" font-family="Consolas, \'JetBrains Mono\', monospace" '
                f'font-size="10" font-weight="700" text-anchor="middle">{r.merged_count} MERGED</text>'
            )
        else:
            merged_pill = (
                f'<text x="378" y="{y + 23}" fill="#475569" font-family="Consolas, \'JetBrains Mono\', monospace" '
                f'font-size="10" text-anchor="middle">—</text>'
            )

        open_pill = ''
        if r.open_count > 0:
            open_pill = (
                f'<rect x="430" y="{y + 9}" width="72" height="20" rx="10" fill="#2A2112" stroke="#6B4F1D"/>'
                f'<text x="466" y="{y + 23}" fill="#E5A93C" font-family="Consolas, \'JetBrains Mono\', monospace" '
                f'font-size="10" font-weight="700" text-anchor="middle">{r.open_count} OPEN</text>'
            )
        else:
            open_pill = (
                f'<text x="466" y="{y + 23}" fill="#475569" font-family="Consolas, \'JetBrains Mono\', monospace" '
                f'font-size="10" text-anchor="middle">0 OPEN</text>'
            )

        rows_svg.append(
            f'<g>'
            f'<rect x="40" y="{y}" width="664" height="38" rx="7" fill="{bg_fill}" stroke="#1E2636" stroke-width="1"/>'
            f'<rect x="40" y="{y}" width="3.5" height="38" rx="1.5" fill="{r.accent}"/>'
            f'<text x="54" y="{y + 17}" fill="#F1F5F9" font-family="Consolas, \'JetBrains Mono\', monospace" font-size="11.5" font-weight="700">{escape(_short_repo(r.repo))}</text>'
            f'<text x="54" y="{y + 31}" fill="#64748B" font-size="10">{escape(r.domain)}</text>'
            f'{merged_pill}'
            f'{open_pill}'
            f'<text x="538" y="{y + 23}" fill="#94A3B8" font-family="Consolas, \'JetBrains Mono\', monospace" font-size="10.5" text-anchor="middle">{escape(pr_tag)}</text>'
            f'<text x="692" y="{y + 23}" fill="#CBD5E1" font-family="Consolas, \'JetBrains Mono\', monospace" font-size="10.5" text-anchor="end">{escape(diff_text)}</text>'
            f'</g>'
        )

    # Right column: Production Edge Workers (3) + Official MCP Registry
    probe_cards: list[str] = []
    for idx, p in enumerate(snapshot.probes):
        py = 112 + idx * 76
        badge_bg = '#0F2B22' if p.ok else '#2F1518'
        badge_stroke = '#1E5D47' if p.ok else '#7F2329'
        badge_fg = '#34D399' if p.ok else '#F87171'
        status_txt = f'{p.status_code} OK · {p.latency_ms}ms' if p.ok else f'ERR {p.status_code or "NET"}'
        dot_fill = '#34D399' if p.ok else '#F87171'
        probe_cards.append(
            f'<g transform="translate(744, {py})">'
            f'<rect x="0" y="0" width="416" height="68" rx="8" fill="#131926" stroke="#253047" stroke-width="1.1"/>'
            f'<rect x="0" y="0" width="4" height="68" rx="2" fill="{p.accent}"/>'
            f'<circle cx="18" cy="20" r="3.5" fill="{dot_fill}" class="pulse"/>'
            f'<text x="29" y="24" fill="#F8FAFC" font-size="13" font-weight="700">{escape(p.name)}</text>'
            f'<rect x="278" y="9" width="126" height="20" rx="10" fill="{badge_bg}" stroke="{badge_stroke}"/>'
            f'<text x="341" y="23" fill="{badge_fg}" font-family="Consolas, \'JetBrains Mono\', monospace" font-size="10" font-weight="700" text-anchor="middle">{escape(status_txt)}</text>'
            f'<text x="18" y="42" fill="#60A5FA" font-family="Consolas, \'JetBrains Mono\', monospace" font-size="10">{escape(p.host)}</text>'
            f'<text x="18" y="58" fill="#94A3B8" font-size="10.5">{escape(p.detail)}</text>'
            f'</g>'
        )

    reg = snapshot.registry
    reg_bg = '#201836' if reg.ok else '#2F1518'
    reg_stroke = '#563D99' if reg.ok else '#7F2329'
    reg_fg = '#C4B5FD' if reg.ok else '#F87171'
    reg_pill = f'{reg.status} · v{reg.version}' if reg.ok else 'UNREACHABLE'

    registry_card = (
        f'<g transform="translate(744, 340)">'
        f'<rect x="0" y="0" width="416" height="68" rx="8" fill="#131926" stroke="#362A59" stroke-width="1.1"/>'
        f'<rect x="0" y="0" width="4" height="68" rx="2" fill="#A78BFA"/>'
        f'<circle cx="18" cy="20" r="3.5" fill="#A78BFA" class="pulse"/>'
        f'<text x="29" y="24" fill="#F8FAFC" font-size="13" font-weight="700">Official MCP Registry</text>'
        f'<rect x="278" y="9" width="126" height="20" rx="10" fill="{reg_bg}" stroke="{reg_stroke}"/>'
        f'<text x="341" y="23" fill="{reg_fg}" font-family="Consolas, \'JetBrains Mono\', monospace" font-size="10" font-weight="700" text-anchor="middle">{escape(reg_pill)}</text>'
        f'<text x="18" y="42" fill="#C4B5FD" font-family="Consolas, \'JetBrains Mono\', monospace" font-size="10">{escape(reg.server_id)}</text>'
        f'<text x="18" y="58" fill="#94A3B8" font-size="10.5">Transport: {escape(reg.transport)} · registry.modelcontextprotocol.io</text>'
        f'</g>'
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="tel-title tel-desc">
  <title id="tel-title">Live Upstream OSS and Edge Infrastructure Telemetry</title>
  <desc id="tel-desc">Automatically refreshed every four hours from the GitHub API, Cloudflare Workers edge probes, and the Official MCP Registry: {snapshot.total_merged} merged PRs and {snapshot.total_open} open PRs across {active_repos} upstream repositories.</desc>
  <defs>
    <pattern id="tel-grid" width="28" height="28" patternUnits="userSpaceOnUse">
      <path d="M 28 0 L 0 0 0 28" fill="none" stroke="#161B24" stroke-width="1"/>
    </pattern>
  </defs>
  <style>
    .pulse {{ animation: tel-pulse 2.8s ease-in-out infinite; }}
    @keyframes tel-pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.42; }} }}
    @media (prefers-reduced-motion: reduce) {{ .pulse {{ animation: none; }} }}
  </style>

  <!-- Obsidian Studio Frame -->
  <rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="14" fill="#0B0E14" stroke="#252C3A" stroke-width="2"/>
  <rect x="2" y="2" width="{w - 4}" height="{h - 4}" rx="13" fill="url(#tel-grid)"/>

  <!-- Top Telemetry Bar -->
  <g font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif">
    <rect x="28" y="22" width="1144" height="40" rx="9" fill="#101520" stroke="#242D40" stroke-width="1.2"/>
    <circle cx="48" cy="42" r="4.5" fill="#34D399" class="pulse"/>
    <text x="62" y="46" fill="#E2E8F0" font-family="Consolas, 'JetBrains Mono', monospace" font-size="11.5" font-weight="700" letter-spacing="1.3">LIVE SYSTEM TELEMETRY // UPSTREAM OSS &amp; EDGE INFRA</text>
    <text x="1154" y="46" fill="#64748B" font-family="Consolas, 'JetBrains Mono', monospace" font-size="10.5" text-anchor="end">SYNCED {escape(synced_label)} · 4H AUTO-CRON</text>

    <!-- Left Panel Container: Upstream Open-Source Ledger -->
    <rect x="28" y="76" width="688" height="344" rx="11" fill="#0E131D" stroke="#222B3D" stroke-width="1.2"/>
    <text x="44" y="100" fill="#60A5FA" font-family="Consolas, 'JetBrains Mono', monospace" font-size="10.5" font-weight="700" letter-spacing="1.2">UPSTREAM OPEN-SOURCE PR LEDGER (@{escape(snapshot.username)})</text>

    <!-- 4 Compact KPI Tiles -->
    <g transform="translate(40, 112)">
      <rect x="0" y="0" width="146" height="58" rx="8" fill="#131926" stroke="#1F3A32"/>
      <text x="14" y="20" fill="#64748B" font-family="Consolas, 'JetBrains Mono', monospace" font-size="9.5" font-weight="700">MERGED PRS</text>
      <text x="14" y="46" fill="#34D399" font-size="24" font-weight="800">{snapshot.total_merged}</text>
      <text x="58" y="44" fill="#64748B" font-size="10.5">upstream</text>

      <rect x="158" y="0" width="146" height="58" rx="8" fill="#131926" stroke="#3F311A"/>
      <text x="172" y="20" fill="#64748B" font-family="Consolas, 'JetBrains Mono', monospace" font-size="9.5" font-weight="700">OPEN IN REVIEW</text>
      <text x="172" y="46" fill="#E5A93C" font-size="24" font-weight="800">{snapshot.total_open}</text>
      <text x="220" y="44" fill="#64748B" font-size="10.5">active</text>

      <rect x="316" y="0" width="214" height="58" rx="8" fill="#131926" stroke="#24334D"/>
      <text x="330" y="20" fill="#64748B" font-family="Consolas, 'JetBrains Mono', monospace" font-size="9.5" font-weight="700">MERGED DIFF</text>
      <text x="330" y="45" fill="#60A5FA" font-family="Consolas, 'JetBrains Mono', monospace" font-size="16" font-weight="700">{escape(diff_summary)}</text>

      <rect x="542" y="0" width="122" height="58" rx="8" fill="#131926" stroke="#2C2547"/>
      <text x="556" y="20" fill="#64748B" font-family="Consolas, 'JetBrains Mono', monospace" font-size="9.5" font-weight="700">REPOSITORIES</text>
      <text x="556" y="46" fill="#A78BFA" font-size="24" font-weight="800">{active_repos}</text>
      <text x="584" y="44" fill="#64748B" font-size="10.5">tracked</text>
    </g>

    <!-- Column Headers -->
    <text x="54" y="188" fill="#475569" font-family="Consolas, 'JetBrains Mono', monospace" font-size="9.5" font-weight="700">REPOSITORY</text>
    <text x="378" y="188" fill="#475569" font-family="Consolas, 'JetBrains Mono', monospace" font-size="9.5" font-weight="700" text-anchor="middle">MERGED</text>
    <text x="466" y="188" fill="#475569" font-family="Consolas, 'JetBrains Mono', monospace" font-size="9.5" font-weight="700" text-anchor="middle">OPEN</text>
    <text x="538" y="188" fill="#475569" font-family="Consolas, 'JetBrains Mono', monospace" font-size="9.5" font-weight="700" text-anchor="middle">LATEST</text>
    <text x="692" y="188" fill="#475569" font-family="Consolas, 'JetBrains Mono', monospace" font-size="9.5" font-weight="700" text-anchor="end">DIFF (+ / -)</text>

    {''.join(rows_svg)}

    <!-- Right Panel Container: Production Edge & MCP Registry -->
    <rect x="730" y="76" width="442" height="344" rx="11" fill="#0E131D" stroke="#222B3D" stroke-width="1.2"/>
    <text x="746" y="100" fill="#34D399" font-family="Consolas, 'JetBrains Mono', monospace" font-size="10.5" font-weight="700" letter-spacing="1.2">PRODUCTION EDGE &amp; OFFICIAL REGISTRY PROBES</text>

    {''.join(probe_cards)}
    {registry_card}
  </g>
</svg>
'''


def _render_mobile(snapshot: TelemetrySnapshot, synced_label: str) -> str:
    w, h = 600, 768
    diff_summary = (
        f'+{_fmt_num(snapshot.total_additions)} / -{_fmt_num(snapshot.total_deletions)}'
        if snapshot.any_diff_available
        else 'LIVE SYNC'
    )

    rows_svg: list[str] = []
    for idx, r in enumerate(snapshot.repos):
        y = 186 + idx * 42
        bg_fill = '#121722' if idx % 2 == 0 else '#0F141E'
        status_parts = []
        if r.merged_count:
            status_parts.append(f'{r.merged_count}M')
        if r.open_count:
            status_parts.append(f'{r.open_count}O')
        badge = ' · '.join(status_parts) if status_parts else '—'
        diff_txt = f'+{_fmt_num(r.additions)}/-{_fmt_num(r.deletions)}' if r.diff_available and (r.additions or r.deletions) else ''
        rows_svg.append(
            f'<g>'
            f'<rect x="28" y="{y}" width="544" height="36" rx="7" fill="{bg_fill}" stroke="#1E2636"/>'
            f'<rect x="28" y="{y}" width="3.5" height="36" rx="1.5" fill="{r.accent}"/>'
            f'<text x="42" y="{y + 22}" fill="#F1F5F9" font-family="Consolas, \'JetBrains Mono\', monospace" font-size="11" font-weight="700">{escape(_short_repo(r.repo, max_len=32))}</text>'
            f'<text x="456" y="{y + 22}" fill="#34D399" font-family="Consolas, \'JetBrains Mono\', monospace" font-size="10.5" font-weight="700" text-anchor="end">{escape(badge)}</text>'
            f'<text x="560" y="{y + 22}" fill="#94A3B8" font-family="Consolas, \'JetBrains Mono\', monospace" font-size="10" text-anchor="end">{escape(diff_txt)}</text>'
            f'</g>'
        )

    probe_svg: list[str] = []
    for idx, p in enumerate(snapshot.probes):
        py = 432 + idx * 78
        st = f'{p.status_code} OK · {p.latency_ms}ms' if p.ok else 'ERR'
        fg = '#34D399' if p.ok else '#F87171'
        probe_svg.append(
            f'<g transform="translate(28, {py})">'
            f'<rect x="0" y="0" width="544" height="68" rx="8" fill="#131926" stroke="#253047"/>'
            f'<rect x="0" y="0" width="4" height="68" rx="2" fill="{p.accent}"/>'
            f'<text x="16" y="24" fill="#F8FAFC" font-size="13.5" font-weight="700">{escape(p.name)}</text>'
            f'<text x="530" y="24" fill="{fg}" font-family="Consolas, \'JetBrains Mono\', monospace" font-size="11" font-weight="700" text-anchor="end">{escape(st)}</text>'
            f'<text x="16" y="48" fill="#94A3B8" font-family="Consolas, \'JetBrains Mono\', monospace" font-size="10.5">{escape(p.host)}</text>'
            f'</g>'
        )

    reg = snapshot.registry
    reg_pill = f'{reg.status} · v{reg.version}' if reg.ok else 'UNREACHABLE'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="tel-m-title tel-m-desc">
  <title id="tel-m-title">Live Upstream OSS and Edge Infrastructure Telemetry</title>
  <desc id="tel-m-desc">{snapshot.total_merged} merged and {snapshot.total_open} open upstream PRs plus live Cloudflare Worker and Official MCP Registry probes.</desc>
  <defs>
    <pattern id="tel-m-grid" width="28" height="28" patternUnits="userSpaceOnUse">
      <path d="M 28 0 L 0 0 0 28" fill="none" stroke="#161B24" stroke-width="1"/>
    </pattern>
  </defs>
  <rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="14" fill="#0B0E14" stroke="#252C3A" stroke-width="2"/>
  <rect x="2" y="2" width="{w - 4}" height="{h - 4}" rx="13" fill="url(#tel-m-grid)"/>
  <g font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif">
    <rect x="24" y="20" width="552" height="54" rx="9" fill="#101520" stroke="#242D40"/>
    <circle cx="42" cy="40" r="4" fill="#34D399"/>
    <text x="54" y="44" fill="#E2E8F0" font-family="Consolas, 'JetBrains Mono', monospace" font-size="11" font-weight="700">LIVE TELEMETRY // OSS &amp; EDGE INFRA</text>
    <text x="42" y="64" fill="#64748B" font-family="Consolas, 'JetBrains Mono', monospace" font-size="10">SYNCED {escape(synced_label)} · 4H AUTO-CRON</text>

    <!-- KPI Row -->
    <g transform="translate(24, 88)">
      <rect x="0" y="0" width="166" height="58" rx="8" fill="#131926" stroke="#1F3A32"/>
      <text x="12" y="20" fill="#64748B" font-family="Consolas, monospace" font-size="9.5" font-weight="700">MERGED PRS</text>
      <text x="12" y="46" fill="#34D399" font-size="23" font-weight="800">{snapshot.total_merged}</text>

      <rect x="178" y="0" width="166" height="58" rx="8" fill="#131926" stroke="#3F311A"/>
      <text x="190" y="20" fill="#64748B" font-family="Consolas, monospace" font-size="9.5" font-weight="700">OPEN IN REVIEW</text>
      <text x="190" y="46" fill="#E5A93C" font-size="23" font-weight="800">{snapshot.total_open}</text>

      <rect x="356" y="0" width="196" height="58" rx="8" fill="#131926" stroke="#24334D"/>
      <text x="368" y="20" fill="#64748B" font-family="Consolas, monospace" font-size="9.5" font-weight="700">MERGED DIFF</text>
      <text x="368" y="44" fill="#60A5FA" font-family="Consolas, monospace" font-size="14" font-weight="700">{escape(diff_summary)}</text>
    </g>

    <text x="28" y="174" fill="#60A5FA" font-family="Consolas, monospace" font-size="10" font-weight="700">UPSTREAM REPOSITORIES (M = MERGED · O = OPEN)</text>
    {''.join(rows_svg)}

    <text x="28" y="420" fill="#34D399" font-family="Consolas, monospace" font-size="10" font-weight="700">EDGE WORKERS &amp; OFFICIAL MCP REGISTRY</text>
    {''.join(probe_svg)}

    <g transform="translate(28, 666)">
      <rect x="0" y="0" width="544" height="74" rx="8" fill="#131926" stroke="#362A59"/>
      <rect x="0" y="0" width="4" height="74" rx="2" fill="#A78BFA"/>
      <text x="16" y="24" fill="#F8FAFC" font-size="13.5" font-weight="700">Official MCP Registry</text>
      <text x="530" y="24" fill="#C4B5FD" font-family="Consolas, monospace" font-size="11" font-weight="700" text-anchor="end">{escape(reg_pill)}</text>
      <text x="16" y="46" fill="#C4B5FD" font-family="Consolas, monospace" font-size="10.5">{escape(reg.server_id)}</text>
      <text x="16" y="63" fill="#94A3B8" font-size="10.5">Transport: {escape(reg.transport)}</text>
    </g>
  </g>
</svg>
'''


def collect_snapshot(username: str, token: str | None = None) -> TelemetrySnapshot:
    repos = fetch_upstream_prs(username, token=token)
    probes, registry = probe_edge_infra()
    return TelemetrySnapshot(
        username=username,
        synced_at=datetime.now(timezone.utc),
        repos=repos,
        probes=probes,
        registry=registry,
    )


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username', default='yashwant938')
    parser.add_argument(
        '--output',
        type=Path,
        default=Path(__file__).resolve().parents[1] / 'assets' / 'telemetry-panel.svg',
    )
    args = parser.parse_args(argv)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', args.username):
        parser.error('Invalid GitHub username')

    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    snapshot = collect_snapshot(args.username, token=token)
    outputs = {
        args.output: render_telemetry_svg(snapshot, mobile=False),
        args.output.with_name('telemetry-panel-mobile.svg'): render_telemetry_svg(snapshot, mobile=True),
    }
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.svg.tmp')
        tmp.write_text(content, encoding='utf-8', newline='\n')
        tmp.replace(path)

    print(
        f'Updated {args.output.name}: {snapshot.total_merged} merged, {snapshot.total_open} open '
        f'(+{snapshot.total_additions}/-{snapshot.total_deletions}), '
        f'probes={[f"{p.name}:{p.status_code}/{p.latency_ms}ms" for p in snapshot.probes]}, '
        f'registry={snapshot.registry.status}@v{snapshot.registry.version}'
    )


if __name__ == '__main__':
    main()
