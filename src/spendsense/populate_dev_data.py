"""
Development Data Population Module

This module provides utilities for populating the database with development data.
It orchestrates the full data pipeline: generation, signal detection, persona assignment,
and recommendation generation.
"""

import os
from typing import Dict, Any, Optional
from .database import get_db_connection
from .generate_data import generate_users
from .detect_signals import detect_signals_for_all_users
from .personas import assign_personas_for_all_users
from .recommendations import generate_recommendations_for_all_users


def populate_dev_data(num_users: int = 75, skip_existing: bool = False) -> Dict[str, Any]:
    """
    Populate database with development data.
    
    Runs the full data pipeline:
    1. Generate users, accounts, transactions
    2. Detect signals (30d and 180d windows)
    3. Assign personas
    4. Generate recommendations
    
    Args:
        num_users: Number of users to generate (default: 75)
        skip_existing: If True, skip generation if users already exist
        
    Returns:
        Dictionary with summary of operations
    """
    summary = {
        'success': False,
        'users_created': 0,
        'signals_detected': 0,
        'personas_assigned': 0,
        'recommendations_generated': 0,
        'by_persona': {},
        'errors': []
    }
    
    try:
        # Check if users already exist
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        existing_users = cursor.fetchone()[0]
        conn.close()
        
        if skip_existing and existing_users > 0:
            summary['errors'].append(f"Skipped: {existing_users} users already exist")
            summary['success'] = True
            return summary
        
        # Step 1: Generate users
        print(f"Generating {num_users} users...")
        os.environ['NUM_USERS'] = str(num_users)
        from .generate_data import main as generate_main
        generate_main()
        
        # Count users created
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        summary['users_created'] = cursor.fetchone()[0] - existing_users
        conn.close()
        
        # Step 2: Detect signals
        print("Detecting signals...")
        signal_summary = detect_signals_for_all_users()
        summary['signals_detected'] = signal_summary.get('total_signals', 0)
        
        # Step 3: Assign personas
        print("Assigning personas...")
        persona_summary = assign_personas_for_all_users()
        if persona_summary.get('personas_assigned'):
            summary['personas_assigned'] = sum(persona_summary['personas_assigned'].values())
            summary['by_persona'] = persona_summary['personas_assigned']
        
        # Step 4: Generate recommendations
        print("Generating recommendations...")
        rec_summary = generate_recommendations_for_all_users()
        summary['recommendations_generated'] = rec_summary.get('total_recommendations', 0)
        
        summary['success'] = True
        print(f"✅ Dev data population complete: {summary['users_created']} users, "
              f"{summary['signals_detected']} signals, {summary['personas_assigned']} personas, "
              f"{summary['recommendations_generated']} recommendations")
        
    except Exception as e:
        import traceback
        error_msg = f"Error during population: {str(e)}"
        summary['errors'].append(error_msg)
        print(f"❌ {error_msg}")
        traceback.print_exc()
    
    return summary


def generate_users_for_personas(persona_counts: Dict[str, int]) -> Dict[str, Any]:
    """
    Generate users with specific persona characteristics.
    
    This is a simplified version that generates users and relies on the
    persona assignment logic to categorize them correctly.
    
    Args:
        persona_counts: Dictionary mapping persona names to desired counts
                       e.g. {'high_utilization': 10, 'variable_income': 5}
    
    Returns:
        Dictionary with summary of operations
    """
    summary = {
        'success': False,
        'users_created': 0,
        'by_persona': {},
        'errors': []
    }
    
    try:
        total_users = sum(persona_counts.values())
        
        # For now, just generate the total number of users
        # The persona assignment logic will categorize them
        # In a more sophisticated implementation, we could generate
        # users with specific characteristics to match personas
        
        print(f"Generating {total_users} users for specific personas...")
        os.environ['NUM_USERS'] = str(total_users)
        from .generate_data import main as generate_main
        generate_main()
        
        # Count users created
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        summary['users_created'] = cursor.fetchone()[0]
        conn.close()
        
        summary['success'] = True
        summary['by_persona'] = persona_counts
        
        print(f"✅ Generated {summary['users_created']} users")
        
    except Exception as e:
        import traceback
        error_msg = f"Error generating persona users: {str(e)}"
        summary['errors'].append(error_msg)
        print(f"❌ {error_msg}")
        traceback.print_exc()
    
    return summary
