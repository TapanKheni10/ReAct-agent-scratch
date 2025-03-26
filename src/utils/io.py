from typing import Dict, Optional, Any
from src.config.logging import logger


def read_file(path: str) -> Optional[str]:
    """
    Reads the content of a markdown file and returns it as a text object.

    Args:
        path (str): The path to the markdown file.

    Returns:
        Optional[str]: The content of the file as a string, or None if the file could not be read.
    """
    try:
        with open(path, 'r', encoding='utf-8') as file:
            content: str = file.read()
        return content
    except FileNotFoundError:
        logger.info(f"File not found: {path}")
        return None
    except Exception as e:
        logger.info(f"Error reading file: {e}")
        return None
    
    
def write_to_file(path: str, content: str) -> None:
    """
    Writes content to a specified file. Appends to the file if it already exists.

    Args:
        path (str): The path to the file.
        content (str): The content to write to the file.

    Raises:
        Exception: For any other exceptions encountered during file writing.
    """
    try:
        with open(path, 'a', encoding='utf-8') as file:
            file.write(content)
        logger.info(f"Content written to file: {path}")
    except FileNotFoundError:
        logger.error(f"File not found: {path}")
        raise
    except Exception as e:
        logger.error(f"Error writing to file '{path}': {e}")
        raise

