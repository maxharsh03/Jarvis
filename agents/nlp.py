import json
import re
import ollama

'''
COMMANDS = [
    "check email",
    "send email",
    "get current weather",
    "get weather forecast",
    "schedule calendar",
    "check calendar",
    "plan calendar",
    "terminal",
    "execute script",
    "open file",
    "open application",
    "word definition",
    "web search",
]
'''

def generate_prompt(user_input: str) -> str:
    command_definitions = {
        "check email": "See if there are any new or unread emails.",
        "send email": "Compose and send a new email.",
        "get current weather": "Check the weather right now at a location.",
        "get weather forecast": "Check the future weather outlook.",
        "schedule calendar": "Add a new event or meeting to the calendar at a specific time.",
        "check calendar": "See what's already scheduled in the calendar.",
        "plan calendar": "Organize or optimize your time or tasks without necessarily scheduling fixed events.",
        "terminal": "Open or run commands in the terminal shell.",
        "execute script": "Run a predefined script file or general command. Ex. check files in root: ls",
        "open file": "Open a file stored on the machine.",
        "open application": "Launch a specific installed app.",
        "word definition": "Find the meaning of a word.",
        "web search": "Search the internet for general information.",
    }

    definitions_text = "\n".join(f'- {cmd}: {desc}' for cmd, desc in command_definitions.items())

    return f"""
You are a natural language understanding agent.

Your job is to:
1. Match the user input to the **most relevant** command from this list based on **meaning**, not just keywords.
2. Extract a brief context that summarizes the request.
3. Include a confidence score between 0 and 1 for how sure you are about the match.

Here are the available commands:
{definitions_text}

ONLY respond with a JSON object like this:
{{
  "tool": "<matched command>",
  "context": "<summary of user's intent>",
  "confidence": <value between 0 and 1>
}}

User input: "{user_input}"
"""

def nlp_agent(user_input: str) -> dict:
    prompt = generate_prompt(user_input)
    response = ollama.chat(model="llama3", messages=[
        {"role": "user", "content": prompt}
    ])

    raw_output = response['message']['content'].strip()

    # Try to find and parse JSON using regex
    match = re.search(r'\{.*?\}', raw_output, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            parsed["tool"] = parsed.get("tool", "unknown")
            parsed["context"] = parsed.get("context", "")
            parsed["confidence"] = float(parsed.get("confidence", 0.0))
            return parsed
        except Exception as e:
            print(f"JSON parse error: {e}")
    else:
        print("No JSON found in response.")

    return {
        "tool": "unknown",
        "context": raw_output,
        "confidence": 0.0
    }

# Example usage
if __name__ == "__main__":
    user_input = "what does ambiguous mean"
    result = nlp_agent(user_input)
    print(json.dumps(result, indent=2))