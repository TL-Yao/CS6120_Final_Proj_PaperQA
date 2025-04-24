import os
import requests
import streamlit as st

QUERY_API = f"http://{os.getenv('DP_HOST')}:{os.getenv('DP_PORT')}/query"
LLM_ENDPOINT  = os.getenv('LLM_ENDPOINT')

TOP_K_DEFAULT = 5
CONFIDENCE_DEFAULT = 0.0

# prompt template
CANNOT_ANSWER_PHRASE = "I cannot answer"
PROMPT = (
    f"Answer the question below using the information from the provided context.\n\n"
    f"Context (with confidence level):\n\n{{context}}\n\n"
    f"----\n\n"
    f"Question: {{question}}\n\n"
    f"Write a concise and well-structured answer in the style of a Wikipedia article.\n"
    f"Use citation numbers like [1], [2], etc., to indicate which parts of the context support each claim.\n"
    # f"Do not cite any information that is not explicitly present in the context.\n\n"
    f"Structure your output as follows:\n\n"
    f"Answer:\n"
    f"<Write your answer here, referencing sources with [n]>\n\n"
    f"References:\n"
    f"[1] Title: <title_1>\n"
    f"    Relevance: <relevance_1>\n"
    f"    Excerpt: <short supporting snippet from the context>\n"
    f"[2] Title: <title_2>\n"
    f"    Relevance: <relevance_2>\n"
    f"    Excerpt: <short supporting snippet from the context>\n"
    f"...\n\n"
    f"If the context provides insufficient information, respond with: \"{CANNOT_ANSWER_PHRASE}.\"\n"
)


def get_prompt(current_query: str, conversation_history=None, *, top_k=TOP_K_DEFAULT, confidence=CONFIDENCE_DEFAULT):
    """
    Build an LLM prompt by enriching the user query with vector-DB context.
    
    Args:
        conn: Placeholder for DB conn (if needed).
        current_query: The user's current question.
        conversation_history: List of previous chat messages (dicts with 'role' and 'content').
        top_k: Number of top vector matches to retrieve.
        confidence: Minimum confidence threshold for retrieval.
    
    Returns:
        A tuple of (filled_prompt, context_block_string)
    """
    if conversation_history is None:
        conversation_history = []

    # 1. Format dialogue history
    history_text = "\n".join(
        f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}" for msg in conversation_history
    )
    full_query = f"{history_text}\n\nCurrent Query: {current_query}" if history_text else current_query

    # 2. Query vector DB for context
    try:
        vect_resp = requests.get(
            QUERY_API,
            params={"query": current_query, "top_k": top_k, "confidence_threshold": confidence},
            timeout=60
        )
        vect_resp.raise_for_status()
        results = vect_resp.json()
    except Exception as exc:
        raise RuntimeError(f"Vector-DB request failed → {exc}") from exc

    # 3. Format context block
    papers_block = ""
    for idx, paper in enumerate(results, start=1):
        meta = paper.get("metadata", {})
        papers_block += (
            f"[{idx}] \"{meta.get('title', 'Unknown Title')}\" "
            f"(arXiv:{meta.get('arxiv_id', 'N/A')}, Confidence: {paper.get('confidence', 0.0):.2f})\n"
            f"URL: {meta.get('url', 'N/A')}\n"
            f"Section Content: {paper.get('content', 'N/A')}\n\n"
        )

    # 4. Format final prompt
    filled_prompt = PROMPT.format(
        context=papers_block.strip(),
        question=current_query
    )

    return filled_prompt



# Placeholder for backend integration
def send_to_llm_backend(user_prompt: str) -> str:
    """
    Replace this function with an actual API call to your LLM backend.
    For example, you could send an HTTP POST request to a FastAPI or Flask endpoint.
    """

    full_prompt = get_prompt(user_prompt, [])

    llm_resp = requests.post(LLM_ENDPOINT, json={"prompt": full_prompt, "model": "llama3", "stream": False}, timeout=120)
    llm_resp.raise_for_status()
    asst_text = llm_resp.json().get("response") or llm_resp.text

    return asst_text

# Initialize session state to store chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Set page title and header
st.set_page_config(page_title="LLM Chat")
st.title("LLM Chat Interface")

# Display previous messages from the conversation
for role, message in st.session_state.chat_history:
    if role == "user":
        st.chat_message("user").write(message)
    else:
        st.chat_message("assistant").write(message)

# Input field for the user to type a new message
if prompt := st.chat_input("Type a message and press Enter..."):
    # Display user message
    st.chat_message("user").write(prompt)
    st.session_state.chat_history.append(("user", prompt))

    # Call backend function to get LLM response
    with st.spinner("Waiting for response..."):
        try:
            response = send_to_llm_backend(prompt)
        except Exception as e:
            response = f"Error from backend: {e}"

    # Display assistant response
    st.chat_message("assistant").write(response)
    st.session_state.chat_history.append(("assistant", response))
