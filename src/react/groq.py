from groq import Groq
from src import logger

def safety_check(model: Groq, content: str):

    try:
        completion = model.chat.completions.create(
            model = "llama-guard-3-8b",
            messages = [
                {
                    "role": "user",
                    "content": content,
                },
            ],
            temperature = 1,
            max_completion_tokens = 1024,
            top_p = 1,
            stream = False,
            stop = None,
        )

        return completion.choices[0].message
    
    except Exception as e:
        logger.error(f"An error occurred while checking the safety of the content.")
        raise e
    
def generate(model: Groq, content: str):
    
    result = safety_check(model = model, content = content)
    if result.split("\n")[0] == 'unsafe':
        return "the answer contains harmful content."
    
    try:
        completion = model.chat.completions.create(
            model = 'gemma2-9b-it',
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful LLM model which is used in a ReAct agent.",
                },
                {
                    "role": "user",
                    "content": content,
                }
            ],
            temperature=1,
            max_completion_tokens=1024,
            top_p=1,
            stream=False,
            stop=None,
        )
        
        if not completion.choices[0].message:
            logger.info('Empty response recieved from the model.')
            return None
        
        logger.info("Response generated successfully.")
        return completion.choices[0].message
        
    except Exception as e:
        logger.error(f"An error occurred while generating the response.")
        raise e