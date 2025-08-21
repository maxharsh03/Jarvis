#!/usr/bin/env python3
"""
Quick Test Script for Jarvis Fixes
==================================

Tests the specific issues that were failing in the comprehensive test suite.
"""

import os
import sys
import logging
from datetime import datetime

# Add project root to path
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

def setup_test_agent():
    """Setup the Jarvis agent for testing fixes"""
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
            "You are Jarvis, a helpful AI assistant. Use the appropriate tools to answer user queries. "
            "Always extract parameters correctly and provide helpful responses."
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
        max_iterations=2,
        handle_parsing_errors=True,
        max_execution_time=15
    )
    
    return executor

def test_email_fixes():
    """Test the email tool parameter validation fixes"""
    print("🧪 Testing Email Tool Fixes...")
    
    executor = setup_test_agent()
    
    # Test cases that were failing
    test_cases = [
        "Search emails for 'meeting'",
        "How many emails do I have?",
        "Check my emails"
    ]
    
    for test_case in test_cases:
        print(f"  Testing: {test_case}")
        try:
            response = executor.invoke({"input": test_case})
            result = response.get("output", "No output")
            
            # Check for validation errors
            if "validation error" in result.lower():
                print(f"    ❌ Still has validation error: {result[:100]}...")
            elif "error" in result.lower() and "validation" not in result.lower():
                print(f"    ⚠️ Different error: {result[:100]}...")
            else:
                print(f"    ✅ No validation error: {result[:100]}...")
        except Exception as e:
            print(f"    ❌ Exception: {str(e)[:100]}...")
        print()

def test_calendar_fixes():
    """Test the calendar tool parameter validation fixes"""
    print("🧪 Testing Calendar Tool Fixes...")
    
    executor = setup_test_agent()
    
    # Test cases that were failing
    test_cases = [
        "What's on my schedule today?",
        "What's tomorrow's schedule?",
        "Do I have any meetings?"
    ]
    
    for test_case in test_cases:
        print(f"  Testing: {test_case}")
        try:
            response = executor.invoke({"input": test_case})
            result = response.get("output", "No output")
            
            # Check for validation errors
            if "validation error" in result.lower():
                print(f"    ❌ Still has validation error: {result[:100]}...")
            elif "error" in result.lower() and "validation" not in result.lower():
                print(f"    ⚠️ Different error: {result[:100]}...")
            else:
                print(f"    ✅ No validation error: {result[:100]}...")
        except Exception as e:
            print(f"    ❌ Exception: {str(e)[:100]}...")
        print()

def test_tool_selection():
    """Test improved tool selection"""
    print("🧪 Testing Tool Selection Improvements...")
    
    executor = setup_test_agent()
    
    # Test cases for proper tool selection
    test_cases = [
        ("What's the weather?", "weather"),
        ("List files", "terminal"),
        ("Open Chrome", "app_launcher"),
        ("What time is it?", "terminal")
    ]
    
    for test_case, expected_tool in test_cases:
        print(f"  Testing: {test_case} (expect {expected_tool})")
        try:
            response = executor.invoke({"input": test_case})
            result = response.get("output", "No output")
            
            # Simple heuristic to check if right tool was used
            if any(keyword in result.lower() for keyword in ["weather", "temperature", "celsius", "fahrenheit"]) and expected_tool == "weather":
                print(f"    ✅ Weather tool likely used: {result[:100]}...")
            elif any(keyword in result.lower() for keyword in ["files", "directory", "folder"]) and expected_tool == "terminal":
                print(f"    ✅ Terminal tool likely used: {result[:100]}...")
            elif any(keyword in result.lower() for keyword in ["chrome", "launch", "open"]) and expected_tool == "app_launcher":
                print(f"    ✅ App launcher likely used: {result[:100]}...")
            elif any(keyword in result.lower() for keyword in ["time", "date", "clock"]) and expected_tool == "terminal":
                print(f"    ✅ Terminal tool likely used: {result[:100]}...")
            else:
                print(f"    ⚠️ Tool selection unclear: {result[:100]}...")
        except Exception as e:
            print(f"    ❌ Exception: {str(e)[:100]}...")
        print()

def main():
    """Run the fix tests"""
    print("🔧 Jarvis Fix Testing")
    print("=" * 50)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    try:
        test_email_fixes()
        test_calendar_fixes() 
        test_tool_selection()
        
        print("🏁 Fix testing completed!")
        print("Check the results above to see if issues are resolved.")
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()