import psycopg2
import flask
import requests

app = flask.Flask(__name__)
VECTOR_DB_API = "vector_dp_url/query"

def connect_to_db():
    conn = psycopg2.connect(
        host="localhost",
        database="dialog",
        user="user",
        password="password",
        port="5432"
    )
    return conn

def create_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dialog (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            context TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    # future process: get summary
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



def get_prompt(conn, user_id, top_k = 5, confidence = 0.0):
    dialog = get_dialog(conn, user_id)
    if not dialog:
        return "No dialog history found for this user."
        
    params = {
        "query": dialog,
        "top_k": top_k,
        "confidence": confidence
    }
    try:
        response = requests.post(VECTOR_DB_API, params=params)
        results = response.json()
        
        # Load the template
        with open('template.txt', 'r') as f:
            template = f.read()
            
        # Format the template with the results
        prompt = template.replace("{{user_query}}", dialog)
        
        # Format papers section
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
