#!/usr/bin/env python3
"""
Test the new Qwen-based two-stage tool execution system
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Import the new system
from main import execute_tool_command, llm

def test_qwen_system():
    """Test the new two-stage system with various commands"""
    print("🔧 Testing Qwen Two-Stage System")
    print("=" * 60)
    
    test_cases = [
        ("Weather query", "what's the weather in Paris"),
        ("App launch", "open Safari"),
        ("File listing", "list files in current directory"),
        ("Calendar check", "what's on my schedule today"),
        ("Web search", "latest news about AI"),
        ("Memory test", "what do you remember about me"),
    ]
    
    for test_name, command in test_cases:
        print(f"\n🧪 {test_name}")
        print(f"   Command: '{command}'")
        
        try:
            result = execute_tool_command(command)
            print(f"   ✅ Result: {result[:150]}...")
            
            # Check if result looks natural (not JSON or error)
            if result.startswith('{') or result.startswith('Sorry'):
                print(f"   ⚠️  May need refinement")
            else:
                print(f"   👍 Natural response")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    print(f"\n🏁 Two-stage system test completed!")

def test_stage1_only():
    """Test just the JSON tool selection stage"""
    print("\n🎯 Testing Stage 1 (Tool Selection) Only")
    print("=" * 60)
    
    from main import TOOL_SELECTION_PROMPT
    
    commands = [
        "what's the weather in Tokyo",
        "launch Chrome", 
        "check my emails",
        "schedule meeting tomorrow"
    ]
    
    for command in commands:
        print(f"\n📝 Command: '{command}'")
        
        tool_prompt = f"{TOOL_SELECTION_PROMPT}\n\nUser: \"{command}\""
        response = llm.invoke(tool_prompt)
        json_response = response.content.strip()
        
        print(f"   🤖 Raw response: {json_response}")
        
        # Try to parse as JSON
        try:
            import json
            parsed = json.loads(json_response.replace("```json", "").replace("```", "").strip())
            print(f"   ✅ Valid JSON: {parsed}")
        except:
            print(f"   ❌ Invalid JSON format")

if __name__ == "__main__":
    print("🚀 Starting Qwen system tests...")
    
    # Test just stage 1 first
    test_stage1_only()
    
    # Then test full system
    test_qwen_system()