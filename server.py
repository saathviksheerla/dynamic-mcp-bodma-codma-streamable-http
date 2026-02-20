"""
MCP Server — BODMA, CODMA & PRODMA
Transport: Streamable HTTP

Math definitions:
    BODMA(a, b)  = (a^b) / (a*b)       — exponent-heavy division
    CODMA(a, b)  = (a*b) / (a^b)       — inverse of BODMA
    PRODMA(a, b) = (a^b) * (b^a)       — symmetric cross-exponentiation
                                          available only 10:00 AM – 10:00 PM

Time-gating:
    PRODMA is registered normally via @mcp.tool() but filtered out of
    tools/list outside its window by wrapping _tool_manager.list_tools.
    A second guard inside the function blocks stale calls at call time.

Testing:
    Set FAKE_NOW_HOUR=11 in .env → inside window  (prodma visible)
    Set FAKE_NOW_HOUR=8  in .env → outside window (prodma hidden)

Run:
    python server.py
"""

import os
from datetime import datetime

import uvicorn
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

# ── Server ────────────────────────────────────────────────────────────────────

mcp = FastMCP(name="BODMA-CODMA-PRODMA", stateless_http=True)

# ── Time window ───────────────────────────────────────────────────────────────

PRODMA_START_HOUR = 10   # 10:00 AM
PRODMA_END_HOUR   = 22   # 10:00 PM


def current_hour() -> int:
    """Return current hour (0-23), overridable via FAKE_NOW_HOUR in .env."""
    fake = os.getenv("FAKE_NOW_HOUR")
    return int(fake) if fake else datetime.now().hour


def prodma_available() -> bool:
    """True if current time falls within the PRODMA availability window."""
    return PRODMA_START_HOUR <= current_hour() < PRODMA_END_HOUR


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def bodma(a: float, b: float) -> float:
    """BODMA: (a^b) / (a*b). Example: bodma(2,3) = 8/6 ≈ 1.333"""
    if a * b == 0:
        raise ValueError("a*b cannot be 0 — division by zero")
    return (a ** b) / (a * b)


@mcp.tool()
def codma(a: float, b: float) -> float:
    """CODMA: (a*b) / (a^b). Inverse of BODMA. Example: codma(2,3) = 6/8 = 0.75"""
    if a ** b == 0:
        raise ValueError("a^b cannot be 0 — division by zero")
    return (a * b) / (a ** b)


@mcp.tool()
def prodma(a: float, b: float) -> float:
    """PRODMA: (a^b) * (b^a). Example: prodma(2,3) = 8*9 = 72. Available 10AM-10PM only."""
    if not prodma_available():
        # Guard at call time — client may have a stale tool list
        raise ValueError(f"PRODMA only available {PRODMA_START_HOUR}:00–{PRODMA_END_HOUR}:00")
    return (a ** b) * (b ** a)


# ── Dynamic tools/list — hide prodma outside its time window ─────────────────

_original_list_tools = mcp._tool_manager.list_tools

def _dynamic_list_tools():
    all_tools = _original_list_tools()
    return [t for t in all_tools if t.name != "prodma" or prodma_available()]

mcp._tool_manager.list_tools = _dynamic_list_tools


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(mcp.streamable_http_app(), host="0.0.0.0", port=8000)