from langchain.tools import StructuredTool
from pydantic import BaseModel
import os
import requests
from dotenv import load_dotenv

load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")


# 1. Schema for current weather
class WeatherInput(BaseModel):
    city: str


# 2. Function to get current weather
def get_current_weather(city: str) -> str:
    """Returns the current weather in the specified city using WeatherAPI."""
    try:
        if not WEATHER_API_KEY:
            return "Weather API key not found. Please set WEATHER_API_KEY in your environment."

        base_url = "http://api.weatherapi.com/v1/current.json"
        params = {"key": WEATHER_API_KEY, "q": city, "aqi": "no"}

        response = requests.get(base_url, params=params)
        data = response.json()

        if response.status_code != 200 or "error" in data:
            return f"Could not retrieve weather for {city}. Error: {data.get('error', {}).get('message', 'Unknown error')}"

        location = data["location"]
        current = data["current"]

        condition = current["condition"]["text"]
        temp_c = current["temp_c"]
        feels_like_c = current["feelslike_c"]
        city_name = location["name"]
        country = location["country"]

        return (
            f"The current weather in {city_name}, {country} is {condition} "
            f"with a temperature of {temp_c}°C (feels like {feels_like_c}°C)."
        )

    except Exception as e:
        return f"Error retrieving weather data: {e}"


# 3. StructuredTool for Langchain agent
get_current_weather_tool = StructuredTool.from_function(
    name="get_current_weather",
    description="Get current weather conditions for any city or location. Use for weather queries, temperature, precipitation, conditions. Required parameter: city (string).",
    func=get_current_weather,
    args_schema=WeatherInput
)


# Placeholder for future forecast tool
class ForecastInput(BaseModel):
    city: str
    days: int


def get_forecast_weather(city: str, days: int) -> str:
    return "Forecast tool not implemented yet."


get_forecast_weather_tool = StructuredTool.from_function(
    name="get_forecast_weather",
    description="Get the weather forecast for a city for a number of days (1–7).",
    func=get_forecast_weather,
    args_schema=ForecastInput
)
