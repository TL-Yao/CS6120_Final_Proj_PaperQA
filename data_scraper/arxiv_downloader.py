import os
import json
import re
import time
import arxiv
from tqdm import tqdm

import config

# ----- CONFIGURATION -----
# Search query for papers in Computer Science with cross-listed categories cs.LG and cs.AI.
QUERY = config.ARXIV_QUERY
MAX_RESULTS = config.ARXIV_MAXIMUM_PAPER_LIMIT

# sort by submission date in descending order
SORT_BY = arxiv.SortCriterion.SubmittedDate
SORT_ORDER = arxiv.SortOrder.Descending

# Sleep durations (in seconds)
FETCH_SLEEP = config.ARXIV_FETCH_DELAY_TIME_IN_SECONDS   # Fetch metadata sleep time
DOWNLOAD_SLEEP = config.ARXIV_PDF_DOWNLOAD_DELAY_TIME_IN_SECONDS # Download sleep time

BASE_PATH = config.RAW_DATA_PATH


def extract_arxiv_id(id_url: str) -> str:
    """
    Extract the arXiv ID from the entry ID URL.
    Example: from "http://arxiv.org/abs/2001.00123v1" returns "2001.00123".
    """
    match = re.search(r"abs/([^v]+)", id_url)
    if match:
        return match.group(1)
    return id_url

def process_result(result: arxiv.Result) -> None:
    """
    Process a single arXiv result:
      - Check if the paper's published date is within the specified range.
      - Verify that a PDF URL is provided.
      - Download the PDF to a folder structured as "year/month" if the download succeeds.
      - Update metadata.json in the same folder.
    """
    if not result.pdf_url:
        print("No PDF URL found for this paper. Skipping...")
        return

    # Extract the arXiv id (e.g., "2001.00123") from the entry id
    arxiv_id = extract_arxiv_id(result.entry_id)

    # Determine folder based on published date (format: "YYYY/MM")
    published_date = result.published
    folder = os.path.join(BASE_PATH, arxiv_id)

    # Prepare filename for the PDF
    pdf_filename = f"{arxiv_id}.pdf"
    
    try:
        # Create folder if it does not exist
        os.makedirs(folder, exist_ok=True)
        # Sleep to prevent overloading the server before downloading each PDF
        time.sleep(DOWNLOAD_SLEEP)
        # Use the arxiv library's built-in method to download the PDF
        result.download_pdf(dirpath=folder, filename=pdf_filename)

        # Construct metadata for the paper
        paper_metadata = {
            "arxiv_id": arxiv_id,
            "title": result.title,
            "published": published_date.isoformat(),
            "updated": result.updated.isoformat(),
            "authors": [author.name for author in result.authors],
            "summary": result.summary,
            "pdf_url": result.pdf_url
        }
        # write metadata.json
        with open(os.path.join(folder, "metadata.json"), "w") as f:
            f.write(json.dumps(paper_metadata, indent=2))

        print(f"Successfully downloaded PDF: {os.path.join(folder, pdf_filename)}")
    except Exception as e:
        print(f"Failed to download PDF for {arxiv_id}: {e}")
        # Optional: Remove folder if created and empty
        if os.path.exists(folder) and not os.listdir(folder):
            os.rmdir(folder)
        return


def get_all_results(query: str, max_results: int = MAX_RESULTS) -> list:
    """
    Retrieve all results (paginated) for the given query.
    
    This function iterates through pages until no more results are returned.
    A sleep delay is added after each batch fetch to prevent being blocked.
    """
    try:
        client = arxiv.Client(page_size=200, delay_seconds=FETCH_SLEEP, num_retries=10)
        all_results = []
        search = arxiv.Search(
            query=query,
            sort_by=SORT_BY,
            sort_order=SORT_ORDER,
            max_results=max_results,
        )
        client_results = list(client.results(search))
        all_results.extend(client_results)
    except Exception as e:
        print(f"Error happens while fetching metadata: {e}")
    
    print(f"Fetched Total results is: {len(all_results)}")
    return all_results


def main():
    print("Starting arXiv query and download process...")
    # Retrieve all results using pagination
    all_results = get_all_results(QUERY)
    print(f"Total results retrieved: {len(all_results)}")

    # Process each result using tpdm for a progress bar
    for result in tqdm(all_results, desc="Downloading papers"):
        try:
            process_result(result)
        except Exception as e:
            print(f"Error downloading: {e}")
            continue
    
    print("Process completed.")

if __name__ == "__main__":
    main()
