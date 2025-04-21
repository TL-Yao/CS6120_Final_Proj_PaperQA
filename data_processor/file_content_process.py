from embedding import embed_passage
from milvus import insert_paper_metadata, insert_paper_summary
import json
from logger_config import setup_logger

logger = setup_logger(__name__)

def process_metadata(metadata: str):
    """
    read metadata.json and save to database
    expect metadata.json structure:
    {
        "arxiv_id": "2504.10415",
        "title": "",
        "published": "2025-04-14T17:00:13+00:00",
        "updated": "2025-04-14T17:00:13+00:00",
        "authors": [],
        "pdf_url": ""
    }
    """
    try:
        metadata = json.loads(metadata)
        arxiv_id = metadata.get("arxiv_id")
        title = metadata.get("title")
        published = metadata.get("published")
        updated = metadata.get("updated")
        authors = metadata.get("authors")
        pdf_url = metadata.get("pdf_url")
        papaer_id = insert_paper_metadata(arxiv_id, title, published, updated, authors, pdf_url)
    except Exception as e:
        print(f"Error parsing metadata: {e}")
        return None

    return papaer_id

def process_summarization(summarization: str, paper_id: int, arxiv_id: str):
    try:
        json_summar = json.loads(summarization)
    except Exception as e:
        print(f"Error parsing summarization: {e}")
        return
    
    chunks = json_summar['chunks'] if type(json_summar) == dict else json_summar
    for chunk in chunks:
        chunk_file = f"{arxiv_id}/{chunk['chunk_file']}"
        summaries = chunk['summaries']
        for summary in summaries:
            prompt = summary['prompt']
            content = summary['content']
            summary_embedding = embed_passage(content).tolist()
            insert_paper_summary(prompt, content, chunk_file, paper_id, summary_embedding)
