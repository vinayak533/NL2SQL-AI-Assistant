import os
import re
import time
import logging
import sqlite3
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

load_dotenv()

from vanna_setup import get_agent, agent_memory

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("nl2sql")

# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="NL2SQL Clinic API",
    description="Natural Language to SQL chatbot powered by Vanna 2.0 + Gemini",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.getenv("DB_PATH", "clinic.db")

# ✅ ROOT ROUTE (FIXED YOUR ERROR)
@app.get("/")
def home():
    return {"message": "API is running. Go to /docs to test endpoints."}

# ── SQL Validation ─────────────────────────────────────────────────────────────
BLOCKED_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|EXEC|EXECUTE|GRANT|REVOKE|SHUTDOWN"
    r"|CREATE|TRUNCATE|REPLACE|MERGE|xp_|sp_)\b",
    re.IGNORECASE,
)
SYSTEM_TABLES = re.compile(r"\bsqlite_master\b|\bsqlite_sequence\b", re.IGNORECASE)


def validate_sql(sql: str) -> tuple[bool, str]:
    stripped = sql.strip().upper()

    if not stripped.startswith("SELECT"):
        return False, "Only SELECT queries are permitted."

    if BLOCKED_KEYWORDS.search(sql):
        kw = BLOCKED_KEYWORDS.search(sql).group()
        return False, f"Forbidden keyword detected: '{kw}'."

    if SYSTEM_TABLES.search(sql):
        return False, "System tables access not allowed."

    return True, ""


# ── Models ─────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)

    @field_validator("question")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Question must not be blank.")
        return v.strip()


class ChatResponse(BaseModel):
    message: str
    sql_query: str | None = None
    columns: list[str] | None = None
    rows: list[list[Any]] | None = None
    row_count: int | None = None
    chart: dict | None = None
    chart_type: str | None = None
    execution_time_ms: float | None = None


class HealthResponse(BaseModel):
    status: str
    database: str
    agent_memory_items: int


# ── DB Query ───────────────────────────────────────────────────────────────────
def run_query(sql: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        if not rows:
            return [], []
        cols = list(rows[0].keys())
        data = [list(r) for r in rows]
        return cols, data
    finally:
        conn.close()


# ── SQL Extract ────────────────────────────────────────────────────────────────
SQL_FENCE = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
INLINE_SQL = re.compile(r"SELECT\s.+", re.DOTALL | re.IGNORECASE)


def extract_sql(text: str):
    m = SQL_FENCE.search(text)
    if m:
        return m.group(1).strip()
    m = INLINE_SQL.search(text)
    if m:
        return m.group(0).strip()
    return None


# ── Chart ──────────────────────────────────────────────────────────────────────
def guess_chart_type(cols, rows):
    col_lower = [c.lower() for c in cols]
    if any(k in " ".join(col_lower) for k in ["date", "month", "year"]):
        return "line"
    if len(cols) == 2:
        return "bar"
    return "bar"


def build_chart(cols, rows):
    if not cols or not rows or len(cols) < 2:
        return None
    try:
        import plotly.graph_objects as go
        chart_type = guess_chart_type(cols, rows)

        x = [r[0] for r in rows]
        y = [r[1] for r in rows]

        if chart_type == "line":
            fig = go.Figure(go.Scatter(x=x, y=y))
        else:
            fig = go.Figure(go.Bar(x=x, y=y))

        return fig.to_dict()
    except:
        return None


# ── Rate Limit ─────────────────────────────────────────────────────────────────
_rate_store = {}
RATE_LIMIT = 20


def check_rate_limit(ip):
    now = time.time()
    times = _rate_store.get(ip, [])
    times = [t for t in times if now - t < 60]
    if len(times) >= RATE_LIMIT:
        return False
    times.append(now)
    _rate_store[ip] = times
    return True


# ── CHAT API ───────────────────────────────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest):
    ip = request.client.host if request.client else "unknown"

    if not check_rate_limit(ip):
        raise HTTPException(status_code=429, detail="Too many requests")

    t0 = time.perf_counter()

    # Step 1: Agent
    try:
        agent = get_agent()
        text = ""
        async for event in agent.send_message(body.question):
            if isinstance(event, dict):
                text += event.get("content", "")
            else:
                text += str(event)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Step 2: Extract SQL
    sql = extract_sql(text)

    if not sql:
        return ChatResponse(message=text)

    # Step 3: Validate
    valid, err = validate_sql(sql)
    if not valid:
        return ChatResponse(message=err, sql_query=sql)

    # Step 4: Execute
    try:
        cols, rows = run_query(sql)
    except Exception as e:
        return ChatResponse(message=str(e), sql_query=sql)

    # Step 5: Response
    chart = build_chart(cols, rows)

    return ChatResponse(
        message=f"Found {len(rows)} results",
        sql_query=sql,
        columns=cols,
        rows=rows,
        row_count=len(rows),
        chart=chart,
        execution_time_ms=round((time.perf_counter() - t0) * 1000, 1),
    )


# ── HEALTH ─────────────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse)
def health():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("SELECT 1")
        conn.close()
        db = "connected"
    except:
        db = "disconnected"

    return HealthResponse(
        status="ok",
        database=db,
        agent_memory_items=len(agent_memory._memories),
    )


# ── RUN ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", reload=True)