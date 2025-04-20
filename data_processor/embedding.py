from pymilvus.model.hybrid import BGEM3EmbeddingFunction
from FlagEmbedding import FlagModel
from transformers import AutoTokenizer
import numpy as np

from logger_config import setup_logger

logger = setup_logger(__name__)

def check_token_length(content: str) -> bool:
    """
    Check the token length of the content.
    """
    tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-base-en-v1.5")


    # 统计 token 数量（注意 padding=False）
    tokenized = tokenizer(content, padding=False, truncation=False, return_tensors="pt")
    token_count = tokenized["input_ids"].shape[1]

    logger.info(f"Token count: {token_count}")
    return token_count <= 512

def embed_passage(content: str) -> np.ndarray:
    """
    Embed a passage using the embedding model.
    """
    ef = FlagModel(
        "BAAI/bge-base-en-v1.5",
    )

    check_token_length(content=content)
    # ef = BGEM3EmbeddingFunction(
    #     model_name='BAAI/bge-m3', # Specify the model name
    #     device='cpu', # Specify the device to use, e.g., 'cpu' or 'cuda:0'
    #     use_fp16=False # Specify whether to use fp16. Set to `False` if `device` is `cpu`.
    # )

    # docs_embeddings = ef.encode_documents(docs)
    docs_embeddings = ef.encode(content)

    return docs_embeddings

def embed_query(query: str) -> np.ndarray:
    """
    Embed a query using the embedding model.
    """
    ef = FlagModel(
        "BAAI/bge-base-en-v1.5",
        query_instruction_for_retrieval="Represent this sentence for searching relevant passages:"
    )

    check_token_length(query)
    query_embeddings = ef.encode(query)

    return query_embeddings