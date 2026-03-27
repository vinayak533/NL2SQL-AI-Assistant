# NL2SQL Clinic Chatbot

A **Natural Language to SQL** system built with **Vanna 2.0** and **FastAPI** that lets users ask plain-English questions about a clinic database and receive structured results, including charts.

> **LLM Provider chosen:** Google Gemini (`gemini-2.5-flash`) — free tier via [Google AI Studio](https://aistudio.google.com/apikey)

---

## Project Structure

```
nl2sql/
├── setup_database.py   # Creates clinic.db with schema + 500+ dummy rows
├── seed_memory.py      # Seeds Vanna agent memory with 20 Q-SQL pairs
├── vanna_setup.py      # Vanna 2.0 Agent initialisation
├── main.py             # FastAPI application (POST /chat, GET /health)
├── requirements.txt    # All Python dependencies
├── README.md           # This file
├── RESULTS.md          # Test results for 20 benchmark questions
└── clinic.db           # Generated SQLite database (created at runtime)
```

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10+ |
| Google Gemini API key | Free — [get one here](https://aistudio.google.com/apikey) |

---

## Setup Instructions

### 1. Clone / unzip the project

```bash
cd nl2sql
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```ini
# .env
GOOGLE_API_KEY=your-google-gemini-api-key-here

# Optional overrides
DB_PATH=clinic.db
RATE_LIMIT_PER_MINUTE=20
QUERY_CACHE=true
```

### 5. Create the database

```bash
python setup_database.py
```

Expected output:

```
✅  Created 200 patients, 15 doctors, 500 appointments, 350 treatments, 300 invoices
📁  Database saved to: clinic.db
```

### 6. Seed agent memory

```bash
python seed_memory.py
```

Expected output:

```
Seeding 20 Q&A pairs into DemoAgentMemory …
  [01] ✓  How many patients do we have?
  ...
✅  Memory seeded with 20 items.
   Total items in memory: 20
```

### 7. Start the API server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Or, run everything in one command:

```bash
pip install -r requirements.txt && python setup_database.py \
  && python seed_memory.py && uvicorn main:app --port 8000
```

The server starts at **http://localhost:8000**

---

## API Documentation

### `POST /chat`

Ask a natural-language question about the clinic database.

**Request**

```http
POST /chat
Content-Type: application/json

{
  "question": "Show me the top 5 patients by total spending"
}
```

**Response**

```json
{
  "message": "Found 5 results.",
  "sql_query": "SELECT p.first_name, p.last_name, ROUND(SUM(i.total_amount), 2) AS total_spending FROM invoices i JOIN patients p ON p.id = i.patient_id GROUP BY p.id ORDER BY total_spending DESC LIMIT 5;",
  "columns": ["first_name", "last_name", "total_spending"],
  "rows": [
    ["John", "Smith", 24500.0],
    ["Priya", "Nair", 21300.0]
  ],
  "row_count": 5,
  "chart": { "data": [...], "layout": {...} },
  "chart_type": "bar",
  "execution_time_ms": 842.3
}
```

**Validation errors (400)**

If the question is blank or too long:

```json
{ "detail": "Value error, Question must not be blank." }
```

**Rate limit (429)**

```json
{ "detail": "Rate limit exceeded. Please wait before sending more requests." }
```

---

### `GET /health`

Check if the API is running and the database is connected.

**Response**

```json
{
  "status": "ok",
  "database": "connected",
  "agent_memory_items": 20
}
```

---

## Example curl Requests

```bash
# Health check
curl http://localhost:8000/health

# Ask a question
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How many patients do we have?"}'

# Revenue by doctor
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Show revenue by doctor"}'
```

---

## Architecture Overview

```
User Question (HTTP POST /chat)
         │
         ▼
   FastAPI (main.py)
   ├── Input validation (Pydantic, min 3 chars, max 500)
   ├── Rate limiting (in-memory, 20 req/min per IP)
   └── Cache check (in-memory dict)
         │
         ▼
   Vanna 2.0 Agent (vanna_setup.py)
   ├── GeminiLlmService  ← Google Gemini 2.5 Flash
   ├── DemoAgentMemory   ← 20 pre-seeded Q-SQL pairs
   ├── RunSqlTool        ← SqliteRunner(clinic.db)
   └── VisualizeDataTool ← Plotly charts
         │
         ▼
   SQL Extraction (regex from agent response)
         │
         ▼
   SQL Validation
   ├── SELECT-only check
   ├── Blocked keywords (INSERT/DROP/EXEC …)
   └── System table check (sqlite_master)
         │
         ▼
   SQLite Execution (clinic.db)
         │
         ▼
   Chart Generation (Plotly — bar/line/pie)
         │
         ▼
   JSON Response → User
```

### Key Design Decisions

| Decision | Rationale |
|---|---|
| Vanna 2.0 Agent | Uses `Agent` + `DemoAgentMemory`; no ChromaDB or `vn.train()` |
| Google Gemini | Free tier, high accuracy for SQL generation |
| SQL-only validation | Blocks all write/system queries before execution |
| In-memory cache | Avoids redundant LLM calls for repeated questions |
| SimpleUserResolver | All users mapped to `user` group; easily extensible |

---

## Bonus Features Implemented

- ✅ **Chart generation** — Plotly bar/line/pie charts based on result shape
- ✅ **Input validation** — Length limits, blank checks via Pydantic
- ✅ **Query caching** — In-memory cache for repeated questions
- ✅ **Rate limiting** — 20 requests/minute per IP address
- ✅ **Structured logging** — Timestamped logs for all steps

---

## Troubleshooting

**`GOOGLE_API_KEY is not set`** — Create a `.env` file with your key (see Step 4).

**`ModuleNotFoundError: vanna`** — Run `pip install -r requirements.txt` again in your active virtualenv.

**`clinic.db not found`** — Run `python setup_database.py` first.

**Agent returns no SQL** — The agent may need clarification. Try rephrasing the question more specifically.
