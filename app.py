import sqlite3

import streamlit as st

import db
import guard
import llm

st.set_page_config(page_title="SenseQL", page_icon="🔎", layout="wide")
db.ensure_db()

# Streamlit Cloud exposes secrets; copy them into the environment for llm.py.
import os
for key in ("GROQ_API_KEY", "GROQ_MODEL"):
    try:
        if key in st.secrets and not os.getenv(key):
            os.environ[key] = str(st.secrets[key])
    except Exception:
        pass

EXAMPLES = [
    "Top 5 customers by total spend",
    "Monthly revenue for 2025",
    "Which product category earns the most revenue?",
    "How many orders were cancelled or returned, by city?",
    "Average order value by customer city",
    "Best selling product in each category",
]

st.session_state.setdefault("history", [])
st.session_state.setdefault("question", "")


def answer(question: str) -> dict:
    schema = db.schema_text()
    entry = {"question": question, "sql": "", "explanation": "", "df": None, "error": ""}
    sql, why = llm.generate(question, schema)
    for attempt in range(2):
        entry["sql"], entry["explanation"] = sql, why
        try:
            entry["df"] = db.run(sql)
            entry["error"] = ""
            return entry
        except guard.UnsafeSQL as e:
            entry["error"] = f"Blocked by the safety gate: {e}"
            return entry
        except sqlite3.Error as e:
            entry["error"] = f"SQLite error: {e}"
            if attempt == 0:
                sql, why = llm.generate(question, schema, previous_error=str(e), previous_sql=sql)
    return entry


with st.sidebar:
    st.header("Database")
    st.caption("Demo online shop, 200 customers, 900 orders.")
    st.code(db.schema_text(), language="text")
    st.caption(f"Model: {llm.model_name()}")
    st.header("Try one")
    for ex in EXAMPLES:
        if st.button(ex, key=f"ex_{ex}", width="stretch"):
            st.session_state.question = ex

st.title("🔎 SenseQL")
st.write("Ask a question in plain English. SenseQL writes the SQL, checks it is a safe read-only query, runs it and shows the result.")

question = st.text_input("Your question", key="question", placeholder="e.g. Which city has the highest revenue?")
go = st.button("Ask", type="primary")

if go and question.strip():
    with st.spinner("Thinking..."):
        try:
            st.session_state.history.insert(0, answer(question.strip()))
        except Exception as e:  # missing key, network, model error
            st.session_state.history.insert(0, {"question": question.strip(), "sql": "", "explanation": "", "df": None, "error": str(e)})

for i, item in enumerate(st.session_state.history):
    with st.container(border=True):
        st.markdown(f"**{item['question']}**")
        if item["sql"]:
            st.code(item["sql"], language="sql")
        if item["explanation"]:
            st.caption(item["explanation"])
        if item["error"]:
            st.error(item["error"])
        elif item["df"] is not None:
            st.dataframe(item["df"], width="stretch", hide_index=True)
            note = f"{len(item['df'])} rows"
            if len(item["df"]) >= db.MAX_ROWS:
                note += f" (capped at {db.MAX_ROWS})"
            st.caption(note)
