"""Question -> SQL using Groq's chat API."""
import os
import re

from groq import Groq

DEFAULT_MODEL = "openai/gpt-oss-120b"


def model_name() -> str:
    return os.getenv("GROQ_MODEL", DEFAULT_MODEL)


def _client() -> Groq:
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to the environment or Streamlit secrets.")
    return Groq(api_key=key)


SYSTEM = """You translate business questions into one SQLite query.

Database schema:
{schema}

Rules:
- Reply with exactly one ```sql fenced block, then one short sentence starting with "Explanation:".
- Read-only: a single SELECT (CTEs with WITH are fine). Never write, alter or drop anything.
- Use only the tables and columns listed above. Join through the foreign keys shown.
- Revenue means SUM(order_items.quantity * order_items.unit_price) and only counts orders whose status is not 'cancelled' or 'returned', unless the user says otherwise.
- Dates are ISO text (YYYY-MM-DD). Use strftime for months and years.
- Name result columns clearly. Add ORDER BY when ranking and LIMIT when the user asks for a top N.
"""


def _parse(text: str) -> tuple[str, str]:
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    sql = (m.group(1) if m else text).strip()
    e = re.search(r"Explanation:\s*(.+)", text, re.S)
    return sql, (e.group(1).strip() if e else "")


def generate(question: str, schema: str, previous_error: str | None = None, previous_sql: str | None = None) -> tuple[str, str]:
    """Return (sql, explanation). When retrying, pass the failed SQL and its error."""
    messages = [
        {"role": "system", "content": SYSTEM.format(schema=schema)},
        {"role": "user", "content": question},
    ]
    if previous_error:
        messages += [
            {"role": "assistant", "content": f"```sql\n{previous_sql}\n```"},
            {"role": "user", "content": f"That query failed: {previous_error}\nFix it and answer in the same format."},
        ]
    resp = _client().chat.completions.create(model=model_name(), messages=messages, temperature=0)
    return _parse(resp.choices[0].message.content or "")
