# MCP Server — BODMA, CODMA & PRODMA

A minimal MCP (Model Context Protocol) server exposing custom math tools,
with a Gemini-powered agent as the client. Features **dynamic tool listing** —
PRODMA is only available between 10:00 AM and 10:00 PM.

---

## The Math

| Tool   | Formula               | Example (a=2, b=3)       |
|--------|-----------------------|--------------------------|
| BODMA  | `(a^b) / (a*b)`       | `8 / 6 ≈ 1.333`          |
| CODMA  | `(a*b) / (a^b)`       | `6 / 8 = 0.75`           |
| PRODMA | `(a^b) * (b^a)`       | `8 * 9 = 72`             |

CODMA is the inverse of BODMA — their product always equals 1.
PRODMA is time-gated: only exposed via `tools/list` between 10AM and 10PM.

---

## Project Structure

```
mcp-fresh/
├── server.py          # MCP server — BODMA, CODMA, PRODMA (dynamic)
├── agent.py           # Gemini agent — connects to MCP server and calls tools
├── client.py          # Simple test client — no LLM, just raw tool calls
├── test_server.py     # Unit tests — math logic + time-gating edge cases
├── requirements.txt   # Python dependencies
├── .env               # Your API key + optional FAKE_NOW_HOUR (not committed)
└── .env.example       # Template — copy this to .env
```

---

## How It Works

```
You (prompt)
    │
    ▼
Gemini Agent (agent.py)
    │  1. Fetches available tools from MCP server (dynamic — depends on time)
    │  2. Sends prompt + tool definitions to Gemini
    │  3. Gemini decides to call a tool
    │  4. Agent calls the tool on MCP server
    │  5. Sends result back to Gemini
    │  6. Gemini produces final answer
    ▼
MCP Server (server.py)
    │  Receives tool call over Streamable HTTP
    │  Executes bodma(), codma(), or prodma()
    └→ Returns result
```

### Dynamic Tool List

`tools/list` is patched at startup to filter PRODMA based on the current hour:

```
10:00 AM – 10:00 PM  →  tools/list returns [bodma, codma, prodma]
outside this window  →  tools/list returns [bodma, codma]
```

The agent fetches the tool list fresh on every run — no client changes needed.
PRODMA also guards itself at call time in case a client has a stale tool list.

---

## Setup

### 1. Clone / download the project

```bash
cd mcp-fresh
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your Gemini API key

```bash
cp .env.example .env
```

Edit `.env`:
```
GEMINI_API_KEY=your_key_here
```

Get a free key at: https://aistudio.google.com/apikey

---

## Running

### Step 1 — Start the MCP server

```bash
python server.py
```

Server runs at `http://localhost:8000/mcp`

### Step 2 — Run the Gemini agent (in a new terminal)

```bash
source .venv/bin/activate
python agent.py
```

Expected output:
```
User: Calculate BODMA and CODMA for a=2, b=3 and explain the results.

🔧 Calling bodma({'a': 2.0, 'b': 3.0})
   → 1.3333333333333333

🔧 Calling codma({'a': 2.0, 'b': 3.0})
   → 0.75

Gemini: BODMA(2,3) equals 1.333 — this is (2³)/(2×3) = 8/6.
        CODMA(2,3) equals 0.75 — this is (2×3)/2³ = 6/8.
        They are inverses: 1.333 × 0.75 = 1.
```

### (Optional) Raw test without Gemini

```bash
python client.py
```

Tests tool calls directly against the MCP server — useful for debugging.

---

## Testing

Unit tests cover math logic and time-gating edge cases:

```bash
pytest test_server.py -v
```

To test PRODMA availability without waiting for the right time, set `FAKE_NOW_HOUR` in `.env`:

```env
FAKE_NOW_HOUR=11   # inside window  → prodma visible
FAKE_NOW_HOUR=8    # outside window → prodma hidden
```

Remove `FAKE_NOW_HOUR` (or leave it unset) to use real system time.

---

## Transport: Streamable HTTP

This project uses the **Streamable HTTP** transport (MCP spec 2025-03-26).

- The server exposes a single endpoint: `POST /mcp`
- Each request is stateless (`stateless_http=True`) — no session management needed
- The client sends JSON-RPC requests; the server streams back responses

---

## Connecting to Claude Desktop (optional)

If you want to use these tools directly inside Claude Desktop instead of the Gemini agent:

1. Open `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Add:

```json
{
  "mcpServers": {
    "bodma-codma": {
      "type": "streamable-http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

3. Keep `python server.py` running, then restart Claude Desktop.
4. You'll see a 🔧 tools icon in the chat input.

---

## Adding More Tools

Open `server.py` and add a new `@mcp.tool()` function:

```python
@mcp.tool()
def my_tool(x: float) -> float:
    """Description shown to the LLM."""
    return x * 42
```

To make it time-gated, add it to the filter in `_dynamic_list_tools`:

```python
def _dynamic_list_tools():
    all_tools = _original_list_tools()
    return [t for t in all_tools if t.name != "my_tool" or my_condition()]
```

---

## Cloud Deployment

### Railway (easiest)

```bash
brew install railway
railway login
railway init
railway up
```

Update the URL in `agent.py` and Claude Desktop config:
```
MCP_URL = "https://your-app.railway.app/mcp"
```

### Render / Fly.io

Both auto-detect a `Dockerfile` — add one based on the template below:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
EXPOSE 8000
CMD ["python", "server.py"]
```

---

## Dependencies

| Package          | Purpose                          |
|------------------|----------------------------------|
| `mcp[cli]`       | MCP SDK — server + client        |
| `uvicorn`        | ASGI server to run the app       |
| `google-genai`   | Gemini API (new SDK)             |
| `python-dotenv`  | Loads `.env` into environment    |