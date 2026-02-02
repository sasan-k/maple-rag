#!/usr/bin/env python
"""
Test script to verify AWS Bedrock connectivity.

Usage:
    uv run python scripts/test_bedrock.py
    
Requires AWS credentials to be configured via:
    - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    - .env file in project root
    - AWS CLI (aws configure)
    - IAM role (for EC2/Lambda)
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env file
from dotenv import load_dotenv
load_dotenv()


def test_aws_credentials():
    """Test if AWS credentials are available."""
    print("[CHECK] Checking AWS credentials...")
    
    try:
        import boto3
        session = boto3.Session()
        credentials = session.get_credentials()
        
        if credentials is None:
            print("[FAIL] No AWS credentials found!")
            print("   Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables")
            print("   Or run: aws configure")
            return False
        
        print(f"[OK] AWS credentials found")
        print(f"   Region: {session.region_name or os.getenv('AWS_REGION', 'not set')}")
        return True
        
    except Exception as e:
        print(f"[FAIL] Error checking credentials: {e}")
        return False


def test_bedrock_access():
    """Test if we can access AWS Bedrock."""
    print("\n[CHECK] Testing AWS Bedrock access...")
    
    try:
        import boto3
        
        region = os.getenv("AWS_REGION", "ca-central-1")
        client = boto3.client("bedrock", region_name=region)
        
        # List available models
        response = client.list_foundation_models()
        models = response.get("modelSummaries", [])
        
        print(f"[OK] Connected to AWS Bedrock in {region}")
        print(f"   Found {len(models)} foundation models")
        
        # Show some Claude models
        claude_models = [m for m in models if "claude" in m.get("modelId", "").lower()]
        if claude_models:
            print("\n   Available Claude models:")
            for model in claude_models[:5]:
                print(f"   - {model['modelId']}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Error accessing Bedrock: {e}")
        print("   Make sure you have enabled Bedrock models in AWS Console")
        return False


def test_llm_factory():
    """Test the LLM factory with AWS Bedrock."""
    print("\n[CHECK] Testing LLM Factory...")
    
    try:
        from src.llm.factory import LLMFactory
        from src.config.settings import get_settings
        
        settings = get_settings()
        print(f"   Provider: {settings.llm_provider}")
        print(f"   Model: {settings.aws_bedrock_model_id}")
        print(f"   Embedding Model: {settings.aws_bedrock_embedding_model_id}")
        
        # Try to create the chat model
        llm = LLMFactory.create_chat_model()
        print(f"[OK] LLM created: {type(llm).__name__}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Error creating LLM: {e}")
        return False


def test_chat_completion():
    """Test a simple chat completion."""
    print("\n[CHECK] Testing chat completion...")
    
    try:
        from src.llm.factory import LLMFactory
        
        llm = LLMFactory.create_chat_model()
        
        # Simple test message
        response = llm.invoke("Say 'Hello, Canada!' in both English and French. Keep it brief.")
        
        print(f"[OK] Chat completion successful!")
        print(f"\n   Response:\n   {response.content[:300]}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Error in chat completion: {e}")
        return False


def main():
    print("=" * 50)
    print("AWS Bedrock Integration Test")
    print("=" * 50)
    
    # Run tests
    creds_ok = test_aws_credentials()
    if not creds_ok:
        print("\n[WARN] Cannot proceed without AWS credentials")
        return 1
    
    bedrock_ok = test_bedrock_access()
    factory_ok = test_llm_factory()
    
    if bedrock_ok and factory_ok:
        # Only test chat if everything else works
        chat_ok = test_chat_completion()
    else:
        chat_ok = False
    
    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    print(f"AWS Credentials: {'[OK]' if creds_ok else '[FAIL]'}")
    print(f"Bedrock Access:  {'[OK]' if bedrock_ok else '[FAIL]'}")
    print(f"LLM Factory:     {'[OK]' if factory_ok else '[FAIL]'}")
    print(f"Chat Completion: {'[OK]' if chat_ok else '[FAIL]'}")
    
    return 0 if all([creds_ok, bedrock_ok, factory_ok, chat_ok]) else 1


if __name__ == "__main__":
    sys.exit(main())
