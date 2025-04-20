import numpy as np
from pymilvus import MilvusClient
from pymilvus.client.types import ExtraList
from flask import Flask
from config import Config
from logger_config import setup_logger

logger = setup_logger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

def get_client(collections: list[str]):
    client = MilvusClient(
        uri=f"http://{app.config.get('MILVUS_HOST')}:{app.config.get('MILVUS_PORT')}",
    )
    for collection in collections:
        client.load_collection(collection_name=collection)
    return client

def insert_paper_metadata(arxiv_id: str, title: str, published: str, updated: str, authors: list[str], pdf_url: str) -> int:
    try:
        client = get_client(["paper_metadata"])
        paper_summary_emb = np.zeros(768)

        # prepare insert data
        data = [
            {
                "arxiv_id": arxiv_id,
                "title": title,
                "published": published,
                "updated": updated,
                "authors": authors,
                "pdf_url": pdf_url,
                "paper_summary_emb": paper_summary_emb.tolist()
            }
        ]

        # check if the data with same arxiv_id exists
        query_result = client.query(collection_name="paper_metadata", filter=f"arxiv_id == '{arxiv_id}'", output_fields=["arxiv_id"])
        if query_result:
            logger.info(f"query_result: {query_result}, type: {type(query_result)}")
            if type(query_result) is ExtraList:
                paper_id = query_result[0]['id']
            else:
                paper_id = query_result['ids'][0]
            logger.info(f"paper with arxiv_id {arxiv_id} already exists, paper_id: {paper_id}")
            return paper_id

        # insert data and get the inserted record's id
        insert_result = client.insert(collection_name="paper_metadata", data=data)
        logger.info(f"insert_result: {insert_result}, type: {type(insert_result)}")
        if type(insert_result) is ExtraList:
            paper_id = insert_result[0]['id']
        else:
            paper_id = insert_result['ids'][0]
        logger.info(f"inserted paper_id: {paper_id}")
        return paper_id

        # return papaer_id
    except Exception as e:
        logger.error(f"error: {str(e)}", exc_info=True)
        return None
    finally:
        client.release_collection(collection_name="paper_metadata")

def insert_paper_summary(prompt: str, content: str, chunk_file: str, paper_id: int, embedding: list[float]):
    try:
        client = get_client(["chunk_summaries"])
        data = [
            {
                "prompt": prompt,
                "content": content,
                "chunk_file": chunk_file,
                "paper_id": paper_id,
                "embedding": embedding
            }
        ]

        # check if the data with same paper_id and chunk_file exists
        query_result = client.query(collection_name="chunk_summaries", filter=f"paper_id == {paper_id} and chunk_file == '{chunk_file}'", output_fields=["paper_id", "chunk_file"])
        if len(query_result) > 0:
            logger.info(f"chunk with paper_id {paper_id} and chunk_file {chunk_file} already exists")
            return

        client.insert(collection_name="chunk_summaries", data=data)
    except Exception as e:
        logger.error(f"fail when inserting paper chunk summaries, error: {str(e)}", exc_info=True)
        return
    finally:
        client.release_collection(collection_name="chunk_summaries")

def query_paper_by_id(paper_id: int) -> list[str]:
    try:
        client = get_client(["paper_metadata"])
        query_result = client.query(collection_name="paper_metadata", filter=f"id == {paper_id}", output_fields=["arxiv_id", "title", "published", "updated", "authors", "pdf_url"])
        return query_result
    except Exception as e:
        logger.error(f"fail when querying paper by id, error: {str(e)}", exc_info=True)
        return []

def query_relative_chunks(query_embeddings: list[float], top_k: int, distance_threshold: float) -> list[str]:
    try:
        client = get_client(["chunk_summaries"])
        search_params = {
            "metric_type": "COSINE",
            "params": {
                "radius": distance_threshold
            }
        }

        res = client.search(
            collection_name="chunk_summaries",
            data=[query_embeddings],
            limit=top_k,
            output_fields=["content", "paper_id", "chunk_file", "embedding"],
            search_params=search_params
        )
        return res
    except Exception as e:
        logger.error(f"fail when querying relative chunks, error: {str(e)}", exc_info=True)
        return []