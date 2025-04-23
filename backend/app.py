import psycopg2
import flask
import requests
import uuid
from datetime import datetime
from flask import render_template
import os

app = flask.Flask(__name__)

# --- Configuration ---------------------------------------------------------
QUERY_API = f"{os.getenv('DP_HOST')}:{os.getenv('DP_PORT')}/query"
LLM_ENDPOINT  = os.getenv('LLM_ENDPOINT')
TOP_K_DEFAULT = 5
CONFIDENCE_DEFAULT = 0.0

# --- Frontend Route --------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

# --- Database helpers ------------------------------------------------------

def connect_to_db():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        port=os.getenv("POSTGRES_PORT")
    )


def create_table(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id   VARCHAR(255) PRIMARY KEY,
            session_name VARCHAR(255) NOT NULL,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id         SERIAL PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL,
            role       VARCHAR(50) NOT NULL,
            content    TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
        """
    )
    conn.commit()

# --- Prompt helper ---------------------------------------------------------

def get_prompt(conn, current_query: str, conversation_history=None, *, top_k=TOP_K_DEFAULT, confidence=CONFIDENCE_DEFAULT):
    """Build an LLM prompt by enriching the user query with vector-DB context."""
    if conversation_history is None:
        conversation_history = []

    # 1. Format dialogue history ------------------------------------------------
    history_text = "\n".join(
        f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}" for msg in conversation_history
    )

    full_query = f"{history_text}\n\nCurrent Query: {current_query}" if history_text else current_query

    # 2. Fetch extra context from vector store ---------------------------------
    try:
        vect_resp = requests.post(
            QUERY_API,
            json={"query": full_query, "top_k": top_k, "confidence": confidence},
            timeout=60
        )
        vect_resp.raise_for_status()
        results = vect_resp.json()
    except Exception as exc:
        raise RuntimeError(f"Vector-DB request failed → {exc}") from exc

    # 3. Load Jinja-style template --------------------------------------------
    with open("template.txt", "r", encoding="utf-8") as f:
        template = f.read()

    prompt = template.replace("{{user_query}}", full_query)

    # 4. Inject papers section --------------------------------------------------
    papers_block = ""
    for paper in results.get("papers", []):
        meta = paper.get("metadata", {})
        papers_block += (
            f"- Title: {meta.get('title', 'N/A')}\n"
            f"  ArXiv ID: {meta.get('arxiv_id', 'N/A')}\n"
            f"  URL: {meta.get('url', 'N/A')}\n"
            f"  Confidence Score: {paper.get('confidence', 0.0)}\n"
            f"  Summary: {paper.get('content', 'N/A')}\n\n"
        )

    prompt = prompt.replace(r"{% for paper in papers %}\n{% endfor %}", papers_block)
    return prompt

# ---------------------------------------------------------------------------
#                                  ROUTES                                   
# ---------------------------------------------------------------------------

@app.route("/health")
def health_check():
    return "OK"

# ----------------------------- Session CRUD --------------------------------

@app.route("/deepseek_backend/create_session", methods=["POST"])
def create_session():
    data = flask.request.get_json(force=True)
    session_name = data.get("session_name", "New Chat")
    session_id = str(uuid.uuid4())

    conn, cur = connect_to_db(), None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sessions (session_id, session_name) VALUES (%s, %s)",
            (session_id, session_name),
        )
        conn.commit()
    finally:
        if conn:
            conn.close()

    return flask.jsonify({"session_id": session_id, "session_name": session_name})


@app.route("/deepseek_backend/get_session")
def get_sessions():
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("SELECT session_id, session_name FROM sessions ORDER BY updated_at DESC")
    sessions = [{"session_id": s, "session_name": n} for s, n in cur.fetchall()]
    conn.close()
    return flask.jsonify(sessions)


@app.route("/deepseek_backend/delete_session", methods=["POST"])
def delete_session():
    session_id = flask.request.get_json(force=True).get("session_id")
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM messages WHERE session_id = %s", (session_id,))
    cur.execute("DELETE FROM sessions WHERE session_id = %s", (session_id,))
    conn.commit()
    conn.close()
    return flask.jsonify({"status": "success"})


@app.route("/deepseek_backend/load_chat/<session_id>")
def load_chat(session_id):
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT role, content FROM messages WHERE session_id = %s ORDER BY created_at ASC",
        (session_id,),
    )
    msgs = [{"role": r, "content": c} for r, c in cur.fetchall()]
    conn.close()
    return flask.jsonify(msgs)


@app.route("/deepseek_backend/save_chat", methods=["POST"])
def save_chat():
    data = flask.request.get_json(force=True)
    session_id = data["session_id"]
    user_msg    = data.get("user")
    asst_msg    = data.get("assistant")

    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = %s", (session_id,))
    cur.execute("INSERT INTO messages (session_id, role, content) VALUES (%s,'user',%s)", (session_id, user_msg))
    cur.execute("INSERT INTO messages (session_id, role, content) VALUES (%s,'assistant',%s)", (session_id, asst_msg))
    conn.commit()
    conn.close()
    return flask.jsonify({"status": "success"})

# ---------------------------  NEW CHAT ENDPOINT  ---------------------------

@app.route("/deepseek_backend/chat", methods=["POST"])
def backend_chat():
    """Single endpoint that: 1) builds a prompt with extra context, 2) calls the local LLM, 3) stores the Q&A."""
    data = flask.request.get_json(force=True)

    session_id = data.get("session_id")  # may be null for ad-hoc chats
    query      = data.get("query")
    history    = data.get("messages")  # optional - fallback to DB

    if not query:
        return flask.jsonify({"error": "'query' field is required"}), 400

    conn = connect_to_db()

    # If history not supplied, pull the last 10 messages for context
    if history is None and session_id:
        cur = conn.cursor()
        cur.execute(
            """SELECT role, content FROM messages
                WHERE session_id = %s ORDER BY created_at DESC LIMIT 10""",
            (session_id,),
        )
        history = [{"role": r, "content": c} for r, c in cur.fetchall()][::-1]  # chronological

    # 1. Build the prompt -----------------------------------------------------
    try:
        prompt = get_prompt(conn, query, history)
    except Exception as exc:
        conn.close()
        return flask.jsonify({"error": str(exc)}), 500

    # 2. Call local LLM -------------------------------------------------------
    try:
        llm_resp = requests.post(LLM_ENDPOINT, json={"prompt": prompt}, timeout=120)
        llm_resp.raise_for_status()
        asst_text = llm_resp.json().get("response") or llm_resp.text
    except Exception as exc:
        conn.close()
        return flask.jsonify({"error": f"LLM call failed → {exc}"}), 502

    # 3. Persist messages -----------------------------------------------------
    if session_id:
        cur = conn.cursor()
        cur.execute("UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = %s", (session_id,))
        cur.execute("INSERT INTO messages (session_id, role, content) VALUES (%s,'user',%s)", (session_id, query))
        cur.execute("INSERT INTO messages (session_id, role, content) VALUES (%s,'assistant',%s)", (session_id, asst_text))
        conn.commit()

    conn.close()
    return flask.jsonify({"message": {"content": asst_text}})

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    with connect_to_db() as conn:
        create_table(conn)
    app.run(host="0.0.0.0", port=5000, debug=True)
