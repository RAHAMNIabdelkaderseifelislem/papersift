import os
import json
import requests
import arxiv
import ollama
import re
from datetime import datetime, timedelta
import urllib.request
import unicodedata

class ResearchPaperDownloader:
    def __init__(self, project_title, download_path='arxiv_research', relevance_threshold=85):
        """
        Initialize the downloader with project details and setup directories
        
        :param project_title: Title of the research project
        :param download_path: Base path for downloading papers
        :param relevance_threshold: Minimum relevance score to download a paper
        """
        self.project_title = project_title
        self.download_path = download_path
        self.relevance_threshold = relevance_threshold
        
        # Create necessary directories
        self.pdfs_dir = os.path.join(download_path, 'pdfs')
        self.metadata_dir = os.path.join(download_path, 'metadata')
        os.makedirs(self.pdfs_dir, exist_ok=True)
        os.makedirs(self.metadata_dir, exist_ok=True)

    @staticmethod
    def sanitize_filename(title):
        """
        Sanitize the title to create a clean filename
        
        :param title: Original paper title
        :return: Sanitized filename
        """
        # Remove accents
        title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('utf-8')
        
        # Replace non-alphanumeric characters (including spaces) with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9]+', '_', title)
        
        # Remove leading/trailing underscores and convert to lowercase
        sanitized = sanitized.strip('_').lower()
        
        return sanitized

    def generate_search_keywords(self):
        """
        Use LLM to generate search keywords for arXiv
        
        :return: List of keywords
        """
        prompt = f"""
        Generate 5-7 specific, academic search keywords for research papers related to '{self.project_title}'.
        These keywords should be technical and precise. Provide only the keywords, separated by commas.
        """
        
        response = ollama.chat(model='Hermes-3:latest', messages=[
            {'role': 'user', 'content': prompt}
        ])
        
        keywords = response['message']['content'].strip().split(',')
        return [k.strip() for k in keywords]

    def assess_paper_relevance(self, paper):
        """
        Use LLM to assess the relevance of a paper's abstract
        
        :param paper: arxiv paper object
        :return: Tuple of (is_relevant, relevance_details)
        """
        prompt = f"""
        Assess the relevance of the following research paper abstract to the research project: '{self.project_title}'
        
        Paper Abstract: {paper.summary}
        
        Provide a JSON response with these fields:
        - relevance_score: Integer from 0-100
        - is_relevant: Boolean
        - key_strengths: List of reasons for relevance
        - potential_limitations: List of potential weaknesses
        - impact_category: One of [TRANSFORMATIVE, SIGNIFICANT, MODERATE, MINIMAL]
        - recommendation: One of [HIGH PRIORITY, CONSIDER, LOW PRIORITY, SKIP]
        """
        
        try:
            response = ollama.chat(model='Hermes-3:latest', messages=[
                {'role': 'user', 'content': prompt}
            ])
            
            # Parse the response, handling potential JSON parsing issues
            relevance_info = json.loads(response['message']['content'])
            
            # Check if relevance score meets the threshold
            is_relevant = (relevance_info.get('relevance_score', 0) > self.relevance_threshold)
            relevance_info['is_relevant'] = is_relevant
            
            return is_relevant, relevance_info
        except Exception as e:
            print(f"Error in relevance assessment: {e}")
            return False, {}

    def download_paper(self, paper, relevance_details):
        """
        Download the paper PDF and create metadata
        
        :param paper: arxiv paper object
        :param relevance_details: Detailed relevance assessment
        :return: Path to downloaded PDF or None
        """
        # Sanitize filename
        sanitized_title = self.sanitize_filename(paper.title)
        
        # Create filename in format: title-year.pdf
        pdf_filename = f"{relevance_details.get('relevance_score', 0)}-{paper.published.year}-{sanitized_title}.pdf"
        pdf_path = os.path.join(self.pdfs_dir, pdf_filename)
        
        # Download PDF
        try:
            urllib.request.urlretrieve(paper.pdf_url, pdf_path)
        except Exception as e:
            print(f"Error downloading PDF: {e}")
            return None
        
        # Create metadata
        metadata = {
            "title": paper.title,
            "authors": [author.name for author in paper.authors],
            "published_date": paper.published.strftime("%Y-%m-%d"),
            "year": paper.published.year,
            "abstract": paper.summary,
            "url": paper.entry_id,
            "arxiv_id": paper.get_short_id(),
            "categories": paper.categories,
            "local_pdf_path": pdf_path,
            "pdf_filename": pdf_filename,
            "detailed_relevance_assessment": relevance_details
        }
        
        # Save metadata with unique name
        metadata_filename = f"{relevance_details.get('relevance_score', 0)}-{paper.published.year}-{sanitized_title}_metadata.json"
        metadata_path = os.path.join(self.metadata_dir, metadata_filename)
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)
        
        return pdf_path

    def search_and_download(self, max_results=250):
        """
        Search arXiv for relevant papers and download them
        
        :param max_results: Maximum number of papers to process
        """
        # Generate search keywords
        keywords = self.generate_search_keywords()
        
        # Construct search query
        search_query = ' OR '.join(keywords)

        # Calculate the date 5 years ago
        five_years_ago = datetime.now() - timedelta(days=60)
        
        # Perform arXiv search
        search = arxiv.Search(
            query=f"({search_query}) AND submittedDate:[{five_years_ago.strftime('%Y%m%d')}000000 TO 999912312359]",
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        # Track downloaded papers
        downloaded_papers = []
        
        # Process search results
        for paper in search.results():
            # Assess relevance
            is_relevant, relevance_details = self.assess_paper_relevance(paper)
            
            if is_relevant and relevance_details.get('relevance_score', 0) > self.relevance_threshold:
                print(f"Highly Relevant Paper Found (Score: {relevance_details.get('relevance_score', 0)}): {paper.title}")
                
                # Download paper and create metadata
                pdf_path = self.download_paper(paper, relevance_details)
                
                if pdf_path:
                    downloaded_papers.append({
                        "paper": paper,
                        "relevance_details": relevance_details
                    })
        
        print(f"Downloaded {len(downloaded_papers)} highly relevant papers (Score > {self.relevance_threshold})")
        return downloaded_papers

def main(project_title, relevance_threshold=85):
    """
    Main function to run the research paper downloader
    
    :param project_title: Title of the research project
    :param relevance_threshold: Minimum relevance score to download a paper
    """
    downloader = ResearchPaperDownloader(project_title, relevance_threshold=relevance_threshold)
    downloader.search_and_download()

if __name__ == "__main__":
    # Example usage
    project_title = "Generative AI Method for Autonomous Agents and Self-Improvement Behavior"
    main(project_title, relevance_threshold=80)