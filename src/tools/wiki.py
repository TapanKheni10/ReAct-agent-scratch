from src import logger
from typing import Optional
import json
import wikipedia

def search(query: str, lang: Optional[str] = 'en') -> Optional[str]:
    try:
        logger.info(f"Searching for {query} in {lang} through Wikipedia...")
        wikipedia.set_lang(lang)
        result = {
            'query': query,
            'summary': wikipedia.summary(query)
        }
        
        logger.info(f"Successfully retrieved data from Wikipedia for query: {query}")
        return json.dumps(result, indent = 4, ensure_ascii = False)
    
    except Exception as e:
        logger.error(f'Error: {e}')
        return None
    
if __name__ == '__main__':
    search_queries = ['Virat Kohli', 'Cristiano Ronaldo']
    
    results = []
    for query in search_queries:
        result = search(query)
        
        if result:
            results.append(result)
            print(result)
        else:
            print(f'No data found for query: {query}')
            
    with open('../../data/tool_output/wikipedia_search_results.json', 'w') as f:
        f.write(json.dumps(results, indent = 4, ensure_ascii = False))