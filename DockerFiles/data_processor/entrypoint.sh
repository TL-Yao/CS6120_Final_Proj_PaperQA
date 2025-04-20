#!/bin/bash

# call http://localhost:9091/healthz check if milvus is ready
while ! curl -s --fail http://milvus:9091/healthz; do
  echo "Waiting for Milvus to be ready..."
  sleep 1
done

# create collections
python ./data_processor/milvus_schemas/0001_init_tables.py

# start data processor service
python data_processor/app.py
