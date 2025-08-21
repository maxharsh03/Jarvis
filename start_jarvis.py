#!/usr/bin/env python3
"""
Jarvis startup script with system checks and initialization.
Run this script to start Jarvis with proper setup validation.
"""

import os
import sys
import subprocess
import importlib.util
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.8+"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python version: {sys.version.split()[0]}")

def check_ollama():
    """Check if Ollama is running and has required models"""
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            models = result.stdout.lower()
            if 'llama3.2' in models or 'llama3' in models:
                print("✅ Ollama is running with required models")
                return True
            else:
                print("⚠️ Ollama is running but llama3.2 model not found")
                print("Run: ollama pull llama3.2")
                return False
        else:
            print("❌ Ollama is not responding")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ Ollama not found or not running")
        print("Install from: https://ollama.ai")
        print("Then run: ollama pull llama3.2")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'langchain',
        'langchain_ollama', 
        'speech_recognition',
        'pyttsx3',
        'requests',
        'sqlalchemy',
        'chromadb',
        'python_dotenv'
    ]
    
    missing_packages = []
    for package in required_packages:
        package_name = package.replace('_', '-')  # Handle package name differences
        if importlib.util.find_spec(package) is None:
            missing_packages.append(package_name)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nInstall with: pip install -r requirements.txt")
        return False
    
    print("✅ All required packages installed")
    return True

def check_env_file():
    """Check if .env file exists and has required settings"""
    env_path = Path('.env')
    if not env_path.exists():
        print("⚠️ .env file not found")
        print("Copy .env.example to .env and configure your settings")
        return False
    
    # Check for critical environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    warnings = []
    if not os.getenv('WEATHER_API_KEY'):
        warnings.append("WEATHER_API_KEY not set - weather features will be limited")
    
    if not os.getenv('EMAIL_ADDRESS') or not os.getenv('EMAIL_PASSWORD'):
        warnings.append("Email credentials not set - email features will be disabled")
    
    if warnings:
        print("⚠️ Environment warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("✅ Environment configuration looks good")
    
    return True

def check_audio():
    """Check if audio system is available"""
    try:
        import speech_recognition as sr
        import pyttsx3
        
        # Test microphone
        r = sr.Recognizer()
        mic = sr.Microphone()
        print("✅ Audio input available")
        
        # Test TTS
        engine = pyttsx3.init()
        engine.stop()
        print("✅ Audio output available")
        return True
        
    except Exception as e:
        print(f"⚠️ Audio system check failed: {e}")
        print("Voice features may not work properly")
        return False

def initialize_database():
    """Initialize database if needed"""
    try:
        from db.models import create_engine_and_tables
        create_engine_and_tables()
        print("✅ Database initialized")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def main():
    """Main startup routine"""
    print("🚀 Starting Jarvis AI Assistant...")
    print("=" * 50)
    
    # Run all checks
    checks_passed = 0
    total_checks = 6
    
    print("🔍 System Check 1/6: Python Version")
    check_python_version()
    checks_passed += 1
    
    print("\n🔍 System Check 2/6: Dependencies")
    if check_dependencies():
        checks_passed += 1
    
    print("\n🔍 System Check 3/6: Environment Configuration")
    if check_env_file():
        checks_passed += 1
    
    print("\n🔍 System Check 4/6: Ollama LLM Backend")
    if check_ollama():
        checks_passed += 1
    
    print("\n🔍 System Check 5/6: Audio System")
    if check_audio():
        checks_passed += 1
    
    print("\n🔍 System Check 6/6: Database")
    if initialize_database():
        checks_passed += 1
    
    print("\n" + "=" * 50)
    print(f"✅ System checks completed: {checks_passed}/{total_checks} passed")
    
    if checks_passed >= 4:  # Minimum required checks
        print("\n🎤 Starting Jarvis voice interface...")
        print("Say 'Jarvis' to activate, 'Jarvis shut down' to exit")
        print("-" * 50)
        
        # Import and start main interface
        from main import write
        write()
    else:
        print("\n❌ Too many system checks failed")
        print("Please resolve the issues above before running Jarvis")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye! Jarvis shutting down...")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Check the logs and try again")