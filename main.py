import os
import logging
import time
import traceback
import uuid
from dotenv import load_dotenv

from voice.stt import SpeechToText
from voice.tts import TextToSpeech
from tools.weather import get_current_weather_tool
from tools.terminal import run_terminal_command_tool
from tools.app_launcher import app_launcher_tool
from tools.email import email_tool
from tools.calendar import calendar_tool
from tools.gmail_oauth import gmail_oauth_tool
from tools.calendar_oauth import calendar_oauth_tool
from tools.web_search import web_search_tool
from tools.memory import smart_lookup_tool, recent_context_tool

from langchain_ollama import ChatOllama
from db.memory import memory_system

load_dotenv()

# Core configuration
MIC_INDEX = 0
TRIGGER_WORD = "jarvis"
CONVERSATION_TIMEOUT = 30

logging.basicConfig(level=logging.DEBUG)

# Voice interface setup
stt = SpeechToText(mic_index=MIC_INDEX)
tts = TextToSpeech()

# Language model
llm = ChatOllama(model="qwen:latest")

# Tool registry for direct execution
TOOL_REGISTRY = {
    "get_current_weather": get_current_weather_tool.func,
    "run_terminal_command": run_terminal_command_tool.func,
    "launch_application": app_launcher_tool.func,
    "email_management": email_tool.func,
    "calendar_management": calendar_tool.func,
    "web_search": web_search_tool.func,
    "search_memory": smart_lookup_tool.func,
    "get_recent_context": recent_context_tool.func,
}

# Two-stage system prompts
TOOL_SELECTION_PROMPT = """You are Jarvis, an AI assistant that selects tools to execute user commands.

Your job is to analyze the user command and output EXACTLY ONE JSON object with the tool to call.

AVAILABLE TOOLS:
- get_current_weather(city: str) - For weather queries
- run_terminal_command(command: str) - For system commands, file operations
- launch_application(app_name: str) - For opening apps
- email_management(action: str, limit: int, unread_only: bool, to: str, subject: str, body: str, query: str) - For email
- calendar_management(action: str, title: str, date: str, time: str, duration: int, description: str, query: str, days_ahead: int, days_back: int) - For calendar
- web_search(query: str, num_results: int) - For web searches
- search_memory(query: str, search_type: str) - For searching past conversations
- get_recent_context(limit: int) - For recent conversation context

RULES:
1. Output ONLY valid JSON in this format: {"tool": "tool_name", "parameters": {"param1": "value1", "param2": "value2"}}
2. Use smart defaults for missing parameters
3. For weather: default city to "New York" if not specified
4. For calendar actions: "check", "create", or "search"
5. For email actions: "check", "send", or "search"
6. Convert times: "3pm" → "15:00", "tomorrow" → actual date
7. NO extra text, explanations, or formatting - ONLY the JSON object

EXAMPLES:
User: "What's the weather in London?"
{"tool": "get_current_weather", "parameters": {"city": "London"}}

User: "List files"
{"tool": "run_terminal_command", "parameters": {"command": "ls -la"}}

User: "Open Chrome"
{"tool": "launch_application", "parameters": {"app_name": "Chrome"}}

User: "Check my emails"
{"tool": "email_management", "parameters": {"action": "check", "limit": 5, "unread_only": true}}

User: "Schedule tennis tomorrow at 3pm"
{"tool": "calendar_management", "parameters": {"action": "create", "title": "tennis", "date": "tomorrow", "time": "15:00"}}

Now analyze this command and output the JSON:"""

RESPONSE_GENERATION_PROMPT = """You are Jarvis, an AI assistant. A tool was executed based on the user's command.

Convert the tool result into a natural, conversational response. Be concise and helpful.

USER COMMAND: {command}
TOOL USED: {tool_name}
TOOL RESULT: {tool_result}

Provide a natural response based on the tool result:"""


