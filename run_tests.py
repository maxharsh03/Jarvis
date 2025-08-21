#!/usr/bin/env python3
"""
Quick Test Runner for Jarvis AI Assistant
========================================

This script provides a simple way to run different types of tests:
- Quick smoke tests (basic functionality)
- Full comprehensive tests (all edge cases)
- Specific category tests (weather, email, etc.)
- Security-focused tests
"""

import sys
import os
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_prerequisites():
    """Check if system is ready for testing"""
    print("🔍 Checking prerequisites...")
    
    # Check if Ollama is running
    try:
        import subprocess
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            print("❌ Ollama is not running. Start with: ollama serve")
            return False
        if 'llama3.2' not in result.stdout.lower():
            print("❌ llama3.2 model not found. Install with: ollama pull llama3.2")
            return False
        print("✅ Ollama and llama3.2 model ready")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ Ollama not found. Install from: https://ollama.ai")
        return False
    
    # Check environment file
    if not os.path.exists('.env'):
        print("⚠️ .env file not found - some tests may fail")
    else:
        print("✅ Environment file found")
    
    # Check database
    try:
        from db.models import create_engine_and_tables
        create_engine_and_tables()
        print("✅ Database connection ready")
    except Exception as e:
        print(f"⚠️ Database issue: {e}")
    
    return True

def run_smoke_tests():
    """Run quick smoke tests for basic functionality"""
    print("🚀 Running smoke tests (basic functionality only)...")
    
    from test_comprehensive import JarvisTestSuite
    
    suite = JarvisTestSuite()
    
    # Run only basic tests for each category
    print("Testing basic functionality...")
    suite.test_weather_basic()
    suite.test_terminal_basic()
    suite.test_email_basic()
    suite.test_calendar_basic()
    suite.test_web_search_basic()
    suite.test_app_launcher_basic()
    suite.test_memory_basic()
    
    suite.generate_report()
    return suite.results

def run_security_tests():
    """Run security-focused tests"""
    print("🔒 Running security tests...")
    
    from test_comprehensive import JarvisTestSuite
    
    suite = JarvisTestSuite()
    
    # Run security-specific tests
    suite.test_terminal_security()
    suite.test_security_penetration()
    
    suite.generate_report()
    return suite.results

def run_category_tests(category):
    """Run tests for a specific category"""
    print(f"🎯 Running {category} tests...")
    
    from test_comprehensive import JarvisTestSuite
    
    suite = JarvisTestSuite()
    
    # Map categories to test methods
    category_methods = {
        'weather': ['test_weather_basic', 'test_weather_edge_cases'],
        'terminal': ['test_terminal_basic', 'test_terminal_edge_cases', 'test_terminal_security'],
        'email': ['test_email_basic', 'test_email_edge_cases'],
        'calendar': ['test_calendar_basic', 'test_calendar_creation', 'test_calendar_edge_cases'],
        'search': ['test_web_search_basic', 'test_web_search_complex', 'test_web_search_edge_cases'],
        'apps': ['test_app_launcher_basic', 'test_app_launcher_edge_cases'],
        'memory': ['test_memory_basic', 'test_memory_edge_cases'],
        'nlp': ['test_complex_nlp'],
        'integration': ['test_multi_tool_integration'],
        'performance': ['test_performance'],
        'security': ['test_terminal_security', 'test_security_penetration']
    }
    
    if category in category_methods:
        for method_name in category_methods[category]:
            if hasattr(suite, method_name):
                method = getattr(suite, method_name)
                method()
        suite.generate_report()
    else:
        print(f"❌ Unknown category: {category}")
        print(f"Available categories: {', '.join(category_methods.keys())}")
        return None
    
    return suite.results

def main():
    parser = argparse.ArgumentParser(description="Jarvis AI Assistant Test Runner")
    parser.add_argument('--type', choices=['smoke', 'full', 'security', 'category'], 
                       default='smoke', help='Type of tests to run')
    parser.add_argument('--category', help='Category to test (weather, terminal, email, etc.)')
    parser.add_argument('--skip-prereq', action='store_true', help='Skip prerequisite checks')
    
    args = parser.parse_args()
    
    print("🤖 Jarvis AI Assistant - Test Runner")
    print("=" * 50)
    print(f"Test Type: {args.type}")
    if args.category:
        print(f"Category: {args.category}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Check prerequisites
    if not args.skip_prereq:
        if not check_prerequisites():
            print("❌ Prerequisites not met. Use --skip-prereq to force run.")
            return 1
    
    try:
        if args.type == 'smoke':
            results = run_smoke_tests()
        elif args.type == 'full':
            print("🚀 Running full comprehensive test suite...")
            from test_comprehensive import JarvisTestSuite
            suite = JarvisTestSuite()
            suite.run_all_tests()
            results = suite.results
        elif args.type == 'security':
            results = run_security_tests()
        elif args.type == 'category':
            if not args.category:
                print("❌ --category required for category tests")
                return 1
            results = run_category_tests(args.category)
            if results is None:
                return 1
        
        # Summary
        if results:
            successful = sum(1 for r in results if r.success)
            total = len(results)
            print(f"\n🏁 Test Summary: {successful}/{total} passed ({successful/total*100:.1f}%)")
            
            if successful < total:
                print("⚠️ Some tests failed. Check the detailed logs in test_logs/ directory.")
            else:
                print("🎉 All tests passed!")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())