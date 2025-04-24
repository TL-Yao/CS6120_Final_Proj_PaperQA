# Ask the Paper: An LLM-Based Assistant for Academic Papers

## Live Demo Link
http://34.122.121.114:80

## Installation Guide
### Requirements
- Docker and Docker-Compose
- Ollama with running llama3, for more information, check [Ollama Installation Guide](https://ollama.com/download/mac) and [llama3 on Ollama](https://ollama.com/library/llama3)
- Create a `.env` file on the under `CS6120_FINAL_PROJ_PAPERQA` folder according to the instructions below

### Sample Dot Env
```
MINIO_HOST_NAME=minio
MINIO_PORT=9000
MINIO_ENDPOINT=http://minio:9000
MINIO_HTTP_SECURE=False
MINIO_ACCESS_KEY=Test12345
MINIO_SECRET_KEY=Test12345
PAPER_DATA_ROOT_PATH=/app/paper_data
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
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=root
POSTGRES_PASSWORD=Test12345
POSTGRES_DB=postgres

# data_processor
DP_HOST=data_processor
DP_PORT=8000

# endpoint to your LLM interface
LLM_ENDPOINT=http://localhost:11434/api/generate
```
- LLM_ENDPOINT is an Ollama API endpoint, example: `http://localhost:11434/api/generate`
- Create a .env file in the working directory and ensure all required configurations are set correctly.

> **Warning**
> 
> If you are using different `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` or `MILVUS_BUCKET_NAME`, please also update the values in `milvus.yaml`

### Build Docker Images and Start Your Docker Containers

Run `docker compose up --build -d`

### Import Processed Paper Data
#### Recovery From Backup Milvus Data (Recommended)
1. Download and unzip backup Milvus backup data from [here](https://drive.google.com/drive/folders/15yJtVvoRGLHpx3mHiP2K8P1-dwL9UiKb?usp=sharing)
2. Place the `backup` folder under `backup_milvus`
3. Start the container `docker compose up -d --build` and Get into container bash using `docker exec -it data_processor bash`
4. `cd backup_milvus` and run `python backup.py --mode restore`

#### Download Original Paper Data We collected and Embeding them by Yourself
1. Download and unzip processed paper data from [here]() or start the scraper to fetch paper data according to instructions [here](https://github.com/TL-Yao/CS6120_Final_Proj_PaperQA/blob/main/data_scraper/README.md)
2. Place folders containing paper data into `paper_data`
3. Start the container `docker compose up -d --build` and run `bash /app/data_processor/process_paper_data.sh` to embed and insert data into the vector database.


## Overall Project Structure

```bash
CS6120_FINAL_PROJ_PAPERQA/
├── backend/                 # LLM API and User Interface (Streamlit)
├── backup_milvus/           # Backup files for Milvus vector database
├── data_processor/          # Chunk embedding and storing to vector database
├── data_scraper/            # Data collecting, preprocessing, and chunking pipeline
├── DockerFiles/             # Dockerfile and container setup scripts
├── docs/                    # Project documentation
├── .env                     # Environment variable configuration
├── docker-compose.yaml      # Docker Compose setup for containers deployment
├── milvus.yaml              # Configuration file for Milvus vector DB
├── prompts.json             # Prompt templates for chunk summarization
├── .gitignore
└── README.md
```

## Modules
### Data Processor Service
This service performs vectorization on processed paper texts and user queries, and retrieves the most relevant content from the vector database based on the user's query.


#### APIs
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

### Paper Scraper

####  Paper Preprocess Output Format

##### File Structure
```
prompts.json              # prompts we used to generate summary
{arxiv_id}/
├── metadata.json         # Metadata for the paper (title, authors, etc.)
├── summarization.json    # generated summary of each chunk of the paper
├── chunk_1.txt           # Chunked text part 1
├── chunk_2.txt           # Chunked text part 2
├── ...                   # Additional chunks
```

##### metadata.json
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

##### summarization.json

```json
{
  [
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

##### prompts.json
The prompt IDs should be incremental, and any prompt once written should not be modified or deleted. Even if a prompt is deleted, its ID should not be reused.
```json
{
    "1": ""
}
```
