# -*- coding: utf-8 -*-
"""
MCP Client Module.

Connects to local stdio JSON-RPC MCP servers.

This production handoff version is strict by default: it does not synthesize
mock market tables when MCP servers are missing. Set STRICT_EXTERNAL_DATA=false
only for local UI smoke tests.
"""

import json
import os
import select
import subprocess
import sys
import time
from typing import Any, Dict, Iterable, List, Optional

HOME_DIR = os.path.expanduser("~")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_TUIK_SERVER_CANDIDATES = [
    os.getenv("MCP_TUIK_SERVER_PATH", ""),
    os.path.join(BASE_DIR, "tuik_data", "mcp_server.py"),
    os.path.join(HOME_DIR, "Desktop", "tuik_data", "mcp_server.py"),
    os.path.join(HOME_DIR, "tuik_data", "mcp_server.py"),
]

DEFAULT_BRAND_SERVER_CANDIDATES = [
    os.getenv("MCP_BRAND_SERVER_PATH", ""),
    os.path.join(BASE_DIR, "sector_news", "mcp_server.py"),
    os.path.join(HOME_DIR, "Desktop", "sector_news", "mcp_server.py"),
    os.path.join(HOME_DIR, "sector_news", "mcp_server.py"),
]

def env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def first_existing_path(paths: Iterable[str]) -> Optional[str]:
    for path in paths:
        if path and os.path.exists(os.path.expanduser(path)):
            return os.path.expanduser(path)
    return None


def parse_extra_server_paths(value: Optional[str]) -> List[str]:
    if not value:
        return []
    separators = [os.pathsep, "\n", ","]
    items = [value]
    for sep in separators:
        next_items = []
        for item in items:
            next_items.extend(item.split(sep))
        items = next_items
    return [os.path.expanduser(item.strip()) for item in items if item.strip()]


