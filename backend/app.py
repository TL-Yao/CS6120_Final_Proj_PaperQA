import os
import requests
import streamlit as st
import sys
# Configurable endpoints

QUERY_API = f"http://{os.getenv('DP_HOST')}:{os.getenv('DP_PORT')}/query"
LLM_ENDPOINT  = os.getenv('LLM_ENDPOINT')

TOP_K_DEFAULT = 5
CONFIDENCE_DEFAULT = 0.5
LLM_MODEL = "llama3"

CANNOT_ANSWER_PHRASE = "This question cannot be answered based on the given context."

# PROMPT_TEMPLATE = """\
# You are a Paper Q&A assistant, answer the question below with the previous conversations and provided paper context.

# Previous conversations:

# {conversations}

# ----
# Paper Context(with confidence scores):

# {context}

# ----
# Question: {question}

# Write an answer based on the paper context. If the context provides insufficient information or the question is not a question, such as "hello", "hi", "?", reply "{cannot_answer}" only and do not mention any other thing, including provided references.\n  
# Write in the style of a Wikipedia article, with concise sentences and coherent paragraphs. The context comes from a variety of sources and is only a summary, so there may be inaccuracies or ambiguities. 
# If quotes are present and relevant, use them in the answer. If not or the question is not about the quotes, do not mention them and do not include them in the references

# At the end of your answer, include references you used as the following format exactly:

# References:

# Title: <title>
# arXiv ID: <arxiv_id>
# ...

# Answer:

# """

PROMPT_TEMPLATE = """\
You are a Paper Q&A assistant that helps users understand academic papers and research.

Previous conversations:
{conversations}

----
Paper Context (with confidence scores):
{context}

----
Question: {question}

INSTRUCTIONS:
1. EVALUATE THE QUESTION:
   - If it's related to the paper context, answer based on the provided information.
   - If it's a general academic question but not covered in the context, use your knowledge to provide a helpful response, clearly indicating you're not using the paper context.
   - If it's a simple greeting or non-question (e.g., "hello", "hi", "?"), respond conversationally and briefly.
   - If it's inappropriate or harmful, reply with "{cannot_answer}" only.

2. ANSWER FORMAT:
   - Write in a clear, concise Wikipedia style with coherent paragraphs.
   - Be aware that the context may contain inaccuracies or ambiguities.
   - Use relevant quotes if available and appropriate.

3. REFERENCES:
   - If you used information from the provided context, include references in this exact format:
     
     References:
     
     Title: <title>
     arXiv ID: <arxiv_id>
     [Include only the fields that are provided in the context]
   
   - Only include references you actually used in your answer.
   - If you didn't use the provided context, omit the References section entirely.

Answer:
"""

REFORM_QUERY_PROMPT = """\
You are a Query Reformulation Agent designed to help with RAG (Retrieval-Augmented Generation) systems. Your task is to reformulate user queries in a way that:

1. Makes the query self-contained and context-independent so it can be used effectively for embedding and vector database retrieval.
2. Resolves pronouns and references by looking at the previous conversation history.
3. Preserves the original intent and meaning of the user's question.
4. Does NOT add unnecessary information or modify questions that are already self-contained.
5. Your output MUST NOT exceed 450 words.

CONVERSATION HISTORY:
{conversation_history}

CURRENT USER QUERY:
{user_query}

Instructions:
- If the current query contains references to previous questions/answers (like "it", "this", "that", "these", etc.), replace them with their specific referents from the conversation history.
- If the query is a follow-up question, incorporate relevant context from previous exchanges to make it standalone.
- If the query is already self-contained OR introduces a new topic unrelated to the previous conversation, leave it unchanged.
- Format your response as a clear, complete question that could be understood by someone who hasn't seen the previous conversation.
- DO NOT add information that wasn't implied or referenced in the conversation.
- Keep the reformulated query under 450 words.

Your output MUST be ONLY the reformulated query with NO explanations or additional text.
"""

def build_prompt(question: str, context_docs: list, conversation_history: list = None) -> str:
    context_block = ""
    for idx, paper in enumerate(context_docs, start=1):
        meta = paper.get("metadata", {})
        context_block += (
            f"{meta.get('title', 'Unknown Title')} "
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

def build_reform_query_prompt(user_query: str, conversation_history: list) -> str:
    history_block = ""
    if conversation_history:
        for role, msg in conversation_history[-5:-1]:
            role_name = "User" if role == "user" else "Assistant"
            history_block += f"{role_name}: {msg}\n"
        history_block += "\n"

    return REFORM_QUERY_PROMPT.format(
        user_query=user_query,
        conversation_history=history_block
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
            json={"prompt": prompt, "model": LLM_MODEL, "stream": False, "temperature": 0},
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
        reform_query_prompt = build_reform_query_prompt(user_input, st.session_state.chat_history)
        # print(reform_query_prompt)
        reform_query = call_llm(reform_query_prompt)
        print(reform_query)
        sys.stdout.flush()
        prompt = build_prompt(reform_query, retrieved_context, st.session_state.chat_history)

        # print(prompt)

        placeholder.info("Generating answer...")
        answer = call_llm(prompt)

    except Exception as e:
        answer = f"Error: {e}"
    finally:
        placeholder.empty()

    st.chat_message("assistant").write(answer)
    st.session_state.chat_history.append(("assistant", answer))
