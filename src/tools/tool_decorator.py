from typing import Callable, Dict
from config.logging import logger
from dataclasses import dataclass
import inspect
import re

@dataclass
class Tool:
    name: str
    description: str
    func: Callable[..., str]
    parameters: Dict[str, Dict[str, str]]
    
    def __call__(self, *args, **kwargs) -> str:
        return self.func(*args, **kwargs)

def parse_docstring(docstring: str) -> Dict[str, str]:
    """
    Parses the docstring to extract a high-level description and parameter descriptions.
    Returns:
        description (str)
        param_docs (Dict[str, str])
    """
    
    description = ""
    params_info = {}
    
    if not docstring:
        return description, params_info
    
    lines = docstring.strip().splitlines()
    
    logger.info(f'Before lines: {lines}')
    
    lines = [line.strip() for line in lines if line.strip()]
    
    logger.info(f'After lines: {lines}')
    
    description_lines = []
    for line in lines:
        if line.lower().startswith(("args:", "parameters:")):
            break
        description_lines.append(line)
    description = " ".join(description_lines)
    
    param_section = "\n".join(lines)
    param_matches = re.findall(r'(\w+)\s*\(([^)]+)\):\s*(.+)', param_section)
    for name, type_, desc in param_matches:
        params_info[name] = desc.strip()
        
    logger.info(f'description: {description}')
    logger.info(f'params_info: {params_info}')
    
    return description, params_info

def tool(name: str = None):
    def decorator(func: Callable[..., str]) -> Callable:
        tool_name = name or func.__name__
        
        signature = inspect.signature(func)
        
        logger.info(f'signature: {signature}')
        
        doc = func.__doc__ or ""
        
        logger.info(f'doc: {doc}')
        
        description, params_info = parse_docstring(doc)
        
        parameters = {}
        for param_name, param in signature.parameters.items():
            logger.info(f'name: {param_name}, param: {param}')
            param_type = str(param.annotation) if param.annotation is not inspect.Parameter.empty else "str"
            parameters[param_name] = {
                "type": param_type.replace("<class '", "").replace("'>", ""),
                "description": params_info.get(param_name, "No description available.")
            }
            
        logger.info(f'parameters: {parameters}')
            
        return Tool(
            name = tool_name,
            description = description,
            func = func,
            parameters = parameters 
        )
        
    return decorator