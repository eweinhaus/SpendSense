#!/usr/bin/env python3
"""
Helper script to populate development data on Render deployment.

This script calls the admin endpoint to regenerate data after deployment.
Requires operator API key for authentication.
"""

import os
import sys
import httpx
from typing import Optional

# Configuration
RENDER_SERVICE_URL = os.getenv("RENDER_SERVICE_URL", "https://spendsense-2e84.onrender.com")
OPERATOR_API_KEY = os.getenv("OPERATOR_API_KEY", "")

def populate_data(num_users: int = 75, skip_existing: bool = False) -> bool:
    """
    Populate development data on Render service.
    
    Args:
        num_users: Number of users to generate
        skip_existing: Skip if users already exist
        
    Returns:
        True if successful, False otherwise
    """
    if not OPERATOR_API_KEY:
        print("❌ Error: OPERATOR_API_KEY environment variable not set")
        print("   Set it with: export OPERATOR_API_KEY='your-key-here'")
        return False
    
    url = f"{RENDER_SERVICE_URL}/admin/populate-dev-data"
    headers = {
        "X-Operator-API-Key": OPERATOR_API_KEY,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "num_users": str(num_users),
        "skip_existing": "true" if skip_existing else "false"
    }
    
    print(f"🔄 Populating data on {RENDER_SERVICE_URL}...")
    print(f"   Generating {num_users} users...")
    
    try:
        with httpx.Client(timeout=300.0) as client:
            response = client.post(url, headers=headers, data=data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                summary = result.get("summary", {})
                print("✅ Data population successful!")
                print(f"   Users created: {summary.get('users_created', 0)}")
                print(f"   Signals detected: {summary.get('signals_detected', 0)}")
                print(f"   Personas assigned: {summary.get('personas_assigned', 0)}")
                print(f"   Recommendations generated: {summary.get('recommendations_generated', 0)}")
                
                if summary.get('by_persona'):
                    print("\n   Persona breakdown:")
                    for persona, count in summary['by_persona'].items():
                        print(f"     - {persona}: {count} users")
                
                if summary.get('errors'):
                    print("\n   ⚠️  Warnings:")
                    for error in summary['errors'][:5]:
                        print(f"     - {error}")
                
                return True
            else:
                print(f"❌ Error: {result.get('error', 'Unknown error')}")
                return False
        elif response.status_code == 401:
            print("❌ Error: Authentication failed")
            print("   Check that OPERATOR_API_KEY is correct")
            return False
        elif response.status_code == 404:
            print("❌ Error: Service not found or endpoint not available")
            print(f"   Check that {RENDER_SERVICE_URL} is correct and service is deployed")
            return False
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except httpx.RequestError as e:
        print(f"❌ Error connecting to service: {e}")
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Populate development data on Render")
    parser.add_argument(
        "--num-users",
        type=int,
        default=75,
        help="Number of users to generate (default: 75)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip if users already exist"
    )
    parser.add_argument(
        "--url",
        type=str,
        default=RENDER_SERVICE_URL,
        help=f"Render service URL (default: {RENDER_SERVICE_URL})"
    )
    
    args = parser.parse_args()
    
    # Override URL if provided
    global RENDER_SERVICE_URL
    RENDER_SERVICE_URL = args.url
    
    success = populate_data(
        num_users=args.num_users,
        skip_existing=args.skip_existing
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

