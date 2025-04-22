import yaml
import os
import subprocess
import argparse
from pymilvus import connections, Collection, DataType

BACKUP_NAME = 'backup_milvus'
milvus_backup_yaml_file = '/app/backup_milvus/configs/backup.yaml'
milvus_backup_exe = '/app/backup_milvus/milvus-backup'

# def set_milvus_config():
#     """
#     read environment variables and update milvus.yaml
#     """
#     minio_host = os.getenv('MINIO_HOST_NAME', 'minio')
#     minio_port = os.getenv('MINIO_PORT', '9000')
#     minio_access_key = os.getenv('MINIO_ACCESS_KEY', 'Test12345')
#     minio_secret_key = os.getenv('MINIO_SECRET_KEY', 'Test12345')
#     milvus_bucket_name = os.getenv('MILVUS_BUCKET_NAME', 'milvus')

#     # read yaml file
#     with open(milvus_yaml_file, 'r') as f:
#         config = yaml.safe_load(f)

#     # update minio config
#     config['minio']['address'] = minio_host
#     config['minio']['port'] = int(minio_port)s
#     config['minio']['accessKeyID'] = minio_access_key
#     config['minio']['secretAccessKey'] = minio_secret_key
#     config['minio']['bucketName'] = milvus_bucket_name

#     # write updated config to file
#     with open(milvus_yaml_file, 'w') as f:
#         yaml.dump(config, f, default_flow_style=False)

def set_backup_milvus_config():
    """
    update milvus_backup yaml config file
    """
    milvus_host = os.getenv('MILVUS_HOST', 'milvus')
    milvus_port = os.getenv('MILVUS_PORT', '19530')
    minio_host = os.getenv('MINIO_HOST_NAME', 'minio')
    minio_port = os.getenv('MINIO_PORT', '9000')
    minio_access_key = os.getenv('MINIO_ACCESS_KEY', 'Test12345')
    minio_secret_key = os.getenv('MINIO_SECRET_KEY', 'Test12345')
    milvus_bucket_name = os.getenv('MILVUS_BUCKET_NAME', 'milvus')
    gc_pause_address = f'http://{milvus_host}:{milvus_port}'

    with open(milvus_backup_yaml_file, 'r') as f:
        config = yaml.safe_load(f)

    config['milvus']['address'] = milvus_host
    config['milvus']['port'] = int(milvus_port)
    config['minio']['address'] = minio_host
    config['minio']['port'] = int(minio_port)
    config['minio']['accessKeyID'] = minio_access_key
    config['minio']['secretAccessKey'] = minio_secret_key
    config['minio']['bucketName'] = milvus_bucket_name
    config['minio']['backupStorageType'] = "local"
    config['minio']['backupRootPath'] = "backup"
    config['backup']['gcPause']['address'] = gc_pause_address

    with open(milvus_backup_yaml_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

def run_backup_milvus(backup_name = BACKUP_NAME):
    """
    run backup milvus
    """
    subprocess.run([milvus_backup_exe, 'create', '-n', backup_name])

def create_scalar_index(collection, field_name):
    """Create scalar index for a field"""
    # Get field from collection schema
    field = None
    for f in collection.schema.fields:
        if f.name == field_name:
            field = f
            break
    
    if field is None:
        raise ValueError(f"Field {field_name} not found in collection schema")
    
    if field.dtype in [DataType.INT8, DataType.INT16, DataType.INT32, DataType.INT64, DataType.FLOAT, DataType.DOUBLE]:
        index_params = {
            "index_type": "STL_SORT",
            "metric_type": "COSINE"
        }
    else:
        # For VARCHAR and other types, use inverted index
        index_params = {
            "index_type": "INVERTED",
            "metric_type": "COSINE"
        }
    collection.create_index(field_name=field_name, index_params=index_params)

def rebuild_indexes():
    """
    rebuild indexes for paper_metadata and chunk_summaries
    """
    print("rebuilding indexes...")
    # connect to milvus
    milvus_host = os.getenv('MILVUS_HOST', 'milvus')
    milvus_port = os.getenv('MILVUS_PORT', '19530')
    connections.connect("default", host=milvus_host, port=milvus_port)
    
    # rebuild paper_metadata indexes
    paper_metadata = Collection("paper_metadata")
    
    # rebuild scalar indexes
    scalar_fields = ["arxiv_id", "title", "authors", "published", "updated", "pdf_url"]
    for field_name in scalar_fields:
        create_scalar_index(paper_metadata, field_name)
    
    # rebuild vector index
    paper_metadata.create_index(
        field_name="paper_summary_emb",
        index_params={
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
    )
    
    # rebuild chunk_summaries indexes
    chunk_summaries = Collection("chunk_summaries")
    
    # rebuild scalar indexes
    scalar_fields = ["paper_id", "prompt", "content", "chunk_file"]
    for field_name in scalar_fields:
        create_scalar_index(chunk_summaries, field_name)
    
    # rebuild vector index
    chunk_summaries.create_index(
        field_name="embedding",
        index_params={
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
    )
    
    # load indexes to memory
    paper_metadata.load()
    chunk_summaries.load()
    
    connections.disconnect("default")

def load_backup_milvus(backup_name = BACKUP_NAME):
    """
    load backup milvus and rebuild indexes
    """
    subprocess.run([milvus_backup_exe, 'restore', '-n', backup_name])
    rebuild_indexes()

if __name__ == '__main__':
    # set_milvus_config()
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', type=str, help='backup or restore')
    parser.add_argument('--name', type=str, default=BACKUP_NAME, help='backup name')
    args = parser.parse_args()
    set_backup_milvus_config()

    if args.mode == 'backup':
        run_backup_milvus(args.name)
    elif args.mode == 'restore':
        load_backup_milvus(args.name)
    else:
        raise ValueError(f'Invalid mode: {args.mode}')