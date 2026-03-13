#!/usr/bin/env python3
"""
HVDC Knowledge MCP — Validation Suite
서버 배포 전 lint / compile / 기능 테스트를 한 번에 수행합니다.

사용법:
    python scripts/validate.py          # 전체 검증
    python scripts/validate.py --quick  # 컴파일 + 핵심 테스트만
"""

import argparse
import asyncio
import contextlib
from functools import partial
import http.server
import importlib
import json
import os
import platform
import socket
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from urllib.request import Request, urlopen

# ──────────────────────────────────────────
# Windows ANSI 색상 활성화
# ──────────────────────────────────────────
if platform.system() == "Windows":
    os.system("")  # Windows Terminal에서 ANSI escape 활성화

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

passed = 0
failed = 0
warnings = 0

# subprocess 공통 옵션 (Windows cp949 문제 방지)
_SP_OPTS = {"capture_output": True, "text": True, "encoding": "utf-8", "errors": "replace"}


def ok(msg: str):
    global passed
    passed += 1
    print(f"  {GREEN}PASS{RESET}  {msg}")


def fail(msg: str):
    global failed
    failed += 1
    print(f"  {RED}FAIL{RESET}  {msg}")


def warn(msg: str):
    global warnings
    warnings += 1
    print(f"  {YELLOW}WARN{RESET}  {msg}")


def section(title: str):
    print(f"\n{BOLD}{CYAN}-- {title} --{RESET}")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@contextlib.contextmanager
def serve_directory(directory: Path):
    """Serve a fixture directory over local HTTP for file_param tests."""

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args):
            return

    handler = partial(QuietHandler, directory=str(directory))

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    with ReusableTCPServer(("127.0.0.1", 0), handler) as httpd:
        port = int(httpd.server_address[1])
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{port}"
        finally:
            httpd.shutdown()
            thread.join(timeout=5)


@contextlib.contextmanager
def run_streamable_http_server(root: Path, *, port: int):
    """Start the MCP server in streamable-http mode for self-test validation."""
    base_url = f"http://127.0.0.1:{port}"
    proc = subprocess.Popen(
        [
            sys.executable,
            str(root / "server.py"),
            "--transport",
            "streamable-http",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--public-base-url",
            base_url,
        ],
        cwd=str(root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            with urlopen(f"{base_url}/health", timeout=1) as response:
                if response.status == 200:
                    break
        except Exception:
            time.sleep(0.25)
    else:
        proc.terminate()
        proc.wait(timeout=5)
        raise RuntimeError("Timed out waiting for streamable-http server to start.")

    try:
        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


# ──────────────────────────────────────────
# Phase 1: 정적 검증
# ──────────────────────────────────────────
def check_compile():
    """py_compile로 문법 검증"""
    section("Phase 1: Compile Check")
    root = Path(__file__).parent.parent
    python_files = [
        root / "server.py",
        root / "install.py",
        root / "scripts" / "deploy.py",
        root / "scripts" / "remote_mcp.py",
        root / "scripts" / "railway_run.py",
        root / "hvdc_ops" / "__init__.py",
        root / "hvdc_ops" / "ingest.py",
        root / "hvdc_ops" / "rules.py",
        root / "hvdc_ops" / "snapshots.py",
        root / "hvdc_ops" / "reports.py",
    ]
    for path in python_files:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(path)],
                **_SP_OPTS,
            )
            if result.returncode == 0:
                ok(f"{path.relative_to(root)} compile OK")
            else:
                fail(f"{path.relative_to(root)} compile FAIL: {result.stderr.strip()}")
        except Exception as e:
            fail(f"{path.relative_to(root)} compile error: {e}")


def check_lint():
    """ruff 린트 검사 (설치되어 있을 때만)"""
    section("Phase 2: Lint Check (ruff)")
    server_path = Path(__file__).parent.parent / "server.py"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", str(server_path)],
            **_SP_OPTS,
        )
        if result.returncode == 0:
            ok("ruff lint passed")
        else:
            fail(f"ruff lint errors:\n{result.stdout.strip()}")
    except FileNotFoundError:
        warn("ruff not installed - skip (pip install ruff)")


def check_imports():
    """핵심 의존성 import 검증"""
    section("Phase 3: Import Check")
    deps = ["mcp.server.fastmcp", "pydantic", "pandas", "openpyxl", "uvicorn", "json", "pathlib"]
    for dep in deps:
        try:
            importlib.import_module(dep)
            ok(f"import {dep}")
        except ImportError:
            fail(f"import {dep} FAIL - pip install -r requirements.txt")


