#!/usr/bin/env python3
"""
Test the critical agent fixes - bypassing validation layer
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.memory import ConversationSummaryBufferMemory
from langchain_core.prompts import ChatPromptTemplate

# Import tools
from tools.weather import get_current_weather_tool
from tools.terminal import run_terminal_command_tool
from tools.app_launcher import app_launcher_tool
from tools.email import email_tool
from tools.calendar import calendar_tool
from tools.web_search import web_search_tool
from tools.memory import smart_lookup_tool, recent_context_tool

load_dotenv()

def test_agent_fixes():
    """Test the fixed agent without validation layer interference"""
    print("🔧 Testing Agent Fixes")
    print("=" * 50)
    
    # Setup agent exactly like main.py (after fixes)
    llm = ChatOllama(model="llama3.2")
    
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
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are Jarvis, an efficient AI assistant. Your job is to execute user commands using available tools. "
            "Be decisive, take action immediately, and provide concise responses. Do not ask unnecessary questions.\n\n"
            
            "CRITICAL EXECUTION RULES:\n"
            "1. IMMEDIATELY execute the appropriate tool - do not explain what you're going to do\n"
            "2. For weather questions: ALWAYS use get_current_weather tool\n"  
            "3. For calendar: Use calendar_management with appropriate action (check/create/search)\n"
            "4. For apps: Use launch_application tool\n"
            "5. For memory/personal questions: Use search_memory tool first\n"
            "6. Use smart defaults for missing parameters\n"
            "7. Keep responses short and direct\n"
        )),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}")
    ])
    
    memory = ConversationSummaryBufferMemory(
        llm=llm, 
        memory_key="chat_history", 
        return_messages=True,
        max_token_limit=1000
    )
    
    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)
    executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        memory=memory, 
        verbose=False,
        max_iterations=3,
        handle_parsing_errors=True,
        max_execution_time=20
    )
    
    # Test critical failing scenarios from log
    test_cases = [
        ("Weather test", "what's the weather in New York"),
        ("Calendar creation", "schedule tennis tomorrow at 3pm"),
        ("Memory test", "remember that I like pizza"),
        ("Memory recall", "what do I like to eat?"),
        ("App launch", "open Chrome"),
    ]
    
    for test_name, command in test_cases:
        print(f"\n🧪 {test_name}: '{command}'")
        try:
            # This is exactly what main.py now does (direct to agent)
            response = executor.invoke({"input": command})
            result = response.get("output", "No output")
            
            print(f"   ✅ Response: {result[:150]}...")
            
            # Check if it looks like proper tool execution
            if "tool" in result.lower() and "action=" in result:
                print("   ❌ Agent outputting tool syntax instead of executing!")
            elif len(result) > 500:
                print("   ⚠️ Response very long - might be verbose")
            else:
                print("   👍 Response looks good")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}...")
        
    print("\n🏁 Test completed!")
    print("Check if responses show actual tool execution vs. tool syntax output")

if __name__ == "__main__":
    test_agent_fixes()