import os
import glob
import json
from tqdm import tqdm
from google import genai

import config

# A value in the prompt to limit the length of summarization, 
# if the original content is alreay shorter than this,
# then we will not summarize it using LLM.
APPROXIMATE_MAX_SUMMARY_WORD = config.SUMMARIZER_MAX_SUMMARY_WORD 
PROJECT_ID = config.SUMMARIZER_GCP_PROJECT_ID
LOCATION = config.SUMMARIZER_GCP_LOCATION
MODEL = config.SUMMARIZER_GCP_MODEL_NAME
RAW_PATH_BASE = config.RAW_DATA_PATH
TARGET_PATH_BASE = config.PROCESSED_DATA_PATH


def generate_summary(client: genai.Client, full_prompt, model):
    """
    Calls the Google GenAI model (Gimini 1.0 Pro) via Vertex AI to generate a text summary.
    
    Args:
        client: An instance of google.genai.Client.
        full_prompt: The combined prompt and content string.
        model: The model identifier, default is "gemini-1.0-pro-002".
        max_length: Maximum number of tokens for the generated summary (currently not used).
        temperature: Controls the randomness of the generated output (currently not used).
        
    Returns:
        The generated summary as a string.
    """
    # Create a new chat session with the specified model
    response = client.models.generate_content(model = model, contents=full_prompt)
    return response.text

def main():
    # find all summarized paths (paths that have metadata.json under TARGET_PATH_BASE), we will skip those
    already_processed_metadata_json_paths = glob.glob(os.path.join(TARGET_PATH_BASE, "**", "metadata.json"), recursive=True)
    already_processed_arxiv_ids = set([already_processed_metadata_json_path.split("/")[-2] for already_processed_metadata_json_path in already_processed_metadata_json_paths])

    # Initialize the google-genai client using Vertex AI
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

    # retrive original xml paths
    xml_paths = glob.glob(os.path.join(RAW_PATH_BASE, "**", "*.xml"), recursive=True)
    xml_paths.sort()

    for xml_path in tqdm(xml_paths, desc="Processing Chunks"):
        base_path, xml_file_name = os.path.split(xml_path)
        arxiv_id = os.path.splitext(xml_file_name)[0]
        if arxiv_id in already_processed_arxiv_ids:
            continue # skip if we already processed it before
        json_path = os.path.join(base_path, arxiv_id + ".json")
        metadata_json_path = os.path.join(base_path, "metadata.json")

        # load metadata
        with open(metadata_json_path, "r") as f:
            metadata = json.loads(f.read())

        # load orinal chunks json
        with open(json_path, "r") as f:
            original_chunks = json.loads(f.read())

        # load summarization prompts
        with open("./prompts.json", "r") as f:
            prompts = json.loads(f.read())
        
        # target folder that stores extracted chunk text and summarization.json and metadata.json
        target_path = os.path.join(TARGET_PATH_BASE, arxiv_id)

        if not os.path.exists(target_path):
            os.makedirs(target_path, exist_ok=True)
        
        target_chunks = []
        target_metadata = metadata

        for original_chunk_index, original_chunk in enumerate(original_chunks):
            original_chunk_title = original_chunk["title"]
            original_chunk_content = original_chunk["content"]
            # paper_title = metadata["title"]
            original_chunk_content = original_chunk_content.strip().replace('\n', '').replace('\r', '') # remove all \n and \r
            # save chunk text file
            chunk_file_name = f"chunk_{original_chunk_index + 1}.txt"
            chunk_path = os.path.join(target_path, chunk_file_name)
            with open(chunk_path, "w") as f:
                f.write(original_chunk_content)
            
            # summarization current chunk using different prompts
            current_chunk_summaries = []
            for prompot_key, prompt_val in prompts.items():
                summarized_chunk_content = original_chunk_content
                # if original chunk is longer than threshold, we need to summarize it
                if len(summarized_chunk_content.split(" ")) > APPROXIMATE_MAX_SUMMARY_WORD:
                    full_prompt = prompt_val.format(max_words = APPROXIMATE_MAX_SUMMARY_WORD, title = original_chunk_title, content=original_chunk_content)
                    summarized_chunk_content = generate_summary(client, full_prompt, MODEL)
                summarized_chunk_content = summarized_chunk_content.strip().replace("\n", "").replace("\r", "") # remove blanks
                current_chunk_summaries.append({
                    "prompt": prompot_key,
                    "content": summarized_chunk_content
                })
            
            # add different prompt summarizations to target_chunks
            target_chunks.append({
                "chunk_file": chunk_file_name,
                "summaries": current_chunk_summaries
            })

        # wrap-up and write stuff to summarization.json
        target_json_path = os.path.join(target_path, "summarization.json")
        with open(target_json_path, "w") as f:
            f.write(json.dumps(target_chunks, indent=4))


        # write metadata to processed data folder, if summary is too long, we need to summarize it using LLM
        if len(target_metadata["summary"].split(" ")) > APPROXIMATE_MAX_SUMMARY_WORD:
            full_prompt = prompts[0].format(max_words = APPROXIMATE_MAX_SUMMARY_WORD, title = "Summary", content=target_metadata["summary"])
            target_metadata["summary"] = generate_summary(client, full_prompt, MODEL)
        target_metadata["summary"] = target_metadata["summary"].strip().replace("\n", "").replace("\r", "") # remove blanks
        
        target_metadata_path = os.path.join(target_path, "metadata.json")
        with open(target_metadata_path, "w") as f:
            f.write(json.dumps(target_metadata, indent=4))

        tqdm.write("Finished: " + target_path)


if __name__ == "__main__":
    main()
            


    
        
