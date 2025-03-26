from ..config.logging import logger
from typing import Tuple, Union, Dict, List, Any
from ..config.settings import Config
import httpx
import json

class SerpAPIClient:
    
    def __init__(self):
        self.api_key = Config.SERP_API_KEY
        self.base_url = 'https://serpapi.com/search'
        
    def __call__(self, query: str, engine: str = "google", location: str = "") -> Union[Dict[str, Any], Tuple[int, str]]:
        
        params = {
            "engine": engine,
            "q": query,
            "api_key": self.api_key,
            "location": location
        }
        
        try:
            with httpx.Client() as client:
                response = client.get(self.base_url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error: {e}")
            return e.response.status_code, e.response.text

def format_top_search_results(self, results: Dict[str, Any], top_n: int = 10) -> List[Dict[str, Any]]:
    return [
    {
        "position": result.get('position'),
        "title": result.get('title'),
        "link": result.get('link'),
        "snippet": result.get('snippet')
    }
    for result in results.get('organic_results', [])[:top_n]
]
        
def search(self, search_query: str, location: str = "") -> str:
    
    serp_client = SerpAPIClient()
    
    results = serp_client(query = search_query, location = location)
    
    if isinstance(results, Dict):
        top_results = format_top_search_results(results = results)
        return json.dumps({"top_results" : top_results}, indent = 4)
    else:
        status_code, error_message = results
        error_json = json.dumps({"error": f"Search failed with status code {status_code}: {error_message}"})
        logger.error(error_json)
        return error_json
    
if __name__ == "__main__":
    search_query = "Best punjabi cuisine in surat."
    result_json = search(search_query, '')
    print(result_json)
        