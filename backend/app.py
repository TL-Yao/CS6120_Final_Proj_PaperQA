import os
import requests
import streamlit as st

# Configurable endpoints

QUERY_API = f"http://{os.getenv('DP_HOST')}:{os.getenv('DP_PORT')}/query"
LLM_ENDPOINT  = os.getenv('LLM_ENDPOINT')

TOP_K_DEFAULT = 5
CONFIDENCE_DEFAULT = 0.5
LLM_MODEL = "llama3"

CANNOT_ANSWER_PHRASE = "This question cannot be answered based on the given context."

PROMPT_TEMPLATE = """\
Your are Assistant, answer the question below with the previous conversations and context.

Previous conversations:

{conversations}

----
Context (with confidence scores):

{context}

----
Question: {question}

Write an answer based on the context. If the context provides insufficient information or the question is not a question, such as "hello", "hi", "?", reply "{cannot_answer}" only and do not mention any other thing, including provided references.\n 
For each part of your answer, indicate which sources most support with [source_indicator] such as [1]. 
Write in the style of a Wikipedia article, with concise sentences and coherent paragraphs. The context comes from a variety of sources and is only a summary, so there may be inaccuracies or ambiguities. 
If quotes are present and relevant, use them in the answer. This answer will go directly onto Wikipedia, so do not add any extraneous information.

At the end of your answer, include references you used as the following format exactly:

References:

[1] Title: <title_1>
    Relevance: <relevance_1>
    Excerpt: <short supporting snippet from the context>

[2] Title: <title_2>
    Relevance: <relevance_2>
    Excerpt: <short supporting snippet from the context>

...
Each reference **must include** an excerpt from the context that directly supports the corresponding claim.
If there is no such excerpt, do not include that reference.

Answer:"""


def build_prompt(question: str, context_docs: list, conversation_history: list = None) -> str:
    context_block = ""
    for idx, paper in enumerate(context_docs, start=1):
        meta = paper.get("metadata", {})
        context_block += (
            f"[{idx}] \"{meta.get('title', 'Unknown Title')}\" "
            f"(arXiv:{meta.get('arxiv_id', 'N/A')}, Confidence: {paper.get('confidence', 0.0):.2f})\n"
            f"URL: {meta.get('url', 'N/A')}\n"
            f"Section Content: {paper.get('content', 'N/A')}\n\n"
        )

    history_block = ""
    if conversation_history:
        for role, msg in conversation_history[-5:-1]:
            role_name = "User" if role == "user" else "Assistant"
            history_block += f"{role_name}: {msg}\n"
        history_block += "\n"

    return PROMPT_TEMPLATE.format(
        conversations=history_block,
        context=context_block.strip(),
        question=question,
        cannot_answer=CANNOT_ANSWER_PHRASE
    )



def query_vector_db(query: str, top_k: int = TOP_K_DEFAULT, confidence: float = CONFIDENCE_DEFAULT) -> list:
    try:
        response = requests.get(
            QUERY_API,
            params={"query": query, "top_k": top_k, "confidence_threshold": confidence},
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to query vector DB: {e}")


def call_llm(prompt: str) -> str:
    try:
        response = requests.post(
            LLM_ENDPOINT,
            json={"prompt": prompt, "model": LLM_MODEL, "stream": False},
            timeout=120
        )
        response.raise_for_status()
        return response.json().get("response") or response.text
    except requests.RequestException as e:
        raise RuntimeError(f"LLM backend error: {e}")


# Streamlit App Logic
st.set_page_config(page_title="Paper Q&A")
st.title("Paper Q&A")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display history
for role, msg in st.session_state.chat_history:
    st.chat_message(role).write(msg)

# Input
if user_input := st.chat_input("Type your question..."):
    st.chat_message("user").write(user_input)
    st.session_state.chat_history.append(("user", user_input))

    placeholder = st.empty()
    try:
        placeholder.info("Retrieving relevant documents...")
        retrieved_context = query_vector_db(user_input)

        placeholder.info("Constructing prompt...")
        prompt = build_prompt(user_input, retrieved_context, st.session_state.chat_history)

        print(prompt)

        placeholder.info("Generating answer...")
        answer = call_llm(prompt)

    except Exception as e:
        answer = f"Error: {e}"
    finally:
        placeholder.empty()

    st.chat_message("assistant").write(answer)
    st.session_state.chat_history.append(("assistant", answer))
