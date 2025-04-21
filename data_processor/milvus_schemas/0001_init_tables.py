from pymilvus import (
    connections,
    utility,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
)
import os
def check_schema_consistency(collection_name, expected_schema):
    """Check if the schema of the collection is consistent with the expected schema"""
    if not utility.has_collection(collection_name):
        return False
    
    collection = Collection(collection_name)
    current_schema = collection.schema
    
    # check if the number of fields is consistent
    if len(current_schema.fields) != len(expected_schema.fields):
        return False
    
    # check if the properties of each field are consistent
    for current_field, expected_field in zip(current_schema.fields, expected_schema.fields):
        if (current_field.name != expected_field.name or
            current_field.dtype != expected_field.dtype or
            current_field.is_primary != expected_field.is_primary or
            current_field.auto_id != expected_field.auto_id):
            return False
    
    return True

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

def init_milvus_collections():
    connections.connect("default", host=os.getenv("MILVUS_HOST"), port=os.getenv("MILVUS_PORT"))
    
    # define paper_metadata schema
    paper_metadata_fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="arxiv_id", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=500),
        FieldSchema(name="published", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="updated", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="authors", dtype=DataType.ARRAY, element_type=DataType.VARCHAR, max_capacity=500, max_length=100),
        FieldSchema(name="pdf_url", dtype=DataType.VARCHAR, max_length=200),
        FieldSchema(name="paper_summary_emb", dtype=DataType.FLOAT_VECTOR, dim=768),
    ]
    paper_metadata_schema = CollectionSchema(fields=paper_metadata_fields, description="store paper metadata")
    
    # define chunk_summaries schema
    chunk_summaries_fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="prompt", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=5000),
        FieldSchema(name="chunk_file", dtype=DataType.VARCHAR, max_length=200),
        FieldSchema(name="paper_id", dtype=DataType.INT64),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),
    ]
    chunk_summaries_schema = CollectionSchema(fields=chunk_summaries_fields, description="store paper chunk summaries and embeddings")
    
    # check and process paper_metadata collection
    if not check_schema_consistency("paper_metadata", paper_metadata_schema):
        if utility.has_collection("paper_metadata"):
            utility.drop_collection("paper_metadata")
        paper_metadata = Collection("paper_metadata", paper_metadata_schema)
        
        # create scalar indexes for paper_metadata
        create_scalar_index(paper_metadata, "arxiv_id")
        create_scalar_index(paper_metadata, "title")
        create_scalar_index(paper_metadata, "authors")
        create_scalar_index(paper_metadata, "published")
        create_scalar_index(paper_metadata, "updated")
        
        # create vector index for title_embedding
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
        paper_metadata.create_index(field_name="paper_summary_emb", index_params=index_params)
        print("paper_metadata collection has been recreated with indexes")
    
    # check and process chunk_summaries collection
    if not check_schema_consistency("chunk_summaries", chunk_summaries_schema):
        if utility.has_collection("chunk_summaries"):
            utility.drop_collection("chunk_summaries")
        chunk_summaries = Collection("chunk_summaries", chunk_summaries_schema)
        
        # create scalar indexes for chunk_summaries
        create_scalar_index(chunk_summaries, "paper_id")
        create_scalar_index(chunk_summaries, "prompt")
        create_scalar_index(chunk_summaries, "content")
        create_scalar_index(chunk_summaries, "chunk_file")
        
        # create vector index for chunk_summaries
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
        chunk_summaries.create_index(field_name="embedding", index_params=index_params)
        print("chunk_summaries collection has been recreated with indexes")
    
    print("Collections check completed!")
    connections.disconnect("default")

if __name__ == "__main__":
    init_milvus_collections()
