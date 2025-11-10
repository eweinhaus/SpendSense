#!/usr/bin/env python3
"""
Script to populate the deployed SpendSense application with sample data.

This script calls the admin API endpoint to trigger data population.
"""

import requests
import sys
import os
from typing import Optional

# Default deployment URL (update if different)
DEFAULT_DEPLOYMENT_URL = "https://spendsense-2e84.onrender.com"


def clear_deployment_data(
    deployment_url: str = DEFAULT_DEPLOYMENT_URL,
    operator_api_key: Optional[str] = None
) -> dict:
    """
    Clear existing data from deployment.
    
    Args:
        deployment_url: Base URL of the deployment
        operator_api_key: Optional operator API key (if OPERATOR_API_KEY env var is set)
        
    Returns:
        Dictionary with response data
    """
    endpoint = f"{deployment_url}/admin/clear-dev-data"
    
    # Prepare headers
    headers = {}
    if operator_api_key:
        headers['X-Operator-API-Key'] = operator_api_key
    elif os.getenv('OPERATOR_API_KEY'):
        headers['X-Operator-API-Key'] = os.getenv('OPERATOR_API_KEY')
    
    print(f"Clearing existing data from {endpoint}...")
    print()
    
    try:
        response = requests.post(endpoint, headers=headers, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error clearing data: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Status code: {e.response.status_code}")
            try:
                print(f"   Response: {e.response.text}")
            except:
                pass
        return {'success': False, 'error': str(e)}


def populate_deployment(
    deployment_url: str = DEFAULT_DEPLOYMENT_URL,
    num_users: int = 75,
    skip_existing: bool = False,
    clear_first: bool = False,
    operator_api_key: Optional[str] = None
) -> dict:
    """
    Populate deployment with sample data.
    
    Args:
        deployment_url: Base URL of the deployment
        num_users: Number of users to generate
        skip_existing: Skip if users already exist
        clear_first: Clear existing data before populating
        operator_api_key: Optional operator API key (if OPERATOR_API_KEY env var is set)
        
    Returns:
        Dictionary with response data
    """
    # Clear existing data first if requested
    if clear_first:
        print("=" * 60)
        print("STEP 1: Clearing Existing Data")
        print("=" * 60)
        print()
        
        clear_result = clear_deployment_data(deployment_url, operator_api_key)
        
        if clear_result.get('success'):
            print("✅ Data cleared successfully!")
            summary = clear_result.get('summary', {})
            print(f"  Users deleted: {summary.get('users_deleted', 0)}")
            print(f"  Signals deleted: {summary.get('signals_deleted', 0)}")
            print(f"  Personas deleted: {summary.get('personas_deleted', 0)}")
            print(f"  Recommendations deleted: {summary.get('recommendations_deleted', 0)}")
            print()
        else:
            print("⚠️  Failed to clear data, but continuing with population...")
            print()
    
    print("=" * 60)
    print(f"STEP {'2' if clear_first else '1'}: Populating Data")
    print("=" * 60)
    print()
    
    endpoint = f"{deployment_url}/admin/populate-dev-data"
    
    # Prepare headers
    headers = {}
    if operator_api_key:
        headers['X-Operator-API-Key'] = operator_api_key
    elif os.getenv('OPERATOR_API_KEY'):
        headers['X-Operator-API-Key'] = os.getenv('OPERATOR_API_KEY')
    
    # Prepare form data
    data = {
        'num_users': num_users,
        'skip_existing': 'true' if skip_existing else 'false'
    }
    
    print(f"Calling {endpoint}...")
    print(f"  Users: {num_users}")
    print(f"  Skip existing: {skip_existing}")
    print()
    
    try:
        response = requests.post(endpoint, data=data, headers=headers, timeout=300)
        response.raise_for_status()
        
        result = response.json()
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error calling API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Status code: {e.response.status_code}")
            try:
                print(f"   Response: {e.response.text}")
            except:
                pass
        return {'success': False, 'error': str(e)}


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Populate deployed SpendSense application with sample data'
    )
    parser.add_argument(
        '--url',
        type=str,
        default=DEFAULT_DEPLOYMENT_URL,
        help=f'Deployment URL (default: {DEFAULT_DEPLOYMENT_URL})'
    )
    parser.add_argument(
        '--num-users',
        type=int,
        default=75,
        help='Number of users to generate (default: 75)'
    )
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip data generation if users already exist'
    )
    parser.add_argument(
        '--clear-first',
        action='store_true',
        help='Clear existing data before populating'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        help='Operator API key (or set OPERATOR_API_KEY env var)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("SpendSense - Deployment Data Population")
    print("=" * 60)
    print()
    
    result = populate_deployment(
        deployment_url=args.url,
        num_users=args.num_users,
        skip_existing=args.skip_existing,
        clear_first=args.clear_first,
        operator_api_key=args.api_key
    )
    
    print()
    print("=" * 60)
    if result.get('success'):
        print("✅ Population Successful!")
        print("=" * 60)
        summary = result.get('summary', {})
        print(f"  Users created: {summary.get('users_created', 0)}")
        print(f"  Signals detected: {summary.get('signals_detected', 0)}")
        print(f"  Personas assigned: {summary.get('personas_assigned', 0)}")
        print(f"  Recommendations generated: {summary.get('recommendations_generated', 0)}")
        
        # Show persona breakdown
        by_persona = summary.get('by_persona', {})
        if by_persona:
            print(f"\n  Persona breakdown:")
            for persona, count in by_persona.items():
                print(f"    - {persona}: {count} users")
        
        errors = summary.get('errors', [])
        if errors:
            print(f"\n  ⚠️  Errors ({len(errors)}):")
            for error in errors[:5]:  # Show first 5
                print(f"    - {error}")
            if len(errors) > 5:
                print(f"    ... and {len(errors) - 5} more errors")
    else:
        print("❌ Population Failed")
        print("=" * 60)
        error = result.get('error', 'Unknown error')
        print(f"  Error: {error}")
        sys.exit(1)
    
    print("=" * 60)


if __name__ == "__main__":
    main()