# ──────────────────────────────────────────
# Phase 2: 기능 테스트
# ──────────────────────────────────────────
def check_tools():
    """MCP 도구 기능 통합 테스트"""
    section("Phase 4: Tool Integration Tests")

    root = Path(__file__).parent.parent
    sys.path.insert(0, str(root))
    try:
        import server
    except Exception as e:
        fail(f"server.py import FAIL: {e}")
        return

    loop = asyncio.new_event_loop()

    # Test 1: domain summary
    try:
        result = loop.run_until_complete(server.hvdc_get_domain_summary())
        assert "MOSB" in result and "Flow Code" in result
        ok("hvdc_get_domain_summary - MOSB + Flow Code")
    except Exception as e:
        fail(f"hvdc_get_domain_summary: {e}")

    # Test 2: node info (전체)
    try:
        result = loop.run_until_complete(
            server.hvdc_get_node_info(server.NodeQueryInput())
        )
        data = json.loads(result)
        assert len(data) == 8
        ok(f"hvdc_get_node_info(all) - {len(data)} nodes")
    except Exception as e:
        fail(f"hvdc_get_node_info(all): {e}")

    # Test 3: node info (DAS — offshore rule)
    try:
        result = loop.run_until_complete(
            server.hvdc_get_node_info(server.NodeQueryInput(node_name="DAS"))
        )
        data = json.loads(result)
        assert "flow_code_rule" in data["DAS"]
        ok("hvdc_get_node_info(DAS) - flow_code_rule added")
    except Exception as e:
        fail(f"hvdc_get_node_info(DAS): {e}")

    # Test 4: node info (MIR — onshore DOT rule)
    try:
        result = loop.run_until_complete(
            server.hvdc_get_node_info(server.NodeQueryInput(node_name="MIR"))
        )
        data = json.loads(result)
        assert "dot_rule" in data["MIR"]
        ok("hvdc_get_node_info(MIR) - dot_rule added")
    except Exception as e:
        fail(f"hvdc_get_node_info(MIR): {e}")

    # Test 5: node info (없는 노드 — 에러 처리)
    try:
        result = loop.run_until_complete(
            server.hvdc_get_node_info(server.NodeQueryInput(node_name="INVALID"))
        )
        data = json.loads(result)
        assert "error" in data and "available" in data
        ok("hvdc_get_node_info(INVALID) - error + available")
    except Exception as e:
        fail(f"hvdc_get_node_info(INVALID): {e}")

    # Test 6: flow code (AGI -> min 3)
    try:
        result = loop.run_until_complete(
            server.hvdc_get_flow_code(server.FlowCodeInput(destination="AGI"))
        )
        data = json.loads(result)
        assert data["destination_validation"]["minimum_flow_code"] == 3
        ok("hvdc_get_flow_code(AGI) - min=3")
    except Exception as e:
        fail(f"hvdc_get_flow_code(AGI): {e}")

    # Test 7: flow code (MIR -> min 1)
    try:
        result = loop.run_until_complete(
            server.hvdc_get_flow_code(server.FlowCodeInput(destination="MIR"))
        )
        data = json.loads(result)
        assert data["destination_validation"]["minimum_flow_code"] == 1
        ok("hvdc_get_flow_code(MIR) - min=1")
    except Exception as e:
        fail(f"hvdc_get_flow_code(MIR): {e}")

    # Test 8: search
    try:
        result = loop.run_until_complete(
            server.hvdc_search_docs(server.SearchInput(keyword="MOSB"))
        )
        data = json.loads(result)
        assert data.get("total_files_matched", 0) > 0
        ok(f"hvdc_search_docs('MOSB') - {data['total_files_matched']} files")
    except Exception as e:
        fail(f"hvdc_search_docs: {e}")

    # Test 9: list docs
    try:
        result = loop.run_until_complete(server.hvdc_list_docs())
        data = json.loads(result)
        assert data["total_files"] > 0
        ok(f"hvdc_list_docs - {data['total_files']} docs")
    except Exception as e:
        fail(f"hvdc_list_docs: {e}")

    # Test 9a: company knowledge search
    try:
        result = loop.run_until_complete(
            server.search(server.CompanyKnowledgeSearchInput(query="MOSB"))
        )
        payload = json.loads(result.content[0].text)
        assert payload["results"] and all("id" in item and "url" in item for item in payload["results"])
        ok(f"search('MOSB') - {len(payload['results'])} indexed docs")
    except Exception as e:
        fail(f"search('MOSB'): {e}")

    # Test 9b: company knowledge fetch
    try:
        search_result = loop.run_until_complete(
            server.search(server.CompanyKnowledgeSearchInput(query="Flow Code"))
        )
        search_payload = json.loads(search_result.content[0].text)
        first_id = search_payload["results"][0]["id"]
        fetch_result = loop.run_until_complete(
            server.fetch(server.CompanyKnowledgeFetchInput(id=first_id))
        )
        fetch_payload = json.loads(fetch_result.content[0].text)
        assert fetch_payload["id"] == first_id and fetch_payload["text"]
        ok(f"fetch('{first_id}') - content loaded")
    except Exception as e:
        fail(f"fetch(company doc): {e}")

    # Test 9c: root status payload includes dashboard routes
    try:
        payload = server._build_root_status_payload()
        assert payload["dashboard_path"] == "/dashboard"
        assert payload["dashboard_status_path"] == "/dashboard/status"
        assert payload["dashboard_self_test_path"] == server.DASHBOARD_SELF_TEST_PATH
        assert "hvdc_render_backlog_upload_widget" in payload["tools"]
        assert payload["chatgpt_upload"]["resource_uri"] == server.BACKLOG_UPLOAD_WIDGET_URI
        assert payload["chatgpt_upload"]["widget_domain_configured"] is True
        assert payload["chatgpt_upload"]["widget_csp_configured"] is True
        ok("root status payload - dashboard routes")
    except Exception as e:
        fail(f"root status payload: {e}")

    # Test 9d: dashboard payload includes summary, connectivity, history
    try:
        payload = loop.run_until_complete(server._build_dashboard_payload())
        assert "summary" in payload and "health_score" in payload["summary"]
        assert "connectivity" in payload and "local_health" in payload["connectivity"]
        assert "history" in payload and "trend" in payload["history"]
        assert "surfaces" in payload and payload["surfaces"]["summary"]["total"] >= 3
        assert "deployment" in payload["runtime"] and "provider_label" in payload["runtime"]["deployment"]
        assert payload["connectivity"]["local_health"]["ok"] is not None
        assert payload["server"]["chatgpt_upload"]["widget_tool_name"] == "hvdc_render_backlog_upload_widget"
        assert payload["server"]["chatgpt_upload"]["template_exists"] is True
        assert payload["server"]["chatgpt_upload"]["widget_domain_configured"] is True
        assert payload["server"]["chatgpt_upload"]["widget_csp_configured"] is True
        assert any(item["id"] == "cursor" for item in payload["surfaces"]["items"])
        assert any(item["id"] == "codex" for item in payload["surfaces"]["items"])
        ok("dashboard payload - summary/connectivity/history")
    except Exception as e:
        fail(f"dashboard payload: {e}")

    # Test 9e: dashboard self-test route returns MCP checks
    try:
        response = loop.run_until_complete(
            server.dashboard_self_test(
                SimpleNamespace(query_params={"target": "both", "include_tool_calls": "false"})
            )
        )
        payload = json.loads(response.body)
        assert payload["status"] in {"pass", "warning", "fail"}
        assert any(check["name"] == "connector freshness" for check in payload["checks"])
        ok("dashboard self-test route - JSON payload")
    except Exception as e:
        fail(f"dashboard self-test route: {e}")

    # Test 10: KPI (전체)
    try:
        result = loop.run_until_complete(
            server.hvdc_get_kpi(server.KPIInput())
        )
        data = json.loads(result)
        assert "kpi_gates" in data and len(data["kpi_gates"]) == 7
        ok(f"hvdc_get_kpi(all) - {len(data['kpi_gates'])} KPIs")
    except Exception as e:
        fail(f"hvdc_get_kpi: {e}")

    # Test 11: KPI (개별)
    try:
        result = loop.run_until_complete(
            server.hvdc_get_kpi(server.KPIInput(kpi_name="invoice_ocr"))
        )
        data = json.loads(result)
        assert data["invoice_ocr"]["threshold"] == 98.0
        ok("hvdc_get_kpi(invoice_ocr) - threshold 98.0")
    except Exception as e:
        fail(f"hvdc_get_kpi(invoice_ocr): {e}")

    # Test 12: regulations (전체)
    try:
        result = loop.run_until_complete(
            server.hvdc_get_regulations(server.RegulationInput())
        )
        data = json.loads(result)
        assert "regulations" in data and len(data["regulations"]) == 6
        ok(f"hvdc_get_regulations(all) - {len(data['regulations'])} regs")
    except Exception as e:
        fail(f"hvdc_get_regulations: {e}")

    # Test 13: regulations (개별 — DOT)
    try:
        result = loop.run_until_complete(
            server.hvdc_get_regulations(server.RegulationInput(regulation_name="DOT"))
        )
        data = json.loads(result)
        assert "DOT" in data and data["DOT"]["weight_threshold_tons"] == 90
        ok("hvdc_get_regulations(DOT) - weight 90t")
    except Exception as e:
        fail(f"hvdc_get_regulations(DOT): {e}")

    # Test 14: HS code
    try:
        result = loop.run_until_complete(
            server.hvdc_hs_code_lookup(server.HSCodeInput(query="850440"))
        )
        data = json.loads(result)
        assert "matched" in data and "850440" in data["matched"]
        ok("hvdc_hs_code_lookup('850440') - transformer matched")
    except Exception as e:
        fail(f"hvdc_hs_code_lookup: {e}")

    fixtures_dir = root / "tests" / "fixtures"
    sample_csv = fixtures_dir / "analysis_backlog_sample.csv"
    candidate_csv = fixtures_dir / "analysis_backlog_candidate.csv"
    sample_xlsx = fixtures_dir / "analysis_backlog_sample.xlsx"

    # Test 15: shipment case from CSV file param
    try:
        with serve_directory(fixtures_dir) as base_url:
            result = loop.run_until_complete(
                server.hvdc_analyze_shipment_case(
                    server.ShipmentCaseInput(
                        file=server.FileParam(
                            download_url=f"{base_url}/{sample_csv.name}",
                            file_id="sample-csv",
                        ),
                        shipment_id="AGI-001",
                    )
                )
            )
        payload = result.structuredContent
        assert payload["flow_assessment"]["recommended_flow_code"] == 3
        assert payload["verdict"]["status"] == "ZERO"
        assert "markdown_summary" in payload and payload["markdown_summary"]
        ok("hvdc_analyze_shipment_case(file param) - AGI flow upgrade + ZERO")
    except Exception as e:
        fail(f"hvdc_analyze_shipment_case(file param): {e}")

    # Test 16: shipment case from XLSX local path with sheet selection
    try:
        result = loop.run_until_complete(
            server.hvdc_analyze_shipment_case(
                server.ShipmentCaseInput(
                    local_path=str(sample_xlsx),
                    sheet_name="Shipments",
                    shipment_id="MIR-001",
                )
            )
        )
        payload = result.structuredContent
        assert payload["zero_gates"]["gate_results"]["DOT permit"]["status"] == "block"
        assert payload["input_source"]["sheet_name"] == "Shipments"
        ok("hvdc_analyze_shipment_case(local xlsx) - DOT block + sheet selection")
    except Exception as e:
        fail(f"hvdc_analyze_shipment_case(local xlsx): {e}")

    # Test 17: shipment case column_map override
    try:
        result = loop.run_until_complete(
            server.hvdc_analyze_shipment_case(
                server.ShipmentCaseInput(
                    shipment={
                        "Ref": "INLINE-001",
                        "Dest Code": "AGI",
                        "Stage": "At WH pending site",
                        "Gross Tons": 40,
                        "Port Stamp": "2026-03-03",
                    },
                    column_map={
                        "shipment_id": "Ref",
                        "destination": "Dest Code",
                        "status": "Stage",
                        "weight_tons": "Gross Tons",
                        "port_date": "Port Stamp",
                    },
                )
            )
        )
        payload = result.structuredContent
        assert payload["normalized_case"]["shipment_id"] == "INLINE-001"
        assert payload["flow_assessment"]["recommended_flow_code"] == 3
        ok("hvdc_analyze_shipment_case(column_map) - override applied")
    except Exception as e:
        fail(f"hvdc_analyze_shipment_case(column_map): {e}")

    # Test 17b: backlog upload widget render tool + resource registration
    try:
        result = loop.run_until_complete(
            server.hvdc_render_backlog_upload_widget(
                server.BacklogUploadWidgetInput(
                    snapshot_name="ops-widget",
                    sheet_name="Shipments",
                    column_map={"destination": "Site"},
                )
            )
        )
        payload = result.structuredContent
        assert payload["defaults"]["snapshot_name"] == "ops-widget"
        assert payload["defaults"]["sheet_name"] == "Shipments"
        assert payload["widget_uri"] == server.BACKLOG_UPLOAD_WIDGET_URI
        tools = loop.run_until_complete(server.mcp.list_tools())
        widget_tool = next(tool for tool in tools if tool.name == "hvdc_render_backlog_upload_widget")
        assert widget_tool.meta["openai/outputTemplate"] == server.BACKLOG_UPLOAD_WIDGET_URI
        assert widget_tool.meta["ui"]["resourceUri"] == server.BACKLOG_UPLOAD_WIDGET_URI
        resources = loop.run_until_complete(server.mcp.list_resources())
        resource = next(resource for resource in resources if str(resource.uri) == server.BACKLOG_UPLOAD_WIDGET_URI)
        assert resource.meta["ui"]["domain"]
        assert "connectDomains" in resource.meta["ui"]["csp"]
        assert "resourceDomains" in resource.meta["ui"]["csp"]
        assert resource.meta["openai/widgetDomain"] == resource.meta["ui"]["domain"]
        assert "connect_domains" in resource.meta["openai/widgetCSP"]
        widget_html = server.backlog_upload_widget_resource()
        assert "uploadFile" in widget_html
        assert "getFileDownloadUrl" in widget_html
        assert "hvdc_analyze_backlog_batch" in widget_html
        ok("hvdc_render_backlog_upload_widget - render tool + resource registered")
    except Exception as e:
        fail(f"hvdc_render_backlog_upload_widget: {e}")

    # Test 17c: sandbox file path explains widget upload flow
    try:
        loop.run_until_complete(
            server.hvdc_analyze_backlog_batch(
                server.BacklogBatchInput(
                    file=server.FileParam(
                        file_id="sandbox-file",
                        download_url="sandbox:/mnt/data/HVDC_STATUS.xlsx",
                    ),
                    snapshot_name="ops-sandbox",
                )
            )
        )
        fail("hvdc_analyze_backlog_batch(sandbox): expected failure")
    except Exception as e:
        message = str(e)
        assert "sandbox" in message
        assert "hvdc_render_backlog_upload_widget" in message
        ok("hvdc_analyze_backlog_batch(sandbox) - actionable error message")

    # Test 18: backlog batch + snapshot persistence
    try:
        result = loop.run_until_complete(
            server.hvdc_analyze_backlog_batch(
                server.BacklogBatchInput(
                    local_path=str(sample_csv),
                    snapshot_name="ops-baseline",
                )
            )
        )
        payload = result.structuredContent
        assert payload["totals"]["total_rows"] == 5
        assert payload["totals"]["zero_rows"] >= 1
        ok("hvdc_analyze_backlog_batch - snapshot saved")
    except Exception as e:
        fail(f"hvdc_analyze_backlog_batch(baseline): {e}")

    # Test 19: snapshot overwrite + candidate snapshot
    try:
        overwrite_first = loop.run_until_complete(
            server.hvdc_analyze_backlog_batch(
                server.BacklogBatchInput(
                    local_path=str(sample_csv),
                    snapshot_name="ops-overwrite",
                )
            )
        )
        overwrite_second = loop.run_until_complete(
            server.hvdc_analyze_backlog_batch(
                server.BacklogBatchInput(
                    local_path=str(candidate_csv),
                    snapshot_name="ops-overwrite",
                )
            )
        )
        candidate = loop.run_until_complete(
            server.hvdc_analyze_backlog_batch(
                server.BacklogBatchInput(
                    local_path=str(candidate_csv),
                    snapshot_name="ops-candidate",
                )
            )
        )
        assert overwrite_first.structuredContent["totals"]["total_rows"] == 5
        assert overwrite_second.structuredContent["totals"]["total_rows"] == 6
        assert candidate.structuredContent["totals"]["total_rows"] == 6
        ok("hvdc_analyze_backlog_batch - overwrite and candidate snapshot")
    except Exception as e:
        fail(f"hvdc_analyze_backlog_batch(overwrite): {e}")

    # Test 20: snapshot compare
    try:
        result = loop.run_until_complete(
            server.hvdc_compare_snapshots(
                server.SnapshotCompareInput(
                    baseline_snapshot="ops-baseline",
                    candidate_snapshot="ops-candidate",
                )
            )
        )
        payload = result.structuredContent
        assert payload["delta_totals"]["total_rows"] == 1
        assert "markdown_report" in payload and payload["markdown_report"]
        ok("hvdc_compare_snapshots - deltas computed")
    except Exception as e:
        fail(f"hvdc_compare_snapshots: {e}")

    # Test 21: ZERO gate missing fields -> not_evaluated
    try:
        result = loop.run_until_complete(
            server.hvdc_zero_gate_check(
                server.ZeroGateContextInput(
                    destination="AGI",
                    gross_weight_tons=40,
                    weather_alert=False,
                )
            )
        )
        payload = result.structuredContent
        assert payload["gate_results"]["FANR permit"]["status"] == "not_evaluated"
        assert payload["verdict"]["status"] == "WARNING"
        ok("hvdc_zero_gate_check - not_evaluated behavior")
    except Exception as e:
        fail(f"hvdc_zero_gate_check: {e}")

    # Test 22: self-test detects stale connector URL
    state_backup = server.REMOTE_STATE_PATH.read_text(encoding="utf-8") if server.REMOTE_STATE_PATH.exists() else None
    runtime_backup = dict(server.RUNTIME)
    try:
        port = _free_port()
        with run_streamable_http_server(root, port=port) as base_url:
            server._configure_runtime("streamable-http", "127.0.0.1", port, base_url)
            server.REMOTE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            server.REMOTE_STATE_PATH.write_text(
                json.dumps(
                    {
                        "public_base_url": base_url,
                        "mcp_url": "https://stale-host.trycloudflare.com/mcp",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            result = loop.run_until_complete(
                server.hvdc_mcp_self_test(
                    server.SelfTestInput(target="both", include_tool_calls=True)
                )
            )
        payload = result.structuredContent
        freshness = next(check for check in payload["checks"] if check["name"] == "connector freshness")
        assert freshness["status"] == "warning"
        assert payload["status"] == "warning"
        ok("hvdc_mcp_self_test - stale connector detection")
    except Exception as e:
        fail(f"hvdc_mcp_self_test: {e}")
    finally:
        server.RUNTIME.update(runtime_backup)
        server._configure_runtime(
            runtime_backup["transport"],
            runtime_backup["host"],
            runtime_backup["port"],
            runtime_backup["public_base_url"],
        )
        if state_backup is None:
            if server.REMOTE_STATE_PATH.exists():
                server.REMOTE_STATE_PATH.unlink()
        else:
            server.REMOTE_STATE_PATH.write_text(state_backup, encoding="utf-8")

    # Test 23: internal base URL normalizes wildcard bind hosts
    runtime_backup = dict(server.RUNTIME)
    try:
        server.RUNTIME.update({"host": "0.0.0.0", "port": 8080})
        assert server._internal_base_url() == "http://127.0.0.1:8080"
        server.RUNTIME.update({"host": "::", "port": 8080})
        assert server._internal_base_url() == "http://[::1]:8080"
        ok("_internal_base_url - wildcard bind normalization")
    except Exception as e:
        fail(f"_internal_base_url: {e}")
    finally:
        server.RUNTIME.update(runtime_backup)

    # Test 24: self-test works through live /mcp without self-deadlock
    try:
        port = _free_port()
        with run_streamable_http_server(root, port=port) as base_url:
            initialize_body = {
                "jsonrpc": "2.0",
                "id": "initialize",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "validate", "version": "1.0"},
                },
            }
            tool_call_body = {
                "jsonrpc": "2.0",
                "id": "self-test",
                "method": "tools/call",
                "params": {
                    "name": "hvdc_mcp_self_test",
                    "arguments": {
                        "params": {"target": "both", "include_tool_calls": True},
                    },
                },
            }
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            }
            with urlopen(
                Request(
                    f"{base_url}/mcp",
                    data=json.dumps(initialize_body).encode("utf-8"),
                    headers=headers,
                    method="POST",
                ),
                timeout=30,
            ) as response:
                assert response.status == 200
            with urlopen(
                Request(
                    f"{base_url}/mcp",
                    data=json.dumps(tool_call_body).encode("utf-8"),
                    headers=headers,
                    method="POST",
                ),
                timeout=30,
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        structured = payload["result"]["structuredContent"]
        assert structured["status"] == "pass"
        assert not [check for check in structured["checks"] if check["status"] == "fail"]
        ok("hvdc_mcp_self_test - live /mcp self-call pass")
    except Exception as e:
        fail(f"hvdc_mcp_self_test(live-mcp): {e}")

    # Test 25: remote runner tailscale-funnel validation + config parsing
    try:
        import scripts.remote_mcp as remote_mcp

        remote_mcp.validate_mode(
            skip_tunnel=False,
            public_base_url="",
            tailscale_funnel=True,
            cloudflared_override=None,
        )
        sample_config = {
            "Web": {
                "c.tail7a10c8.ts.net:443": {
                    "Handlers": {
                        "/": {
                            "Proxy": "http://127.0.0.1:8001",
                        }
                    }
                }
            },
            "AllowFunnel": {
                "c.tail7a10c8.ts.net:443": True,
            },
        }
        url = remote_mcp.find_tailscale_funnel_url(sample_config, 8001)
        assert url == "https://c.tail7a10c8.ts.net"
        try:
            remote_mcp.validate_mode(
                skip_tunnel=True,
                public_base_url="https://example.com",
                tailscale_funnel=True,
                cloudflared_override=None,
            )
            raise AssertionError("expected ValueError for conflicting tunnel modes")
        except ValueError:
            pass
        ok("remote_mcp tailscale-funnel helpers - validation + URL parsing")
    except Exception as e:
        fail(f"remote_mcp tailscale-funnel helpers: {e}")

    loop.close()


def check_security():
    """보안 검증 — path traversal 차단 확인"""
    section("Phase 5: Security Tests")

    sys.path.insert(0, str(Path(__file__).parent.parent))
    import server
    from pydantic import ValidationError

    traversal_payloads = [
        "../../etc/passwd",
        "../server.py",
        "docs/../../../secret",
        "..\\..\\windows\\system32",
    ]

    for payload in traversal_payloads:
        try:
            server.DocQueryInput(filename=payload)
            fail(f"Path traversal NOT blocked: {payload}")
        except ValidationError:
            ok(f"Path traversal blocked: {payload}")

    try:
        external = Path("/etc/passwd")
        result = server._safe_resolve(external)
        assert result is None
        ok("_safe_resolve - external path blocked")
    except Exception as e:
        fail(f"_safe_resolve: {e}")


# ──────────────────────────────────────────
# Phase 3: 구조 검증
# ──────────────────────────────────────────
def check_structure():
    """프로젝트 파일 구조 검증"""
    section("Phase 6: Project Structure")

    root = Path(__file__).parent.parent
    required = [
        "server.py",
        "Dockerfile",
        "railway.json",
        "CLAUDE.md",
        "README.md",
        "WINDOWS_MULTI_PC_PACKAGE.md",
        "SETUP_WINDOWS_CLIENT.cmd",
        "SETUP_WINDOWS_FULL.cmd",
        "requirements.txt",
        "hvdc_ops/ingest.py",
        "hvdc_ops/rules.py",
        "scripts/remote_mcp.py",
        "scripts/railway_run.py",
        "scripts/cursor_mcp.cmd",
        "scripts/setup_windows_client.ps1",
        "scripts/build_windows_portable_bundle.ps1",
        ".codex/config.toml",
        ".claude/settings.json",
        ".cursor/mcp.json",
        ".cursor/rules/hvdc-domain-background.mdc",
        "tests/fixtures/analysis_backlog_sample.csv",
        "tests/fixtures/analysis_backlog_sample.xlsx",
        "widgets/hvdc_backlog_upload_v1.html",
    ]
    for f in required:
        path = root / f
        if path.exists():
            ok(f"{f} exists")
        else:
            fail(f"{f} missing")

    docs = root / "docs"
    if docs.exists():
        md_files = list(docs.rglob("*.md"))
        if len(md_files) >= 10:
            ok(f"docs/ - {len(md_files)} .md files")
        else:
            warn(f"docs/ - {len(md_files)} .md files (10+ recommended)")
    else:
        fail("docs/ directory missing")

    settings_path = root / ".claude" / "settings.json"
    if settings_path.exists():
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
            servers = data.get("mcpServers", {})
            if "hvdc-knowledge" in servers:
                srv = servers["hvdc-knowledge"]
                if srv.get("command") and srv.get("args"):
                    ok("settings.json - hvdc-knowledge config OK")
                else:
                    fail("settings.json - command/args missing")
            else:
                fail("settings.json - hvdc-knowledge key missing")
        except json.JSONDecodeError:
            fail("settings.json - JSON parse error")

    cursor_mcp_path = root / ".cursor" / "mcp.json"
    if cursor_mcp_path.exists():
        try:
            data = json.loads(cursor_mcp_path.read_text(encoding="utf-8"))
            servers = data.get("mcpServers", {})
            if "hvdc-knowledge" in servers:
                srv = servers["hvdc-knowledge"]
                args = srv.get("args") or []
                if srv.get("type") == "stdio" and srv.get("command") == "cmd.exe" and args:
                    ok("Cursor mcp.json - hvdc-knowledge stdio config OK")
                else:
                    fail("Cursor mcp.json - type/command/args missing")
            else:
                fail("Cursor mcp.json - hvdc-knowledge key missing")
        except json.JSONDecodeError:
            fail("Cursor mcp.json - JSON parse error")

    cursor_wrapper_path = root / "scripts" / "cursor_mcp.cmd"
    if cursor_wrapper_path.exists():
        try:
            result = subprocess.run(
                ["cmd.exe", "/d", "/c", str(cursor_wrapper_path), "--help"],
                **_SP_OPTS,
                cwd=str(root),
            )
            if result.returncode == 0 and "HVDC Knowledge MCP server" in result.stdout:
                ok("Cursor wrapper - server.py help reachable")
            else:
                fail("Cursor wrapper - failed to launch server.py --help")
        except Exception as e:
            fail(f"Cursor wrapper - execution error: {e}")

    codex_config_path = root / ".codex" / "config.toml"
    if codex_config_path.exists():
        try:
            text = codex_config_path.read_text(encoding="utf-8")
            if (
                "[mcp_servers.hvdc-knowledge]" in text
                and 'command = "cmd.exe"' in text
                and ".\\\\scripts\\\\cursor_mcp.cmd" in text
            ):
                ok("Codex config.toml - hvdc-knowledge project MCP config OK")
            else:
                fail("Codex config.toml - hvdc-knowledge MCP entry missing or invalid")
        except OSError as e:
            fail(f"Codex config.toml - read error: {e}")

    windows_setup_cmd = root / "SETUP_WINDOWS_CLIENT.cmd"
    if windows_setup_cmd.exists():
        try:
            text = windows_setup_cmd.read_text(encoding="utf-8")
            if "setup_windows_client.ps1" in text:
                ok("Windows setup cmd - PowerShell bootstrap linked")
            else:
                fail("Windows setup cmd - missing PowerShell bootstrap link")
        except OSError as e:
            fail(f"Windows setup cmd - read error: {e}")

    windows_setup_full_cmd = root / "SETUP_WINDOWS_FULL.cmd"
    if windows_setup_full_cmd.exists():
        try:
            text = windows_setup_full_cmd.read_text(encoding="utf-8")
            if "setup_windows_client.ps1" in text and "-SyncClaude" in text and "-SyncCodexGlobal" in text:
                ok("Windows full setup cmd - full bootstrap flags linked")
            else:
                fail("Windows full setup cmd - missing full bootstrap flags")
        except OSError as e:
            fail(f"Windows full setup cmd - read error: {e}")

    windows_setup_ps1 = root / "scripts" / "setup_windows_client.ps1"
    if windows_setup_ps1.exists():
        try:
            text = windows_setup_ps1.read_text(encoding="utf-8")
            if "requirements.txt" in text and "validate.py" in text and "SyncCodexGlobal" in text:
                ok("Windows setup ps1 - install + validate + optional Codex sync OK")
            else:
                fail("Windows setup ps1 - expected install/validate/Codex sync logic missing")
        except OSError as e:
            fail(f"Windows setup ps1 - read error: {e}")

    windows_bundle_ps1 = root / "scripts" / "build_windows_portable_bundle.ps1"
    if windows_bundle_ps1.exists():
        try:
            text = windows_bundle_ps1.read_text(encoding="utf-8")
            if "Compress-Archive" in text and "hvdc-knowledge-windows-portable" in text:
                ok("Windows bundle ps1 - portable package builder OK")
            else:
                fail("Windows bundle ps1 - package builder logic missing")
        except OSError as e:
            fail(f"Windows bundle ps1 - read error: {e}")

    cursor_rule_path = root / ".cursor" / "rules" / "hvdc-domain-background.mdc"
    if cursor_rule_path.exists():
        try:
            text = cursor_rule_path.read_text(encoding="utf-8")
            if "alwaysApply: true" in text and "hvdc-knowledge" in text:
                ok("Cursor rule - alwaysApply + MCP guidance OK")
            else:
                fail("Cursor rule - missing alwaysApply or MCP guidance")
        except OSError as e:
            fail(f"Cursor rule - read error: {e}")

    railway_path = root / "railway.json"
    if railway_path.exists():
        try:
            railway = json.loads(railway_path.read_text(encoding="utf-8"))
            assert railway.get("build", {}).get("builder") == "DOCKERFILE"
            assert railway.get("deploy", {}).get("healthcheckPath") == "/health"
            ok("railway.json - builder + healthcheck OK")
        except Exception as e:
            fail(f"railway.json - invalid: {e}")


# ──────────────────────────────────────────
# Main
# ──────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="HVDC MCP Server Validation")
    parser.add_argument("--quick", action="store_true", help="compile + quick test only")
    args = parser.parse_args()

    start = time.time()

    print(f"\n{BOLD}{'=' * 50}")
    print("  HVDC Knowledge MCP - Validation Suite")
    print(f"{'=' * 50}{RESET}")

    check_compile()
    check_imports()

    if not args.quick:
        check_lint()
        check_tools()
        check_security()
        check_structure()
    else:
        section("Quick Tool Test")
        sys.path.insert(0, str(Path(__file__).parent.parent))
        try:
            import server
            result = asyncio.new_event_loop().run_until_complete(
                server.hvdc_get_domain_summary()
            )
            assert "MOSB" in result
            ok("hvdc_get_domain_summary - quick check OK")
        except Exception as e:
            fail(f"Quick tool test: {e}")

    elapsed = time.time() - start

    print(f"\n{BOLD}{'=' * 50}")
    print(f"  Results: {GREEN}{passed} passed{RESET}{BOLD}, ", end="")
    if failed:
        print(f"{RED}{failed} failed{RESET}{BOLD}, ", end="")
    else:
        print("0 failed, ", end="")
    if warnings:
        print(f"{YELLOW}{warnings} warnings{RESET}{BOLD}")
    else:
        print("0 warnings")
    print(f"  Time: {elapsed:.2f}s")
    print(f"{'=' * 50}{RESET}\n")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
