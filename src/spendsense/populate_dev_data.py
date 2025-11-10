"""
Script to populate the database with development data.
This script runs the full data pipeline: generate data, detect signals, assign personas, generate recommendations.
"""

import os
import sys
from .database import get_db_connection, init_database
from .generate_data import generate_all_users
from .detect_signals import detect_signals_for_all_users
from .personas import assign_personas_for_all_users
from .recommendations import generate_recommendations_for_all_users


def populate_dev_data(num_users: int = 75, skip_existing: bool = False) -> dict:
    """
    Populate database with development data.
    
    Args:
        num_users: Number of users to generate (default: 75)
        skip_existing: If True, skip if users already exist
        
    Returns:
        Dictionary with summary of operations
    """
    # Set NUM_USERS environment variable if not already set
    if 'NUM_USERS' not in os.environ:
        os.environ['NUM_USERS'] = str(num_users)
    
    summary = {
        'success': True,
        'users_created': 0,
        'signals_detected': 0,
        'personas_assigned': 0,
        'recommendations_generated': 0,
        'errors': []
    }
    
    try:
        # Initialize database
        print("Initializing database...")
        init_database()
        
        # Check if users already exist
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        existing_users = cursor.fetchone()[0]
        conn.close()
        
        if existing_users > 0 and skip_existing:
            print(f"⚠️  {existing_users} users already exist. Skipping data generation.")
            summary['users_created'] = existing_users
        else:
            if existing_users > 0:
                print(f"⚠️  {existing_users} users already exist. Generating additional users...")
            
            # Generate users
            print(f"\nGenerating {num_users} users...")
            gen_summary = generate_all_users(get_db_connection())
            summary['users_created'] = gen_summary.get('users_created', 0)
            if gen_summary.get('errors'):
                summary['errors'].extend(gen_summary['errors'])
        
        # Detect signals
        print("\nDetecting signals (30d and 180d windows)...")
        signals_summary = detect_signals_for_all_users()
        summary['signals_detected'] = signals_summary.get('total_signals', 0)
        if signals_summary.get('errors'):
            summary['errors'].extend(signals_summary['errors'])
        
        # Assign personas
        print("\nAssigning personas...")
        personas_summary = assign_personas_for_all_users()
        # Count total personas assigned
        personas_assigned_dict = personas_summary.get('personas_assigned', {})
        summary['personas_assigned'] = sum(personas_assigned_dict.values()) if personas_assigned_dict else 0
        if personas_summary.get('errors'):
            summary['errors'].extend(personas_summary['errors'])
        
        # Generate recommendations (only for users with consent)
        print("\nGenerating recommendations...")
        rec_summary = generate_recommendations_for_all_users()
        summary['recommendations_generated'] = rec_summary.get('total_recommendations', 0)
        if rec_summary.get('errors'):
            summary['errors'].extend(rec_summary['errors'])
        
        print("\n✅ Dev data population complete!")
        
    except Exception as e:
        summary['success'] = False
        summary['errors'].append(str(e))
        print(f"\n❌ Error during population: {e}")
        import traceback
        traceback.print_exc()
    
    return summary


if __name__ == "__main__":
    """Run data population from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Populate SpendSense database with development data'
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
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("SpendSense - Dev Data Population")
    print("=" * 60)
    print()
    
    summary = populate_dev_data(num_users=args.num_users, skip_existing=args.skip_existing)
    
    print()
    print("=" * 60)
    print("Population Summary:")
    print("=" * 60)
    print(f"  Success: {summary['success']}")
    print(f"  Users created: {summary['users_created']}")
    print(f"  Signals detected: {summary['signals_detected']}")
    print(f"  Personas assigned: {summary['personas_assigned']}")
    print(f"  Recommendations generated: {summary['recommendations_generated']}")
    
    if summary['errors']:
        print(f"\n  Errors ({len(summary['errors'])}):")
        for error in summary['errors'][:10]:  # Show first 10
            print(f"    - {error}")
        if len(summary['errors']) > 10:
            print(f"    ... and {len(summary['errors']) - 10} more errors")
    else:
        print("  ✓ All operations completed successfully!")
    print("=" * 60)

