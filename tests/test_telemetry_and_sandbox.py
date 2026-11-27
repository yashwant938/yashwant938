"""Offline unit tests for live OSS/Edge telemetry rendering and interactive sandbox safety."""

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import sandbox_runner
import telemetry


class TelemetryRenderTests(unittest.TestCase):
    def _sample_snapshot(self):
        return telemetry.TelemetrySnapshot(
            username='yashwant938',
            synced_at=datetime(2026, 11, 28, 0, 0, tzinfo=timezone.utc),
            repos=(
                telemetry.RepoPRSummary('qualcomm/eld', 'LLVM / ELF Linker', '#60A5FA', 5, 3, 315, 43, 2437, 'OPEN', True),
                telemetry.RepoPRSummary('deepset-ai/haystack-core-integrations', 'GenAI / Haystack', '#E5A93C', 2, 0, 131, 8, 4297, 'MERGED', True),
                telemetry.RepoPRSummary('IBM/mcp-context-forge', 'MCP Gateway', '#A78BFA', 0, 6, 0, 0, 7473, 'OPEN', False),
                telemetry.RepoPRSummary('strands-agents/harness-sdk', 'Agent SDK / MCP', '#2DD4BF', 0, 1, 28, 4, 6370, 'OPEN', True),
                telemetry.RepoPRSummary('react-chatbotify/react-chatbotify', 'Security / UI', '#34D399', 0, 1, 92, 12, 366, 'OPEN', True),
            ),
            probes=(
                telemetry.EdgeProbe('ArchGuard MCP Worker', 'arch-guard-mcp.yashwant938.workers.dev/mcp', True, 200, 34, 'MCP 2025-03-26 · 6 HTTP tools · 4 res · 3 prompts', '#34D399'),
                telemetry.EdgeProbe('System Design Atlas', 'system-design-guide.yashwant938.workers.dev', True, 200, 52, 'Cloudflare Edge · 14 modules · 100 lessons · 6 labs', '#60A5FA'),
            ),
            registry=telemetry.RegistryStatus('io.github.yashwant938/arch-guard-mc', '1.0.0', 'ACTIVE', 'streamable-http', True),
        )

    def test_merged_diff_totals_exclude_unmerged_repos(self):
        snap = self._sample_snapshot()
        self.assertEqual(snap.total_merged, 7)
        self.assertEqual(snap.total_open, 11)
        # Only qualcomm/eld (+315/-43) and haystack (+131/-8) have merged PRs.
        self.assertEqual(snap.total_additions, 446)
        self.assertEqual(snap.total_deletions, 51)

    def test_desktop_and_mobile_svgs_are_valid_xml_with_metrics(self):
        snap = self._sample_snapshot()
        for mobile in (False, True):
            with self.subTest(mobile=mobile):
                svg = telemetry.render_telemetry_svg(snap, mobile=mobile)
                ET.fromstring(svg)
                self.assertIn('200 OK', svg)
                self.assertIn('ACTIVE · v1.0.0', svg)
                self.assertIn('+446', svg)


class SandboxSafetyAndParsingTests(unittest.TestCase):
    def test_issue_form_parser_extracts_sections(self):
        body = (
            '### Audit Mode\n\nSQL DDL Migration Audit (Expand-Contract)\n\n'
            '### SQL Dialect (for SQL mode)\n\npostgres\n\n'
            '### SQL DDL or Dependency Edges / Code Snippet\n\n'
            'CREATE INDEX idx_a ON t(a);\n'
        )
        parsed = sandbox_runner.parse_issue_form(body)
        self.assertEqual(parsed['sql dialect (for sql mode)'], 'postgres')
        self.assertIn('CREATE INDEX', parsed['sql ddl or dependency edges / code snippet'])

    def test_architecture_edge_parser_and_tarjan_scc_cycle_detection(self):
        edges = 'src/auth.js -> src/users.js\nsrc/users.js -> src/billing.js\nsrc/billing.js -> src/auth.js\n'
        files = sandbox_runner.parse_architecture_payload(edges)
        self.assertEqual(len(files), 3)
        res = sandbox_runner._fallback_tarjan_scc(files)
        self.assertEqual(len(res['circularDependencies']), 1)
        self.assertIn('graph LR', res['mermaidGraph'])

    def test_sql_fallback_flags_blocking_ddl(self):
        sql = 'CREATE INDEX idx_u ON orders(user_id);\nALTER TABLE orders ADD COLUMN tenant_id TEXT NOT NULL;'
        res = sandbox_runner._fallback_sql_audit(sql, 'postgres')
        self.assertEqual(res['verdict'], 'BLOCK_DEPLOY')
        self.assertEqual(res['severityCounts']['CRITICAL'], 2)

    def test_cpp_safety_guard_blocks_unsafe_constructs_and_allows_safe_code(self):
        self.assertIsNone(sandbox_runner.validate_cpp_snippet('#include <cstdint>\nuint64_t f(uint64_t n){return n*n;}'))
        for bad in (
            '#include "/etc/passwd"\nint f(){return 0;}',
            '#include <../secret>\nint f(){return 0;}',
            '#include <fstream>\nint f(){return 0;}',
            '#pragma message("hi")\nint f(){return 0;}',
            'int f(){ asm("nop"); return 0; }',
            'int f(){ return system("id"); }',
        ):
            with self.subTest(bad=bad):
                self.assertIsNotNone(sandbox_runner.validate_cpp_snippet(bad))

    def test_clean_assembly_counts_instructions_only(self):
        sample = '\n'.join([
            '\t.text',
            '\t.globl sum',
            'sum:',
            '\tlea rax, [rdi - 1]',
            '\tmul rdi',
            '\tret',
            '\t.size sum, .-sum',
        ])
        lines, count = sandbox_runner.clean_assembly(sample)
        self.assertEqual(count, 3)
        self.assertEqual(lines[0], 'sum:')

    def test_sandbox_svg_renders_valid_xml_desktop_and_mobile(self):
        res = sandbox_runner.SandboxResult(
            mode='ARCHGUARD_SQL',
            badge_label='ARCHGUARD MCP · SQL DDL',
            accent='#E5A93C',
            author='yashwant938',
            issue_number=1,
            ran_at=datetime(2026, 11, 28, 0, 0, tzinfo=timezone.utc),
            headline='Audited postgres migration · 2 critical lock(s)',
            metric_pill='BLOCK_DEPLOY · 2 CRITICAL',
            preview_lines=('$ mcp call check_migration_safety', 'verdict: BLOCK_DEPLOY', '[MIG-001] Blocking index', 'plan: 3-phase emitted'),
            comment_markdown='ok',
        )
        for mobile in (False, True):
            with self.subTest(mobile=mobile):
                svg = sandbox_runner.render_sandbox_svg(res, mobile=mobile)
                ET.fromstring(svg)
                self.assertIn('BLOCK_DEPLOY', svg)


if __name__ == '__main__':
    unittest.main()
