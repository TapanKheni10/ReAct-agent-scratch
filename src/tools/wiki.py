from config.logging import logger
from typing import Optional
import json
from tools.tool_registery import tool
import wikipedia

@tool()
def wikipedia_search(query: str, lang: Optional[str] = 'en') -> Optional[str]:
    """
    Searches for a query on Wikipedia and retrieves a summary.

    Args:
        query (str): The search query string.
        lang (Optional[str]): The language code for the Wikipedia search (default is 'en').

    Returns:
        Optional[str]: A JSON string containing the query and its summary if successful, or None if an error occurs.
    """
    try:
        logger.info(f"Searching for {query} in {lang} through Wikipedia...")
        wikipedia.set_lang(lang)
        result = {
            'query': query,
            'summary': wikipedia.summary(query)
        }
    
        logger.info(f"Successfully retrieved data from Wikipedia for query: {query}")
        
        return result
    
    except Exception as e:
        logger.error(f'Error: {e}')
        return None
    
if __name__ == '__main__':
    """
    Executes sample Wikipedia searches and writes the results to a JSON file.

    The script searches for predefined queries on Wikipedia, prints the results to the console,
    and saves them to a JSON file if data is found.
    """
    search_queries = ['Virat Kohli', "Cristiano Ronaldo"]
    
    results = []
    for query in search_queries:
        result = wikipedia_search(query)
        
        if result:
            results.append(json.loads(result))
        else:
            print(f'No data found for query: {query}')
            
    with open('../../data/tool_output/wikipedia_search_results.json', 'w') as f:
        f.write(json.dumps(results, indent=2, ensure_ascii=False))