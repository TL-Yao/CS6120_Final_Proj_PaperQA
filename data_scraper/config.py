RAW_DATA_PATH = "raw_data"
PROCESSED_DATA_PATH = "processed_data"

# for arxiv_downloader.py
ARXIV_QUERY = "cat:cs.AI AND cat:cs.LG"
ARXIV_MAXIMUM_PAPER_LIMIT = 200  # maximum number of papers you want to fetch
ARXIV_FETCH_DELAY_TIME_IN_SECONDS = 30
ARXIV_PDF_DOWNLOAD_DELAY_TIME_IN_SECONDS = 10

# for pdf_processor.py
PDF_PROCESSOR_GROBID_URL = "https://kermitt2-grobid.hf.space/api/processFulltextDocument"  # a public GROBID API
PDF_PROCESSOR_MIN_CHARACTER_CHUNK_THRESHOLD = 50  # sections from GROBID output less than this will be discarded
PDF_PROCESSOR_GROBID_API_CALL_DELAY_TIME_IN_SECONDS = 10

# for summarizer.py
SUMMARIZER_MAX_SUMMARY_WORD = 300
SUMMARIZER_GCP_PROJECT_ID = "third-expanse-377300"
SUMMARIZER_GCP_LOCATION = "us-west1"
SUMMARIZER_GCP_MODEL_NAME = "gemini-2.0-flash-lite-001"
