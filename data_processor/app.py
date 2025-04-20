from flask import Flask, jsonify, request
from config import Config
from boto3_actions import get_first_folder, get_file_content, cp_file, delete_folder
from logger_config import setup_logger
from embedding import embed_query
from milvus import query_relative_chunks, query_paper_by_id
import re
from file_content_process import process_summarization, process_metadata
from utils import confidence_to_distance, distance_to_confidence
app = Flask(__name__)
app.config.from_object(Config)

logger = setup_logger(__name__)

@app.route('/health')
def health():
    return 'OK'

@app.route('/embedding_file')
def embedding_file():
    try:
        arxiv_id, files_info = get_first_folder(app.config.get('MINIO_PAPER_DATA_BUCKET'))
        if not arxiv_id:
            return jsonify({'error': 'no folder found in bucket'}), 404

        metadata_obj_key = None
        summarization_obj_key = None
        chunk_obj_keys = []

            # get metadata, summarization and chunk file object keys
        for file_info in files_info:
            if "metadata.json" in file_info['object_key']:
                metadata_obj_key = file_info['object_key']
            elif "summarization.json" in file_info['object_key']:
                summarization_obj_key = file_info['object_key']
            elif re.match(r'.*/chunk_\d+\.txt', file_info['object_key']):
                chunk_obj_keys.append(file_info['object_key'])
            else:
                print(f"Unknown file: {file_info['object_key']}")

        # process metadata information
        metadata = get_file_content(metadata_obj_key, app.config.get('MINIO_PAPER_DATA_BUCKET'))
        paper_id = process_metadata(metadata)
        if not paper_id:
            logger.error(f"failed to process metadata for arxiv_id: {arxiv_id}")
            return jsonify({'error': 'failed to process metadata'}), 500

        # process summarization information
        summarization = get_file_content(summarization_obj_key, app.config.get('MINIO_PAPER_DATA_BUCKET'))
        process_summarization(summarization, paper_id, arxiv_id)

        # copy chunks to processed bucket
        for chunk_obj_key in chunk_obj_keys:
            cp_file(chunk_obj_key, app.config.get('MINIO_PAPER_DATA_BUCKET'), app.config.get('MINIO_PROCESSED_DATA_BUCKET'))

        # delete processed folder from paper data bucket
        delete_folder(app.config.get('MINIO_PAPER_DATA_BUCKET'), arxiv_id)

    except Exception as e:
        logger.error(f"error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

    return jsonify({'arxiv_id': arxiv_id, 'status': 'success'}), 200

@app.route('/query')
def query():
    # read query parameters from request
    query_params = request.args
    query_text = query_params.get('query')
    top_k = query_params.get('top_k', 5)
    confidence_threshold = query_params.get('confidence_threshold', 0.5)

    # validate query parameters
    if not query_text:
        logger.error(f"query text is required")
        return jsonify({'error': 'query text is required'}), 400
    
    if not top_k:
        logger.error(f"top_k is required")
        return jsonify({'error': 'top_k is required'}), 400
    
    # query milvus
    query_embeddings = embed_query(query_text)
    distance_threshold = confidence_to_distance(float(confidence_threshold))
    relative_chunks = query_relative_chunks(query_embeddings.tolist(), top_k, distance_threshold)

    if not relative_chunks:
        logger.error(f"no relative chunks found")
        return jsonify([]), 200

    response = []
    for chunk in relative_chunks[0]:
        distance = chunk['distance']
        entity = chunk['entity']
        chunk_file_obj_key = entity['chunk_file']
        summary = entity['content']
        paper_id = entity['paper_id']

        # query paper info
        paper_info = query_paper_by_id(int(paper_id))[0]
        authors = paper_info['authors']
        title = paper_info['title']
        pdf_url = paper_info['pdf_url']
        arxiv_id = paper_info['arxiv_id']

        response.append({
            "metadata": {
                "title": title,
                "arxiv_id": arxiv_id,
                "url": pdf_url,
                "authors": authors
            },
            "confidence": distance_to_confidence(distance),
            "content": summary
        })
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)