# SenseQL

Ask a question about a database in plain English. SenseQL writes the SQL with an LLM, checks that it is a safe read-only query, runs it and shows the result.

**Live demo:** see the link in the repo description.

## How it works

1. You type a question in the Streamlit UI.
2. `db.schema_text()` reads the live SQLite schema (tables, columns, foreign keys).
3. `llm.generate()` sends the schema and your question to Groq (`openai/gpt-oss-120b` by default) and parses the SQL from the reply.
4. `guard.check()` is the safety gate. It strips comments, allows one statement only, requires `SELECT` or `WITH`, and rejects write or admin keywords.
5. `db.run()` executes on a read-only SQLite connection (`mode=ro`) with an authorizer that denies everything except reads. Results are capped at 500 rows.
6. If SQLite rejects the query, the error goes back to the model once for a repair attempt. The answer, the SQL and a short explanation are kept in the session history.

The gate has three layers on purpose: text validation, a read-only connection and a SQLite authorizer. If the model writes something harmful, any one of them stops it.

## Demo data

`seed.py` builds a small online shop (5 categories, 40 products, 200 customers, 900 orders, about 2,200 order lines) with a fixed random seed, so results are the same on every machine. The database file is created on first run.

## Run it locally

```bash
pip install -r requirements.txt
export GROQ_API_KEY=your_key      # free key from console.groq.com
# optional: export GROQ_MODEL=openai/gpt-oss-120b
streamlit run app.py
```

On Streamlit Community Cloud, put `GROQ_API_KEY` (and optionally `GROQ_MODEL`) in the app's Secrets.

## Files

| File | Purpose |
| --- | --- |
| `app.py` | Streamlit UI, history, retry loop |
| `llm.py` | Prompt building and Groq call |
| `guard.py` | SELECT-only validator and SQLite authorizer |
| `db.py` | Schema introspection and guarded execution |
| `seed.py` | Deterministic demo database |

## Limits

- SQLite dialect only.
- The model can write valid SQL that answers a different question than you meant. Always read the SQL shown above the result.
- Row cap of 500, single statement, no writes by design.
