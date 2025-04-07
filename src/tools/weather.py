import httpx
from typing import Optional
from src.config.logging import logger
from src.config.settings import Config
from src.tools.tool_decorator import tool

@tool()
def get_weather(location: str) -> Optional[dict]:
    """
    Gets current weather information for a specific location.
    
    Args:
        location (str): The city name, address, or coordinates to get weather for.
        
    Returns:
        Optional[dict]: Weather data for the specified location.
    """
    
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": location,
            "appid": Config.OPEN_WEATHER_API_KEY,
            "units": "metric"
        }
        
        with httpx.Client(verify = False, timeout = 10) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            weather_data = response.json()
            
            return {
                "location": location,
                "temperature": weather_data["main"]["temp"],
                "description": weather_data["weather"][0]["description"],
                "humidity": weather_data["main"]["humidity"],
                "wind_speed": weather_data["wind"]["speed"],
                "icon": weather_data["weather"][0]["icon"],
                "feels_like": weather_data["main"]["feels_like"],
            }  
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Weather API error: {e}")
        return {
            "error": "Weather API error",
            "message": f"Could not retrieve weather data: {str(e)}",
        }