class MCPClient:
    """Small stdio JSON-RPC client for a single local MCP server."""

    def __init__(
        self,
        server_path: Optional[str] = None,
        name: str = "tuik",
        timeout: float = 5.0,
        strict: Optional[bool] = None,
    ):
        self.server_path = server_path if server_path is not None else first_existing_path(DEFAULT_TUIK_SERVER_CANDIDATES)
        self.name = name
        self.timeout = timeout
        self.strict = env_bool("STRICT_EXTERNAL_DATA", True) if strict is None else strict
        self.process: Optional[subprocess.Popen] = None
        self.enabled = False
        self._next_id = 1

        if not self.server_path or not os.path.exists(self.server_path):
            message = f"[MCP:{self.name}] Server not found. Configure the MCP path or merge the MCP server."
            if self.strict:
                raise FileNotFoundError(message)
            print(f"⚠️ {message}")
            return

        try:
            self.process = subprocess.Popen(
                [sys.executable, self.server_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            response = self.request("initialize", {}, timeout=self.timeout)
            if response and "result" in response:
                self.enabled = True
                print(f"✓ [MCP:{self.name}] Connected to {self.server_path}")
            else:
                message = f"[MCP:{self.name}] Invalid initialize response."
                if self.strict:
                    raise RuntimeError(message)
                print(f"⚠️ {message}")
        except Exception as exc:
            if self.strict:
                self.close()
                raise
            print(f"⚠️ [MCP:{self.name}] Could not start server: {exc}.")
            self.close()

    def _send_raw(self, payload: Dict[str, Any]) -> None:
        if not self.process or not self.process.stdin:
            return
        self.process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def _read_raw(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        if not self.process or not self.process.stdout:
            return None
        timeout = self.timeout if timeout is None else timeout
        try:
            deadline = time.time() + timeout
            while time.time() < deadline:
                ready, _, _ = select.select([self.process.stdout], [], [], max(0.05, deadline - time.time()))
                if not ready:
                    return None
                line = self.process.stdout.readline()
                if not line:
                    return None
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    print(f"⚠️ [MCP:{self.name}] Skipping non-JSON stdout line: {line[:120].strip()}")
                    continue
            return None
        except Exception as exc:
            print(f"⚠️ [MCP:{self.name}] Error reading stdout: {exc}")
            return None

    def request(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        req_id = self._next_id
        self._next_id += 1
        self._send_raw({
            "jsonrpc": "2.0",
            "method": method,
            "id": req_id,
            "params": params or {},
        })
        return self._read_raw(timeout=timeout)

    def list_tools(self) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        response = self.request("tools/list", {}, timeout=self.timeout)
        return response.get("result", {}).get("tools", []) if response else []

    def call_tool(self, tool_name: str, arguments: Dict[str, Any], timeout: Optional[float] = None) -> Dict[str, Any]:
        if not self.enabled:
            if self.strict:
                raise RuntimeError(f"[MCP:{self.name}] Tool '{tool_name}' cannot run because the MCP server is not enabled.")
            return {}

        try:
            response = self.request(
                "tools/call",
                {"name": tool_name, "arguments": arguments},
                timeout=timeout or self.timeout,
            )
            if not response or "result" not in response:
                raise TimeoutError("No valid tool response received.")
            content = response["result"].get("content", [])
            if not content:
                return response["result"]
            text_content = content[0].get("text", "{}")
            return json.loads(text_content)
        except Exception as exc:
            if self.strict:
                raise RuntimeError(f"[MCP:{self.name}] Tool '{tool_name}' failed: {exc}") from exc
            print(f"⚠️ [MCP:{self.name}] Tool '{tool_name}' failed: {exc}.")
            return {}

    def close(self) -> None:
        if not self.process:
            return
        try:
            self.process.terminate()
            self.process.wait(timeout=1)
        except Exception:
            try:
                self.process.kill()
            except Exception:
                pass
        finally:
            self.process = None
            self.enabled = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def get_mock_payload(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Synthetic MCP-like payloads for local demo mode."""
        region = arguments.get("region", "Türkiye")
        brand = arguments.get("brand_name") or arguments.get("brand") or "Demo Marka"
        category = arguments.get("category", "Genel")
        
        if tool_name == "get_market_dynamics":
            return {
                "source": "tuik_market_dynamics",
                "findings": [
                    "Bölgesel nüfus payı %14.2",
                    "İş gücüne katılım %53.8",
                    "Yükseköğretim mezun oranı %31.0",
                    "Yıllık harcanabilir gelir 540,000 TL"
                ],
                "signals": [
                    "Bölgesel satın alma gücü endeksi 96.5",
                    "Fiyat hassasiyeti yüksek seviyelerde"
                ],
                "segment_clues": [
                    "Gıda-içecek harcama payı %24.6",
                    "İnternet kullanım penetrasyonu %88.4"
                ],
                "parameter_effects": {
                    "price_sensitivity_index_normalized": 1.18,
                    "regional_purchasing_power_index": 96.5,
                    "regional_population_share_pct": 14.2,
                    "labor_force_participation_rate": 53.8,
                    "higher_education_grad_rate": 0.31,
                    "avg_annual_disposable_income_lira": 540000,
                    "coicop_food_beverages_share_pct": 24.6,
                    "internet_usage_penetration_pct": 88.4
                },
                "confidence": 90
            }
        if tool_name == "get_brand_context":
            return {
                "source": "tuik_brand_context",
                "findings": [
                    f"{brand} pazar payı %6.8",
                    "Bölgesel kapsama yoğunluğu %57.0"
                ],
                "signals": [
                    "Marka fiyat primi endeksi 1.12",
                    "Rakip çakışma endeksi %44.0"
                ],
                "segment_clues": [
                    "Marka sadakat endeksi 61.0"
                ],
                "parameter_effects": {
                    "market_share_pct": 6.8,
                    "brand_price_premium_index": 1.12,
                    "brand_loyalty_index": 61.0
                },
                "confidence": 85
            }
        if tool_name == "get_current_context":
            return {
                "source": "tuik_current_context",
                "findings": [
                    "Bölgesel TÜFE enflasyonu %48.5",
                    "Hammadde maliyet endeksi değişimi %12.4"
                ],
                "signals": [
                    "Mevsimsel talep endeksi 1.08",
                    "Rekabet yoğunluğu endeksi 64.0"
                ],
                "segment_clues": [
                    "Tüketici güven endeksi 78.2"
                ],
                "parameter_effects": {
                    "regional_cpi_inflation": 48.5,
                    "consumer_confidence_index": 78.2
                },
                "confidence": 80
            }
        if tool_name == "generate_report":
            return {
                "source": "brand_news_context",
                "findings": [
                    "Demo modunda sentetik haber ve sektör bağlamı üretildi."
                ],
                "signals": [
                    "Fiyat hassasiyeti yüksek fakat deneme paketi bariyeri azaltıyor.",
                    "Yerel üretim ve şeffaf fayda anlatısı güveni artırıyor.",
                    "Dijital kanallarda kısa karşılaştırmalı içerikler dönüşümü destekliyor."
                ],
                "segment_clues": [],
                "parameter_effects": {},
                "confidence": 75
            }
        
        return {
            "source": "synthetic_demo",
            "findings": [],
            "signals": [],
            "segment_clues": [],
            "parameter_effects": {},
            "confidence": 0
        }


def collect_market_context(
    form_input: Dict[str, Any],
    extra_server_paths: Optional[Iterable[str]] = None,
    progress_callback=None,
    strict: Optional[bool] = None,
) -> Dict[str, Any]:
    """Collects TÜİK, brand, and optional extra MCP context for the pipeline."""

    def emit(message: str):
        if progress_callback:
            progress_callback({
                "phase": "mcp",
                "message": message,
                "progress": None,
            })

    brand = form_input.get("brand_name") or form_input.get("brand") or "Marka"
    category = form_input.get("category", "coffee")
    region = form_input.get("region", "Ege")

    strict_mode = env_bool("STRICT_EXTERNAL_DATA", True) if strict is None else strict
    tuik_path = first_existing_path(DEFAULT_TUIK_SERVER_CANDIDATES)
    emit("TÜİK MCP sunucusu hazırlanıyor.")
    with MCPClient(tuik_path, name="tuik", timeout=4.0, strict=strict) as tuik:
        dynamics = tuik.call_tool("get_market_dynamics", {
            "region": region,
            "age_range": "18-30",
            "category": category,
        }, timeout=4.0)
        if not dynamics and not strict_mode:
            dynamics = tuik.get_mock_payload("get_market_dynamics", {"region": region, "category": category})
        brand_context = tuik.call_tool("get_brand_context", {"brand_name": brand}, timeout=4.0)
        if not brand_context and not strict_mode:
            brand_context = tuik.get_mock_payload("get_brand_context", {"brand_name": brand})
        current_context = tuik.call_tool("get_current_context", {
            "region": region,
            "category": category,
            "brand_name": brand,
        }, timeout=4.0)
        if not current_context and not strict_mode:
            current_context = tuik.get_mock_payload("get_current_context", {"region": region, "category": category, "brand_name": brand})

    brand_report = {}
    brand_path = first_existing_path(DEFAULT_BRAND_SERVER_CANDIDATES)
    emit("Sektör ve haberler MCP sunucusundan marka bağlamı çekiliyor.")
    with MCPClient(brand_path, name="brand", timeout=7.0, strict=strict) as brand_client:
        brand_report = brand_client.call_tool("generate_report", {
            "brand": brand,
            "category": category,
            "region": "TR",
            "sector": category,
        }, timeout=7.0)
        if not brand_report and not strict_mode:
            brand_report = brand_client.get_mock_payload("generate_report", {"brand": brand, "category": category})

    optional_context = []
    configured_extra = parse_extra_server_paths(os.getenv("EXTRA_MCP_SERVER_PATHS"))
    for idx, server_path in enumerate(list(extra_server_paths or []) + configured_extra, start=1):
        if not os.path.exists(server_path):
            if strict_mode:
                raise FileNotFoundError(f"[MCP:extra-{idx}] Configured extra MCP server not found: {server_path}")
            optional_context.append({"path": server_path, "status": "missing"})
            continue
        emit(f"Ek MCP sunucusu #{idx} okunuyor.")
        with MCPClient(server_path, name=f"extra-{idx}", timeout=5.0, strict=strict) as client:
            tools = client.list_tools()
            optional_context.append({
                "path": server_path,
                "status": "connected" if client.enabled else "fallback",
                "tools": [tool.get("name") for tool in tools],
            })

    return {
        "tuik_market_dynamics": dynamics,
        "tuik_brand_context": brand_context,
        "tuik_current_context": current_context,
        "brand_news_context": brand_report,
        "optional_mcp_context": optional_context,
    }
