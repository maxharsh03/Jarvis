from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
import requests
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import json

load_dotenv()

class WebSearchInput(BaseModel):
    query: str = Field(..., description="The search query to look up on the web")
    num_results: int = Field(default=3, description="Number of search results to return (1-10)")

def web_search(query: str, num_results: int = 3) -> str:
    """Search the web for information and return summarized results."""
    try:
        # Try DuckDuckGo first (no API key required)
        search_url = "https://html.duckduckgo.com/html/"
        params = {
            'q': query,
            'b': '',  # start index
            'kl': 'us-en',  # language
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(search_url, params=params, headers=headers, timeout=5)  # Reduced timeout
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            results = []
            
            # Find search result links
            result_links = soup.find_all('a', {'class': 'result__a'})[:num_results]
            
            for i, link in enumerate(result_links):
                title = link.get_text().strip()
                url = link.get('href', '')
                
                # Get snippet from result
                result_div = link.find_parent('div', {'class': 'result'})
                snippet = ""
                if result_div:
                    snippet_div = result_div.find('div', {'class': 'result__snippet'})
                    if snippet_div:
                        snippet = snippet_div.get_text().strip()
                
                if title and url:
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet[:200] + "..." if len(snippet) > 200 else snippet
                    })
            
            if results:
                formatted_results = f"🔍 Web search results for '{query}':\n\n"
                for i, result in enumerate(results, 1):
                    formatted_results += f"{i}. **{result['title']}**\n"
                    if result['snippet']:
                        formatted_results += f"   {result['snippet']}\n"
                    formatted_results += f"   🔗 {result['url']}\n\n"
                
                return formatted_results
            else:
                return f"❌ No search results found for '{query}'"
        
        else:
            # Fallback to a simple search API or return error
            return f"❌ Web search temporarily unavailable. Status code: {response.status_code}"
    
    except requests.RequestException as e:
        return f"❌ Network error during web search: {str(e)}"
    except Exception as e:
        return f"❌ Error performing web search: {str(e)}"

# Alternative search using SerpAPI if available
def serpapi_search(query: str, num_results: int = 3) -> str:
    """Search using SerpAPI (Google Search API) if API key is available."""
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    
    if not serpapi_key:
        return web_search(query, num_results)
    
    try:
        url = "https://serpapi.com/search"
        params = {
            "engine": "google",
            "q": query,
            "api_key": serpapi_key,
            "num": num_results,
            "hl": "en",
            "gl": "us"
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if "organic_results" in data:
            results = data["organic_results"]
            formatted_results = f"🔍 Web search results for '{query}':\n\n"
            
            for i, result in enumerate(results[:num_results], 1):
                title = result.get("title", "No title")
                snippet = result.get("snippet", "No description")
                link = result.get("link", "")
                
                formatted_results += f"{i}. **{title}**\n"
                formatted_results += f"   {snippet}\n"
                formatted_results += f"   🔗 {link}\n\n"
            
            return formatted_results
        else:
            return web_search(query, num_results)
    
    except Exception as e:
        return web_search(query, num_results)

def enhanced_web_search(query: str, num_results: int = 3) -> str:
    """Enhanced web search that tries SerpAPI first, falls back to DuckDuckGo."""
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    
    if serpapi_key:
        return serpapi_search(query, num_results)
    else:
        return web_search(query, num_results)

# Create the Langchain tool
web_search_tool = StructuredTool.from_function(
    name="web_search",
    description="Search the web for current information, news, and general knowledge. Use this for questions about recent events or information not in your training data.",
    func=enhanced_web_search,
    args_schema=WebSearchInput
)