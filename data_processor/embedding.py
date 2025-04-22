from pymilvus.model.hybrid import BGEM3EmbeddingFunction
from FlagEmbedding import FlagModel
from transformers import AutoTokenizer
import numpy as np

from logger_config import setup_logger

logger = setup_logger(__name__)

# 在文件顶部添加全局变量
global_model = None
global_tokenizer = None

def init_embedding_model():
    """
    Initialize the global embedding model and tokenizer.
    """
    global global_model, global_tokenizer
    if global_model is None:
        global_tokenizer = get_tokenizer()
        global_model = get_embedding_model()
    return global_model, global_tokenizer

def get_tokenizer():
    return AutoTokenizer.from_pretrained("BAAI/bge-base-en-v1.5")

def get_embedding_model():
    return FlagModel(
        "BAAI/bge-base-en-v1.5",
    )

def check_token_length(content: str, tokenizer) -> bool:
    """
    Check the token length of the content.
    """
    # 统计 token 数量（注意 padding=False）
    tokenized = tokenizer(content, padding=False, truncation=False, return_tensors="pt")
    token_count = tokenized["input_ids"].shape[1]

    logger.info(f"Token count: {token_count}")
    return token_count <= 512

def embed_passage(content: str) -> np.ndarray:
    """
    Embed a passage using the embedding model.
    """
    global global_model, global_tokenizer
    if global_model is None:
        global_model, global_tokenizer = init_embedding_model()
    
    check_token_length(content=content, tokenizer=global_tokenizer)
    docs_embeddings = global_model.encode(content)
    return docs_embeddings

def embed_query(query: str) -> np.ndarray:
    """
    Embed a query using the embedding model.
    """
    global global_model, global_tokenizer
    if global_model is None:
        global_model, global_tokenizer = init_embedding_model()
        global_model.instruction = "Represent this sentence for searching relevant passages:"
    
    check_token_length(content=query, tokenizer=global_tokenizer)
    query_embeddings = global_model.encode(query)
    return query_embeddings