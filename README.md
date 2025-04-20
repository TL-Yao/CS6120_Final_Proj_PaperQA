## User Guidance

### Sample Env
```
MINIO_ENDPOINT=http://minio:9000
MINIO_HTTP_SECURE=False
MINIO_ACCESS_KEY=Test12345
MINIO_SECRET_KEY=Test12345
MINIO_PAPER_DATA_BUCKET=paper-data-bucket
MINIO_PROCESSED_DATA_BUCKET=processed-bucket

# milvus
MILVUS_MINIO_ADDRESS=minio
ETCD_ENDPOINTS=http://etcd:2379
MILVUS_BUCKET_NAME=milvus
MILVUS_HOST=milvus
MILVUS_PORT=19530

# postgres
TZ=America/Los_Angeles
PGTZ=America/Los_Angeles
POSTGRES_USER=root
POSTGRES_PASSWORD=Test12345
POSTGRES_DB=postgres
```

1. Create .env file and ensure all required configurations are set correctly
2. Run `docker-compose up -d --build` to start all containers
3. Download processed paper data from {placeholder} or start crawler to fetch paper data
4. Place processed paper data into `MINIO_PAPER_DATA_BUCKET`
5. Enter container using `docker exec -it data_processor bash`, run `bash data_processor/process_paper_data.sh` until all papers are inserted into milvus database.

## Data Processor Service
This service performs vectorization on processed paper texts and user queries, and retrieves the most relevant content from the vector database based on the user’s query.

### Script
```
bash data_processor/process_paper_data.sh
```

This script reads pre-processed paper data from S3, performs vectorization, stores the resulting vectors in a Milvus database, and saves the original text back to S3.

### APIs
GET: /query

Query Params：

- k: int, required, top k matched records found in vector DB
- query: string, required, user's query input 
- confidence: float, optional, minimum similarity score threshold for returned results (0-1)

Return:
```json
[
  {
    "metadata": {
      "title": "",
      "arxiv_id": "",
      "url": "",
      "authors": [""]
    },
    "confidence": 0.0,  # float number between 0 - 1
    "content": ""
  }
]
```

## Paper Crawler

###  Paper Processor Output Format

#### File Structure
```
prompts.json              # prompts we used to generate summary
{arxiv_id}/
├── metadata.json         # Metadata for the paper (title, authors, etc.)
├── summarization.json    # generated summary of each chunk of the paper
├── chunk_1.txt           # Chunked text part 1
├── chunk_2.txt           # Chunked text part 2
├── ...                   # Additional chunks
```

#### metadata.json
```json
{
  "arxiv_id": "",
  "title": "",
  "published": "2025-04-14T17:34:06+00:00",
  "updated": "2025-04-14T17:34:06+00:00",
  "authors": [""],
  "pdf_url": ""
}
```

#### summarization.json

```json
{
  "chunks": [
    {
      "chunk_file": "",
      "summaries": [
        {
          "prompt": "1",
          "content": ""
        }
      ]
    }
  ]
}
```

#### prompts.json
The prompt IDs should be incremental, and any prompt once written should not be modified or deleted. Even if a prompt is deleted, its ID should not be reused.
```json
{
    "1": ""
}
```
