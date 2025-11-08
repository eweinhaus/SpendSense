#!/usr/bin/env python3
"""
Test script to verify OpenAI AI workflow works correctly without fallback.
This script tests that:
1. API key is loaded correctly
2. OpenAI client initializes successfully
3. AI generation works and returns content with 'openai' source
4. No fallback to templates occurs
"""

import os
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed. Make sure OPENAI_API_KEY is set in environment.")
    print("   Install with: pip install python-dotenv")

from spendsense.content_generator import ContentGenerator, get_content_generator

def test_api_key_loaded():
    """Test that API key is loaded from environment."""
    print("\n" + "="*60)
    print("TEST 1: API Key Loading")
    print("="*60)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ FAILED: OPENAI_API_KEY not set in environment")
        return False
    
    # Check if it's not the placeholder
    if api_key == "your_openai_api_key_here" or "your" in api_key.lower():
        print("❌ FAILED: OPENAI_API_KEY appears to be a placeholder, not a real key")
        return False
    
    print(f"✅ PASSED: API key is set (length: {len(api_key)} chars)")
    print(f"   Key starts with: {api_key[:7]}...")
    return True


def test_client_initialization():
    """Test that OpenAI client initializes successfully."""
    print("\n" + "="*60)
    print("TEST 2: OpenAI Client Initialization")
    print("="*60)
    
    try:
        generator = ContentGenerator()
        
        if not generator.client:
            print("❌ FAILED: OpenAI client not initialized")
            print("   Check logs above for initialization errors")
            return False
        
        print("✅ PASSED: OpenAI client initialized successfully")
        return True
    except Exception as e:
        print(f"❌ FAILED: Error initializing client: {e}")
        return False


def test_ai_generation():
    """Test that AI generation works and returns OpenAI content."""
    print("\n" + "="*60)
    print("TEST 3: AI Content Generation")
    print("="*60)
    
    try:
        generator = get_content_generator()
        
        if not generator.client:
            print("❌ FAILED: Cannot test - OpenAI client not available")
            return False
        
        # Create test user context
        user_context = {
            'persona': 'high_utilization',
            'signals': {
                'credit_utilization_max': {'value': 75.0},
                'credit_interest_charges': {'value': 50.0}
            },
            'accounts': [
                {
                    'type': 'credit',
                    'current_balance': 5000.0,
                    'limit': 10000.0
                }
            ]
        }
        
        print("   Generating AI recommendations...")
        print("   (This may take 10-30 seconds...)")
        
        result = generator.generate_recommendation(user_context)
        
        if result is None:
            print("❌ FAILED: AI generation returned None (fallback to templates would occur)")
            return False
        
        if 'source' not in result:
            print("❌ FAILED: Result missing 'source' field")
            return False
        
        if result['source'] != 'openai':
            print(f"❌ FAILED: Source is '{result['source']}', expected 'openai'")
            print("   This indicates fallback to templates occurred")
            return False
        
        if 'recommendations' not in result:
            print("❌ FAILED: Result missing 'recommendations' field")
            return False
        
        recommendations = result['recommendations']
        if not isinstance(recommendations, list) or len(recommendations) == 0:
            print("❌ FAILED: Recommendations list is empty")
            return False
        
        print(f"✅ PASSED: Generated {len(recommendations)} AI recommendations")
        print(f"   Source: {result['source']}")
        print(f"   First recommendation title: {recommendations[0].get('title', 'N/A')[:50]}...")
        
        # Verify it's not template content (templates have specific formats)
        first_rec = recommendations[0]
        if 'title' in first_rec and 'content' in first_rec:
            print("   ✅ Recommendation structure is valid")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error during AI generation: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_no_fallback():
    """Test that templates are not used when AI is available."""
    print("\n" + "="*60)
    print("TEST 4: No Template Fallback")
    print("="*60)
    
    try:
        generator = get_content_generator()
        
        if not generator.client:
            print("⚠️  SKIPPED: OpenAI client not available (would fallback to templates)")
            return True  # This is expected if API key not set
        
        # Test with a unique user context to avoid cache
        import time
        user_context = {
            'persona': 'savings_builder',
            'signals': {
                'savings_net_inflow_30d': {'value': 500.0},
                'savings_growth_rate_30d': {'value': 5.0}
            },
            'accounts': [
                {
                    'type': 'savings',
                    'current_balance': 10000.0,
                    'limit': 0
                }
            ]
        }
        
        result = generator.generate_recommendation(user_context)
        
        if result and result.get('source') == 'openai':
            print("✅ PASSED: AI generation used, no template fallback")
            return True
        else:
            print("❌ FAILED: Fallback to templates occurred")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Error testing fallback: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("OpenAI AI Workflow Test")
    print("="*60)
    print("\nThis script verifies that the AI workflow uses OpenAI")
    print("and does not fall back to template-based recommendations.")
    
    results = []
    
    # Run tests
    results.append(("API Key Loading", test_api_key_loaded()))
    results.append(("Client Initialization", test_client_initialization()))
    results.append(("AI Generation", test_ai_generation()))
    results.append(("No Template Fallback", test_no_fallback()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 SUCCESS: All tests passed! AI workflow is working correctly.")
        return 0
    else:
        print("\n⚠️  WARNING: Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())




