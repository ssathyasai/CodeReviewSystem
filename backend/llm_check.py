#!/usr/bin/env python3
"""
LLM Configuration and Health Check Script
Run this to see which LLM is configured and if it's working
"""

import os
import sys

# Load environment variables from .env file FIRST
try:
    from dotenv import load_dotenv
    # Load .env from parent directory (c:\mstack\codereview\.env)
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_file = os.path.join(parent_dir, '.env')
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"Loaded .env from: {env_file}\n")
    else:
        print(f"WARNING: .env file not found at {env_file}\n")
except ImportError:
    print("WARNING: python-dotenv not installed. Install with: pip install python-dotenv\n")

def check_llm_status():
    print("=" * 80)
    print("LLM CONFIGURATION AND HEALTH CHECK")
    print("=" * 80)
    
    # Check environment variables
    print("\n1. ENVIRONMENT CONFIGURATION:")
    print("-" * 80)
    
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        is_valid = len(groq_api_key) > 10 and groq_api_key.startswith("gsk_")
        key_preview = groq_api_key[:10] + "..." + groq_api_key[-5:] if len(groq_api_key) > 15 else "***"
        print(f"   GROQ_API_KEY: {key_preview} ({'✓ Valid format' if is_valid else '✗ Invalid format'})")
    else:
        print(f"   GROQ_API_KEY: ✗ NOT SET")
    
    llm_provider = os.getenv("LLM_PROVIDER", "ollama")
    print(f"   LLM_PROVIDER: {llm_provider} (env var not needed - hardcoded to Groq in governance_engine_api.py)")
    
    print("\n2. BACKEND CONFIGURATION:")
    print("-" * 80)
    print(f"   Current Directory: {os.getcwd()}")
    print(f"   Python Version: {sys.version}")
    
    # Check if Groq SDK is installed
    print("\n3. PYTHON DEPENDENCIES:")
    print("-" * 80)
    try:
        import groq
        print(f"   ✓ groq library installed (version: {groq.__version__ if hasattr(groq, '__version__') else 'unknown'})")
    except ImportError:
        print(f"   ✗ groq library NOT installed - Run: pip install groq")
    
    try:
        import aiohttp
        print(f"   ✓ aiohttp installed")
    except ImportError:
        print(f"   ✗ aiohttp NOT installed - Run: pip install aiohttp")
    
    # Try to initialize Groq client
    print("\n4. GROQ CLIENT TEST:")
    print("-" * 80)
    try:
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY")
        
        if not api_key:
            print("   ✗ Cannot test - GROQ_API_KEY not set")
        else:
            print("   Initializing Groq client...")
            client = Groq(api_key=api_key)
            print("   ✓ Groq client initialized successfully")
            
            print("   Testing API connection...")
            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "user", "content": "Say 'working' in one word only."}
                    ],
                    temperature=0.1,
                    max_tokens=5
                )
                
                if response and response.choices:
                    result = response.choices[0].message.content.strip()
                    print(f"   ✓ API Connection working! Response: '{result}'")
                else:
                    print("   ✗ API returned no response")
            except Exception as e:
                print(f"   ✗ API call failed: {str(e)}")
                if "401" in str(e) or "unauthorized" in str(e).lower():
                    print("      (Invalid or expired API key)")
                if "429" in str(e):
                    print("      (Rate limit exceeded)")
    except ImportError:
        print("   ✗ Groq library not installed")
    except Exception as e:
        print(f"   ✗ Error during client initialization: {str(e)}")
    
    # Check backend files
    print("\n5. BACKEND FILES:")
    print("-" * 80)
    files_to_check = [
        "main.py",
        "engines/governance_engine.py",
        "engines/governance_engine_api.py",
        ".env"
    ]
    
    for file_path in files_to_check:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        exists = os.path.exists(full_path)
        print(f"   {'✓' if exists else '✗'} backend/{file_path}")
    
    print("\n6. SUMMARY:")
    print("-" * 80)
    print("   The backend is configured to use GROQ (Llama 3.3 70B model)")
    print("   for LLM-powered code analysis.")
    print("\n   To run the backend:")
    print("   $ cd c:\\mstack\\codereview")
    print("   $ python -m uvicorn backend.main:app --reload")
    print("\n   To check LLM status via API (after backend is running):")
    print("   $ curl http://localhost:8000/llm/status")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    check_llm_status()
