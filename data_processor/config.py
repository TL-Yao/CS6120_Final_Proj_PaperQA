import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

class Config:
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "Test12345")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "Test12345")
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
    MINIO_PROCESSED_DATA_BUCKET = os.getenv("MINIO_PROCESSED_DATA_BUCKET", "processed-bucket")
    PAPER_DATA_ROOT_PATH = os.getenv("PAPER_DATA_ROOT_PATH", "/app/processed_data")
    MINIO_HTTP_SECURE = os.getenv("MINIO_HTTP_SECURE", "False").lower() == "true"
    
    # Milvus 配置
    MILVUS_HOST = os.getenv("MILVUS_HOST", "milvus")
    MILVUS_PORT = int(os.getenv("MILVUS_PORT", "19530"))