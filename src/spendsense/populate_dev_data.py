"""
Script to populate the database with development data.
This script runs the full data pipeline: generate data, detect signals, assign personas, generate recommendations.
"""

import os
import sys
import random
from .database import get_db_connection, init_database
from .generate_data import (
    generate_all_users, generate_user, generate_accounts, 
    generate_credit_card, generate_liability, generate_transactions,
    generate_high_utilization_profile, generate_variable_income_profile,
    generate_subscription_heavy_profile, generate_savings_builder_profile,
    generate_custom_persona_profile, generate_neutral_profile
)
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


def generate_users_for_personas(persona_counts: dict) -> dict:
    """
    Generate users for specific personas.
    
    Args:
        persona_counts: Dictionary mapping persona names to counts, e.g.
            {'high_utilization': 10, 'variable_income': 10, ...}
            
    Returns:
        Dictionary with summary of operations
    """
    # Map persona names to profile generators
    persona_generators = {
        'high_utilization': generate_high_utilization_profile,
        'variable_income': generate_variable_income_profile,
        'subscription_heavy': generate_subscription_heavy_profile,
        'savings_builder': generate_savings_builder_profile,
        'financial_newcomer': generate_custom_persona_profile,  # custom_persona is Financial Newcomer
        'neutral': generate_neutral_profile,
    }
    
    summary = {
        'success': True,
        'users_created': 0,
        'by_persona': {},
        'errors': []
    }
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        total_users = sum(persona_counts.values())
        user_num = 0
        
        for persona_name, count in persona_counts.items():
            if persona_name not in persona_generators:
                summary['errors'].append(f"Unknown persona: {persona_name}")
                continue
            
            generator_func = persona_generators[persona_name]
            summary['by_persona'][persona_name] = 0
            
            for i in range(count):
                user_num += 1
                try:
                    if user_num % 10 == 0:
                        print(f"Generating user {user_num}/{total_users}...")
                    
                    # Generate profile
                    profile = generator_func()
                    profile['persona_type'] = persona_name
                    
                    # Ensure unique email by using timestamp + user_num + persona + random
                    import time
                    import random as random_module
                    import uuid
                    base_time = int(time.time() * 1000000)  # microseconds for better uniqueness
                    unique_id = str(uuid.uuid4())[:8]  # First 8 chars of UUID
                    email = f"persona_{persona_name}_{user_num}_{base_time}_{unique_id}@example.com"
                    
                    # Double-check uniqueness (very unlikely collision but safe)
                    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
                    if cursor.fetchone():
                        # If somehow collides, add more randomness
                        email = f"persona_{persona_name}_{user_num}_{base_time}_{unique_id}_{random_module.randint(100000, 999999)}@example.com"
                    
                    profile['email'] = email
                    
                    # Ensure name is set
                    if 'name' not in profile:
                        from faker import Faker
                        fake_name = Faker()
                        profile['name'] = fake_name.name()
                    
                    # Generate user
                    try:
                        user_id = generate_user(profile, conn)
                        if not user_id or user_id == 0:
                            raise ValueError(f"generate_user returned invalid user_id: {user_id}")
                    except Exception as user_error:
                        raise ValueError(f"generate_user failed: {str(user_error)}") from user_error
                    
                    # Generate accounts
                    accounts_info = generate_accounts(user_id, profile, conn)
                    
                    # Generate credit card liability data
                    for card_info in accounts_info['credit_cards']:
                        # Find matching card spec
                        card_spec = None
                        for card_spec_item in profile['credit_cards']:
                            if abs(card_spec_item['limit'] - card_info['limit']) < 0.01:
                                card_spec = card_spec_item
                                break
                        if not card_spec and profile['credit_cards']:
                            card_spec = profile['credit_cards'][0]
                        
                        if card_spec:
                            generate_credit_card(card_info['db_id'], card_spec, conn)
                    
                    # Generate liability data for mortgages
                    for mortgage_info in accounts_info['mortgages']:
                        mortgage_spec = mortgage_info.get('spec', {})
                        generate_liability(mortgage_info['db_id'], 'mortgage', mortgage_spec, conn)
                    
                    # Generate liability data for student loans
                    for loan_info in accounts_info['student_loans']:
                        loan_spec = loan_info.get('spec', {})
                        generate_liability(loan_info['db_id'], 'student', loan_spec, conn)
                    
                    # Generate transactions
                    # Checking account transactions
                    if accounts_info['checking']:
                        checking_id = accounts_info['checking'][0]['db_id']
                        generate_transactions(checking_id, 'checking', profile, conn)
                    
                    # Credit card transactions
                    for card_info in accounts_info['credit_cards']:
                        generate_transactions(card_info['db_id'], 'credit', profile, conn)
                    
                    summary['users_created'] += 1
                    summary['by_persona'][persona_name] += 1
                    
                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    # Get full error information
                    error_type = type(e).__name__
                    error_str = str(e) if str(e) else repr(e)
                    error_msg = f"Error generating user {user_num} for {persona_name}: {error_type}: {error_str}"
                    summary['errors'].append(error_msg)
                    print(f"⚠️  {error_msg}")
                    print(f"   Full traceback: {error_details[:1000]}")
        
        conn.close()
        print(f"\n✅ Generated {summary['users_created']} users for specified personas!")
        
    except Exception as e:
        summary['success'] = False
        summary['errors'].append(str(e))
        print(f"\n❌ Error during generation: {e}")
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

