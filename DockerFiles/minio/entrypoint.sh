#!/bin/bash

set -e
set -o pipefail

ALIAS=myminio

# start minio server
minio server /data/external --console-address ":9001" &
MINIO_PID=$!

# wait minio server to start
until curl -s --fail "$MINIO_ENDPOINT/minio/health/ready" > /dev/null; do
  echo "$(date) Waiting for MinIO server to be ready..."
  sleep 1
done

# config mc client
mc alias set $ALIAS "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY"

# check and create bucket
if ! mc ls $ALIAS/$MINIO_PAPER_DATA_BUCKET > /dev/null 2>&1; then
  echo "Bucket $MINIO_PAPER_DATA_BUCKET does not exist. Creating..."
  mc mb $ALIAS/$MINIO_PAPER_DATA_BUCKET
else
  echo "Bucket $MINIO_PAPER_DATA_BUCKET already exists."
fi

if ! mc ls $ALIAS/$MINIO_PROCESSED_DATA_BUCKET > /dev/null 2>&1; then
  echo "Bucket $MINIO_PROCESSED_DATA_BUCKET does not exist. Creating..."
  mc mb $ALIAS/$MINIO_PROCESSED_DATA_BUCKET
else
  echo "Bucket $MINIO_PROCESSED_DATA_BUCKET already exists."
fi

# run minio server in foreground
wait $MINIO_PID