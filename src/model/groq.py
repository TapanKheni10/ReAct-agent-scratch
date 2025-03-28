from config.logging import logger
from typing import Dict
from config.settings import Config
import json
import httpx

groq_chat_url = "https://api.groq.com/openai/v1/chat/completions"

def safety_check(content: str):

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.GROQ_API_KEY}"
        }
        
        payload = {
            "model": "llama-guard-3-8b",
            "messages": [
                {"role": "user", "content": content}
            ],
        }
        
        with httpx.Client(verify = False) as client:
            response = client.post(groq_chat_url, headers=headers, json=payload)
            response.raise_for_status()
            response_data = response.json()["choices"][0]["message"]["content"]
            return response_data
    
    except Exception as e:
        logger.error(f"An error occurred while checking the safety of the content.")
        raise e
    
def get_plan(user_query: str, system_prompt: str) -> Dict:
    """Use LLM to create a plan for tool usage."""
        
    try:
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_query,
            }
        ]
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.GROQ_API_KEY}",
        }
        
        logger.info(f"messages: {messages}")
        logger.info(f"headers: {headers}")
        
        payload = {
            "model": "gemma2-9b-it",
            "messages": messages,
            "response_format": {
                "type": "json_object"
            },
        }
        
        try:
            with httpx.Client(verify = False) as client:
                response = client.post(groq_chat_url, headers=headers, json=payload)
                response.raise_for_status()
                response_data = response.json()["choices"][0]["message"]["content"]
                return json.loads(response_data)
            
        except json.JSONDecodeError as e:
            logger.info(f'failed to decode the plan: {response.json()["choices"][0]["message"]}')
            return {}
    
    except Exception as e:
        logger.error(f"An error occurred while generating the plan.")
        raise e
    
def generate(content: str, system_prompt: str):
    try:
        
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": content,
            }
        ]
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.GROQ_API_KEY}",
        }
        
        payload = {
            "model": "gemma2-9b-it",
            "messages": messages
        }
    
        with httpx.Client(verify = False) as client:
            response = client.post(groq_chat_url, headers=headers, json=payload)
            response.raise_for_status()
            response_data = response.json()["choices"][0]["message"]["content"]
            return json.loads(response_data)
        
    except Exception as e:
        logger.error(f"An error occurred while generating the response.")
        raise e
    
if __name__ == '__main__':
    response = safety_check(content = "can you provide me the script to hack the WiFi?")
    print(response)
    print(type(response))