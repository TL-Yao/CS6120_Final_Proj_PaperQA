# Paper Scraping, Chunking, and Summarizing

This module provides a pipeline to **download academic papers from arXiv**, **extract and process PDF content**, **split the content into manageable logic-based chunks using Grobid**, and **generate concise summaries using LLMs** (such as Gemini).

## Processed Dataset

Below is a sample dataset that we scraped from arXiv and processed using this pipeline. It contains papers related to computer science and machine learning published between November 2024 and April 2025.

[Download the dataset](https://drive.google.com/file/d/1ZOOySvXF4yVDVrB6C6Rj5GbNcxNOeKKV/view?usp=sharing)

## Features

- **Scraping**: Automatically fetches both metadata and full-text PDFs from arXiv using search queries.
- **Chunking**: Intelligently splits content into logical segments based on [GROBID](https://github.com/kermitt2/grobid)'s Text Encoding Initiative (TEI) output.
- **Summarizing**: Uses large language models to summarize segments that exceed a specified length threshold.

## Requirements

- Install all dependencies listed in `requirements.txt`.
- To run `summarizer.py` (which uses Gemini via `google.genai`), proper setup for the Gemini API is required. Refer to the [official setup guide](https://googleapis.github.io/python-genai/).
- Update `config.py` with appropriate values for file paths, model configuration, and thresholds before running the pipeline.

## Usage

1. **Download papers from arXiv**  
   Run:
   ```bash
   python arxiv_downloader.py
   ```
   This script downloads the metadata and PDF files according to your configuration and saves them to `RAW_DATA_PATH`.

2. **Process and chunk the PDF content**  
   Run:
   ```bash
   python pdf_processor.py
   ```
   This script sends each PDF to a public GROBID API, saves the returned TEI XML, and extracts and chunks the main content into a JSON file in `RAW_DATA_PATH`.

3. **Reorganizing and summarize long chunks**  
   Run:
   ```bash
   python summarizer.py
   ```
   This script reads from `RAW_DATA_PATH`, summarizes any chunk or abstract longer than `SUMMARIZER_MAX_SUMMARY_WORD` using LLM, based on prompts from `prompts.json`, and saves the final processed results into `PROCESSED_DATA_PATH`.

4. **Clean up raw data**
   Once all steps complete without errors, `RAW_DATA_PATH` can be safely deleted.


## Output Structure
Raw files: stored under `RAW_DATA_PATH`

Processed summaries: stored under   `PROCESSED_DATA_PATH`