# Custom Tool Execution System
def execute_tool_command(command: str) -> str:
    """Two-stage tool execution system"""
    import json
    import traceback
    
    try:
        # Stage 1: Get tool selection as JSON
        logging.info("🎯 Stage 1: Getting tool selection...")
        tool_prompt = f"{TOOL_SELECTION_PROMPT}\n\nUser: \"{command}\""
        
        response = llm.invoke(tool_prompt)
        json_response = response.content.strip()
        
        logging.info(f"📋 Raw model response: {json_response}")
        
        # Clean up response - sometimes models add extra text
        if json_response.startswith("```json"):
            json_response = json_response.replace("```json", "").replace("```", "").strip()
        
        # Find JSON object in response
        start_idx = json_response.find('{')
        end_idx = json_response.rfind('}') + 1
        if start_idx != -1 and end_idx > start_idx:
            json_response = json_response[start_idx:end_idx]
        
        # Parse JSON response
        try:
            tool_call = json.loads(json_response)
            tool_name = tool_call["tool"]
            parameters = tool_call["parameters"]
            
            logging.info(f"🔧 Tool: {tool_name}")
            logging.info(f"📝 Parameters: {parameters}")
            
        except json.JSONDecodeError as e:
            logging.error(f"❌ JSON parsing failed: {e}")
            logging.error(f"Raw response: {json_response}")
            return "Sorry, I had trouble understanding that command. Could you rephrase it?"
        except KeyError as e:
            logging.error(f"❌ Missing key in JSON: {e}")
            return "Sorry, I couldn't determine what action to take. Could you be more specific?"
        
        # Stage 2: Execute the tool
        if tool_name not in TOOL_REGISTRY:
            logging.error(f"❌ Unknown tool: {tool_name}")
            return f"Sorry, I don't have access to the '{tool_name}' function."
        
        logging.info("🚀 Stage 2: Executing tool...")
        tool_func = TOOL_REGISTRY[tool_name]
        
        try:
            # Execute the tool with parameters
            tool_result = tool_func(**parameters)
            logging.info(f"✅ Tool executed successfully")
            logging.info(f"📊 Tool result: {tool_result[:200]}...")
            
        except TypeError as e:
            logging.error(f"❌ Tool execution failed - parameter error: {e}")
            return f"Sorry, I had trouble with the parameters for that command. Error: {str(e)}"
        except Exception as e:
            logging.error(f"❌ Tool execution failed: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
        
        # Stage 3: Generate natural response
        logging.info("💬 Stage 3: Generating conversational response...")
        response_prompt = RESPONSE_GENERATION_PROMPT.format(
            command=command,
            tool_name=tool_name,
            tool_result=tool_result
        )
        
        final_response = llm.invoke(response_prompt)
        result = final_response.content.strip()
        
        logging.info(f"🎤 Final response: {result[:100]}...")
        return result
        
    except Exception as e:
        logging.error(f"❌ Execute tool command failed: {e}")
        logging.error(traceback.format_exc())
        return "Sorry, I encountered an unexpected error processing your request."

# Main interaction loop
def write():
    conversation_mode = False
    last_interaction_time = None
    session_id = str(uuid.uuid4())

    # Initialize database
    try:
        from db.models import create_engine_and_tables
        create_engine_and_tables()
        logging.info("✅ Database initialized successfully")
    except Exception as e:
        logging.warning(f"⚠️ Database initialization failed: {e}")

    try:
        while True:
            try:
                if not conversation_mode:
                    logging.info("🎤 Listening for wake word...")
                    audio = stt.listen()
                    transcript = stt.transcribe(audio)

                    if transcript and TRIGGER_WORD in transcript.lower():
                        logging.info(f"🗣 Triggered by: {transcript}")
                        tts.speak("Yes sir?")
                        conversation_mode = True
                        last_interaction_time = time.time()
                    else:
                        logging.debug("Wake word not detected.")
                else:
                    logging.info("🎤 Listening for next command...")
                    audio = stt.listen()
                    command = stt.transcribe(audio)

                    if not command:
                        continue

                    logging.info(f"📥 Command: {command}")
                    
                    if "shut down" in command.lower():
                        tts.speak("Shutting down, sir.")
                        break

                    # Use new two-stage tool execution system
                    logging.info("🤖 Processing command with new system...")
                    content = execute_tool_command(command)
                    
                    # Store in memory
                    try:
                        memory_system.store_conversation(
                            session_id=session_id,
                            user_message=command,
                            assistant_response=content,
                            tools_used=[]  # We'll enhance this later if needed
                        )
                    except Exception as e:
                        logging.warning(f"⚠️ Failed to store conversation in memory: {e}")
                    
                    logging.info(f"✅ System responded: {content}")

                    print("Jarvis:", content)
                    tts.speak(content)
                    last_interaction_time = time.time()

                    if time.time() - last_interaction_time > CONVERSATION_TIMEOUT:
                        logging.info("⌛ Timeout: Returning to wake word mode.")
                        conversation_mode = False

            except Exception as e:
                logging.error(f"❌ Error in interaction loop: {e}")
                time.sleep(1)

    except KeyboardInterrupt:
        logging.info("🛑 Manual interrupt received. Exiting.")
    except Exception as e:
        logging.critical(f"❌ Critical error in main loop: {e}")


if __name__ == "__main__":
    write()
