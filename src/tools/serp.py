from config.logging import logger
from typing import Tuple, Union, Dict, List, Any
from config.settings import Config
import httpx
import json
from tools.tool_decorator import tool
from bs4 import BeautifulSoup
from model.groq import generate

class SerpAPIClient:
    """
    A client for interacting with the SerpAPI service to perform search queries.

    Attributes:
        api_key (str): The API key for authenticating with the SerpAPI service.
        base_url (str): The base URL for the SerpAPI service.
    """
    
    def __init__(self):
        """
        Initializes the SerpAPIClient with the API key and base URL.
        """
        self.api_key = Config.SERP_API_KEY
        self.base_url = 'https://serpapi.com/search'
        
    def __call__(self, query: str, engine: str = "google", location: str = "") -> Union[Dict[str, Any], Tuple[int, str]]:
        """
        Executes a search query using the SerpAPI service.

        Args:
            query (str): The search query string.
            engine (str): The search engine to use (default is "google").
            location (str): The location for the search query (optional).

        Returns:
            Union[Dict[str, Any], Tuple[int, str]]: A dictionary containing the search results if successful,
            or a tuple with the HTTP status code and error message if the request fails.
        """
        params = {
            "engine": engine,
            "q": query,
            "api_key": self.api_key,
            "location": location
        }
        
        try:
            with httpx.Client(timeout = 20.0) as client:
                response = client.get(self.base_url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error: {e}")
            return e.response.status_code, e.response.text

def format_top_search_results(results: Dict[str, Any], top_n: int = 10) -> List[Dict[str, Any]]:
    """
    Formats the top search results from the SerpAPI response.

    Args:
        results (Dict[str, Any]): The raw search results from the SerpAPI response.
        top_n (int): The number of top results to format (default is 10).

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing the formatted search results.
    """
    return [
        {
            "position": result.get('position'),
            "title": result.get('title'),
            "link": result.get('link'),
            "snippet": result.get('snippet')
        }
        for result in results.get('organic_results', [])[:top_n]
    ] 
    
def web_scrape(url: str) -> str:
    """
    Scrapes the content from a given URL.

    Args:
        url (str): The URL to scrape.

    Returns:
        str: The scraped text content.
    """
    try:
        with httpx.Client(timeout=1000.0, verify = False) as client:
            response = client.get(url)
            response.raise_for_status()
            html_content = response.text
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
            
            # Get text
            text = soup.get_text()
            
            # Break into lines and remove leading and trailing space on each
            lines = (line.strip() for line in text.splitlines())
            
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            
            # Remove blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text[:5000]
    
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return ""

@tool()
def google_search(search_query: str, location: str = "") -> str:
    """
    Performs a search query using the SerpAPIClient and formats the results.

    Args:
        - search_query (str): The search query string.
        - location (str): The location for the search query (optional).

    Returns:
        str: A JSON string containing the formatted search results or an error message.
    """
    serp_client = SerpAPIClient()
    
    results = serp_client(query=search_query, location=location)
    
    if isinstance(results, Dict):
        top_results = format_top_search_results(results=results)
        
        enriched_results = []
        for result in top_results[:2]:
            try:
                scraped_content = web_scrape(result['link'])
                
                summary_prompt = f"""
                Summarize the following web content in a concise and informative way.
                Focus on extracting key facts, insights, and main points.
                
                Content from: {result['title']}
                {scraped_content}
                """
                
                summary = generate(
                    system_prompt="You are a helpful assistant that summarizes web content accurately and concisely.",
                    content=summary_prompt
                )
                
                enriched_result = {
                    "position": result.get('position'),
                    "title": result.get('title'),
                    "link": result.get('link'),
                    "snippet": result.get('snippet'),
                    "summary": summary
                }
                enriched_results.append(enriched_result)
                
            except Exception as e:
                logger.error(f"Error processing result {result['link']}: {e}")
                # Still include the result without summary if there's an error
                enriched_results.append(result)
                
        response = {
            "top_results": top_results,
            "enriched_results": enriched_results
        }
            
        return response
    else:
        status_code, error_message = results
        error_json = json.dumps({"error": f"Search failed with status code {status_code}: {error_message}"})
        logger.error(error_json)
        return error_json, {}
    
    
if __name__ == "__main__":
    """
    Executes a sample search query and writes the results to a JSON file if successful.
    """
    search_query = "what happend to donald trump recently?"
    serper_search_results = google_search(search_query, '')
    print(serper_search_results)
    print('='*50)
    print(type(serper_search_results))
    
    if "error" not in serper_search_results:
        with open("../../data/tool_output/serp_search_results.json", "w") as f:
            f.write(serper_search_results)
