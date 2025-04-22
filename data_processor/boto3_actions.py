import boto3
from logger_config import setup_logger
from flask import Flask
from config import Config
import os

app = Flask(__name__)
app.config.from_object(Config)
logger = setup_logger(__name__)

def get_client():
    return boto3.client('s3',
        aws_access_key_id=app.config.get('MINIO_ACCESS_KEY'),
        aws_secret_access_key=app.config.get('MINIO_SECRET_KEY'),
        endpoint_url=app.config.get('MINIO_ENDPOINT'),
        config=boto3.session.Config(signature_version='s3v4'),
        verify=False)

def get_first_folder_os(root_path):
    # read all folders path in the path
    folders = os.listdir(root_path)
    if folders:
        logger.info(f"Found folder: {os.path.join(root_path, folders[0])}")
        # skip hidden folders
        for folder in folders:
            if folder.startswith('.'):
                continue
            arxiv_id = folder
            file_paths = []
            for file in os.listdir(os.path.join(root_path, arxiv_id)):
                file_paths.append(os.path.join(root_path, arxiv_id, file))
            return arxiv_id, file_paths
    return None, None

def get_file_content(object_key, bucket_name):
    s3 = get_client()

    response = s3.get_object(Bucket=bucket_name, Key=object_key)
    return response['Body'].read().decode('utf-8')

def get_file_content_os(path):
    with open(path, 'r') as file:
        return file.read()

def upload_file(path, bucket_name, arxiv_id):
    # upload the folder 
    file_name = os.path.basename(path)
    s3 = get_client()
    s3.upload_file(path, bucket_name, f"{arxiv_id}/{file_name}")

def delete_file_os(root_path):
    for file in os.listdir(root_path):
        os.remove(os.path.join(root_path, file))
    os.rmdir(root_path)