import boto3
from logger_config import setup_logger
from flask import Flask
from config import Config

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

def get_first_folder(bucket_name):
    s3 = get_client()
        
    # list all folders in the bucket
    response = s3.list_objects_v2(Bucket=bucket_name, Delimiter='/')
    
    # get the folder list
    if 'CommonPrefixes' not in response:
        logger.warning("No folders found")
        return None, None
        
    # get all folder prefixes
    folder = response['CommonPrefixes'][0]['Prefix']
    arxiv_id = folder.split('/')[0]
    
    logger.info(f"Found folder: {folder}")

    # get the files in the folder
    folder_contents = s3.list_objects_v2(
        Bucket=bucket_name,
        Prefix=folder
    )
        
    files_info = []
    if 'Contents' in folder_contents:
        for file in folder_contents['Contents']:
            # skip the folder itself
            if file['Key'] == folder:
                continue
                
            files_info.append({
                'object_key': file['Key'],
                'size': file['Size'],
                })
    
    return arxiv_id, files_info

def get_file_content(object_key, bucket_name):
    s3 = get_client()

    response = s3.get_object(Bucket=bucket_name, Key=object_key)
    return response['Body'].read().decode('utf-8')

def cp_file(object_key, src_bucket_name, dst_bucket_name):
    s3 = get_client()

    s3.copy_object(
        Bucket=dst_bucket_name,
        Key=object_key,
        CopySource=f"{src_bucket_name}/{object_key}"
    )

def delete_folder(bucket_name, folder_name):
    s3 = get_client()
    
    # make sure the folder name ends with '/'
    if not folder_name.endswith('/'):
        folder_name += '/'
    
    try:
        # list all objects in the folder
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=folder_name)
        
        # collect all objects to delete
        objects_to_delete = []
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    objects_to_delete.append({'Key': obj['Key']})
        
        # if there are objects to delete
        if objects_to_delete:
            s3.delete_objects(
                Bucket=bucket_name,
                Delete={'Objects': objects_to_delete}
            )
            logger.info(f"Deleted {len(objects_to_delete)} objects from folder {folder_name}")
        
        # delete the folder itself
        s3.delete_object(Bucket=bucket_name, Key=folder_name)
        logger.info(f"Deleted folder {folder_name}")
        
    except Exception as e:
        logger.error(f"Error deleting folder {folder_name}: {str(e)}", exc_info=True)
        raise
