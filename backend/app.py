import psycopg2
import flask
import requests
import json
import uuid
from datetime import datetime

app = flask.Flask(__name__)
VECTOR_DB_API = "vector_dp_url/query"

def connect_to_db():
    conn = psycopg2.connect(
        host="postgres",
        database="dialog",
        user="user",
        password="password",
        port="5432"
    )
    return conn

def create_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id VARCHAR(255) PRIMARY KEY,
            session_name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
    """)
    conn.commit()

def insert_dialog(conn, user_id, context):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO dialog (user_id, context) VALUES (%s, %s)
    """, (user_id, context))
    conn.commit()


def get_dialog(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT context FROM dialog WHERE user_id = %s
    """, (user_id,))
    return cursor.fetchone()

def update_dialog(conn, user_id, context):
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE dialog SET context = %s WHERE user_id = %s
    """, (context, user_id))
    conn.commit()   

def delete_dialog(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM dialog WHERE user_id = %s
    """, (user_id,))
    conn.commit()



def get_prompt(conn, user_id, conversation_history=None, top_k=5, confidence=0.0):
    if conversation_history is None:
        conversation_history = []
    
    # Format the conversation history
    history_text = "\n".join([
        f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
        for msg in conversation_history
    ])
    
    # Combine history with current query
    full_query = f"{history_text}\n\nCurrent Query: {user_id}"
    
    params = {
        "query": full_query,
        "top_k": top_k,
        "confidence": confidence
    }
    try:
        response = requests.post(VECTOR_DB_API, params=params)
        results = response.json()
        
        with open('template.txt', 'r') as f:
            template = f.read()
            
        prompt = template.replace("{{user_query}}", full_query)
        
        papers_section = ""
        for paper in results.get('papers', []):
            papers_section += f"- Title: {paper.get('metadata', {}).get('title', 'N/A')}\n"
            papers_section += f"  ArXiv ID: {paper.get('metadata', {}).get('arxiv_id', 'N/A')}\n"
            papers_section += f"  URL: {paper.get('metadata', {}).get('url', 'N/A')}\n"
            papers_section += f"  Confidence Score: {paper.get('confidence', 0.0)}\n"
            papers_section += f"  Summary: {paper.get('content', 'N/A')}\n\n"
            
        prompt = prompt.replace("{% for paper in papers %}\n{% endfor %}", papers_section)
        return prompt

    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/health')
def health_check():
    return "OK"

@app.route('/deepseek_backend/create_session', methods=['POST'])
def create_session():
    data = flask.request.get_json()
    session_name = data.get('session_name', 'New Chat')
    session_id = str(uuid.uuid4())
    
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sessions (session_id, session_name)
        VALUES (%s, %s)
    """, (session_id, session_name))
    conn.commit()
    conn.close()
    
    return flask.jsonify({
        'session_id': session_id,
        'session_name': session_name
    })

@app.route('/deepseek_backend/get_session')
def get_sessions():
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT session_id, session_name 
        FROM sessions 
        ORDER BY updated_at DESC
    """)
    sessions = [{'session_id': row[0], 'session_name': row[1]} for row in cursor.fetchall()]
    conn.close()
    return flask.jsonify(sessions)

@app.route('/deepseek_backend/delete_session', methods=['POST'])
def delete_session():
    data = flask.request.get_json()
    session_id = data.get('session_id')
    
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE session_id = %s", (session_id,))
    cursor.execute("DELETE FROM sessions WHERE session_id = %s", (session_id,))
    conn.commit()
    conn.close()
    
    return flask.jsonify({'status': 'success'})

@app.route('/deepseek_backend/load_chat/<session_id>')
def load_chat(session_id):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, content 
        FROM messages 
        WHERE session_id = %s 
        ORDER BY created_at ASC
    """, (session_id,))
    messages = [{'role': row[0], 'content': row[1]} for row in cursor.fetchall()]
    conn.close()
    return flask.jsonify(messages)

@app.route('/deepseek_backend/save_chat', methods=['POST'])
def save_chat():
    data = flask.request.get_json()
    session_id = data.get('session_id')
    user_message = data.get('user')
    assistant_message = data.get('assistant')
    
    conn = connect_to_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE sessions 
        SET updated_at = CURRENT_TIMESTAMP 
        WHERE session_id = %s
    """, (session_id,))
    
    cursor.execute("""
        INSERT INTO messages (session_id, role, content)
        VALUES (%s, %s, %s)
    """, (session_id, 'user', user_message))
    
    cursor.execute("""
        INSERT INTO messages (session_id, role, content)
        VALUES (%s, %s, %s)
    """, (session_id, 'assistant', assistant_message))
    
    conn.commit()
    conn.close()
    return flask.jsonify({'status': 'success'})

@app.route('/deepseek/api/chat', methods=['POST'])
def chat():
    data = flask.request.get_json()
    messages = data.get('messages', [])
    
    # Get the last user message
    user_message = next((msg['content'] for msg in reversed(messages) if msg['role'] == 'user'), None)
    if not user_message:
        return flask.jsonify({'error': 'No user message found'}), 400
    
    # Get the last 10 messages for context
    conversation_history = messages[-10:] if len(messages) > 10 else messages
    
    conn = connect_to_db()
    try:
        response = get_prompt(conn, user_message, conversation_history)
        
        return flask.jsonify({
            'message': {
                'content': response
            }
        })
    except Exception as e:
        return flask.jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/deepseek/api/generate', methods=['POST'])
def generate():
    data = flask.request.get_json()
    prompt = data.get('prompt', '')
    
    conn = connect_to_db()
    try:
        response = get_prompt(conn, prompt)
        return flask.jsonify({'response': response})
    except Exception as e:
        return flask.jsonify({'error': str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    conn = connect_to_db()
    create_table(conn)
    conn.close()
    app.run(host='0.0.0.0', port=5000)
