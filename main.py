import os
import logging
import time
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

from agents.intent_classifier import intent_classifier, Intent
from agents.tool_validator import tool_validator
from agents.state_manager import state_manager

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.memory import ConversationSummaryBufferMemory
from db.memory import memory_system
import uuid

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
llm = ChatOllama(model="llama3.2")

# Available tools
tools = [
    get_current_weather_tool,
    run_terminal_command_tool,
    app_launcher_tool,
    email_tool,
    calendar_tool,
    web_search_tool,
    smart_lookup_tool,
    recent_context_tool
]

# System prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", (
        "You are Jarvis, a helpful, witty, and intelligent AI assistant with access to various tools. "
        "Use contextual inference and avoid redundant questions. Always check memory first for relevant information. "
        "Keep responses short, smart, and human-like. If the user says 'Jarvis shut down', terminate immediately.\n\n"
        
        "TOOL USAGE GUIDELINES:\n\n"
        
        "🌤️ WEATHER:\n"
        "- User: 'what's the weather' → get_current_weather_tool(location='current location')\n"
        "- User: 'weather in NYC' → get_current_weather_tool(location='New York City')\n"
        "- User: 'is it raining?' → get_current_weather_tool(location='current location')\n\n"
        
        "💻 TERMINAL:\n"
        "- User: 'list files on desktop' → run_terminal_command(command='ls ~/Desktop')\n"
        "- User: 'run ellis' → run_terminal_command(command='ls')\n"
        "- User: 'show me what's in this folder' → run_terminal_command(command='ls -la')\n"
        "- User: 'check git status' → run_terminal_command(command='git status')\n"
        "- User: 'create a folder called test' → run_terminal_command(command='mkdir test')\n\n"
        
        "📅 CALENDAR:\n"
        "- User: 'schedule gym tomorrow at 3pm' → calendar_management(action='create', title='gym', date='2024-XX-XX', time='15:00')\n"
        "- User: 'I'm going to the gym at 5' → calendar_management(action='create', title='gym', time='17:00')\n"
        "- User: 'what's on my calendar' → calendar_management(action='check')\n"
        "- User: 'check my schedule for next week' → calendar_management(action='check', days_ahead=7)\n\n"
        
        "📧 EMAIL:\n"
        "- User: 'send email to john@example.com' → email_tool(action='send', to='john@example.com')\n"
        "- User: 'check my emails' → email_tool(action='read')\n"
        "- User: 'send message about meeting' → email_tool(action='send', subject='meeting', content='...')\n\n"
        
        "🚀 APP LAUNCHER:\n"
        "- User: 'open chrome' → app_launcher_tool(app_name='chrome')\n"
        "- User: 'launch spotify' → app_launcher_tool(app_name='spotify')\n"
        "- User: 'start slack' → app_launcher_tool(app_name='slack')\n\n"
        
        "🔍 WEB SEARCH:\n"
        "- User: 'search for python tutorials' → web_search_tool(query='python tutorials')\n"
        "- User: 'look up weather API' → web_search_tool(query='weather API')\n"
        "- User: 'what is machine learning' → web_search_tool(query='what is machine learning')\n\n"
        
        "🧠 MEMORY:\n"
        "- User: 'what did we discuss earlier' → smart_lookup_tool(query='recent discussion')\n"
        "- User: 'remember my preferences' → recent_context_tool()\n"
        "- Always check memory BEFORE using other tools for relevant context\n\n"
        
        "Parse user intent, extract parameters, and call the appropriate tool with proper arguments."
    )),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])

# Conversation memory
memory = ConversationSummaryBufferMemory(
    llm=llm, 
    memory_key="chat_history", 
    return_messages=True,
    max_token_limit=2000
)

# Agent setup
agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)
executor = AgentExecutor(agent=agent, tools=tools, memory=memory, verbose=True)


# Helper functions
def _format_task_completion(validation_result):
    """Format completed task for agent execution."""
    fields = validation_result.extracted_fields
    if 'title' in fields:  # Calendar event
        return f"Create calendar event: title='{fields.get('title')}', date='{fields.get('date', 'tomorrow')}', time='{fields.get('time', '09:00')}'"
    elif 'to' in fields:  # Email
        return f"Send email to {fields['to']} with subject '{fields.get('subject', '')}' and content '{fields.get('content', '')}'"
    elif 'query' in fields:  # Search
        return f"Search for: {fields['query']}"
    else:
        return f"Execute task with fields: {fields}"

def _format_enhanced_input(command, intent, validation_result):
    """Format enhanced input with context and extracted fields."""
    # Get relevant context from memory
    context = memory_system.get_context_for_query(command)
    
    # Build enhanced input
    enhanced_parts = []
    
    if context:
        enhanced_parts.append(f"Context from memory:\n{context}")
    
    # Add state context
    state_summary = state_manager.get_state_summary()
    if state_summary != "No active tasks.":
        enhanced_parts.append(f"Current state: {state_summary}")
    
    # Add intent and extracted fields
    enhanced_parts.append(f"Intent: {intent.value}")
    if validation_result.extracted_fields:
        enhanced_parts.append(f"Extracted fields: {validation_result.extracted_fields}")
    
    enhanced_parts.append(f"Current query: {command}")
    
    return "\n\n".join(enhanced_parts)

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

                    # Handle pending task responses
                    validation_result = tool_validator.complete_task_with_response(command)
                    if validation_result:
                        if validation_result.is_valid:
                            # Task completed
                            logging.info("✅ Completed pending task with user response")
                            enhanced_input = _format_task_completion(validation_result)
                        else:
                            # Still missing info
                            content = validation_result.clarification
                            logging.info(f"📝 Still need clarification: {content}")
                            print("Jarvis:", content)
                            tts.speak(content)
                            last_interaction_time = time.time()
                            continue
                    else:
                        # New command - classify and validate
                        intent, confidence = intent_classifier.classify_intent(command)
                        logging.info(f"🎯 Classified intent: {intent.value} (confidence: {confidence:.2f})")
                        
                        validation_result = tool_validator.validate_and_extract(command, intent)
                        
                        if not validation_result.is_valid:
                            # Missing fields, ask for clarification
                            content = validation_result.clarification
                            logging.info(f"❓ Need clarification: {content}")
                            print("Jarvis:", content)
                            tts.speak(content)
                            last_interaction_time = time.time()
                            continue
                        
                        # All fields present, proceed
                        enhanced_input = _format_enhanced_input(command, intent, validation_result)
                    
                    logging.info("🤖 Sending command to agent...")
                    
                    response = executor.invoke({"input": enhanced_input})
                    content = response["output"]
                    
                    # Store in memory
                    try:
                        tools_used = []
                        if "intermediate_steps" in response:
                            for step in response["intermediate_steps"]:
                                if hasattr(step[0], 'tool'):
                                    tools_used.append(step[0].tool)
                        
                        memory_system.store_conversation(
                            session_id=session_id,
                            user_message=command,
                            assistant_response=content,
                            tools_used=tools_used
                        )
                    except Exception as e:
                        logging.warning(f"⚠️ Failed to store conversation in memory: {e}")
                    
                    logging.info(f"✅ Agent responded: {content}")

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
