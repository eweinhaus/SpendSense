"""
Recommendation engine module for SpendSense MVP.
Generates personalized recommendations based on user personas.
"""

import sqlite3
import json
from typing import List, Dict, Optional
from .database import get_db_connection
from .personas import get_user_signals
from .rationales import generate_rationale
from .traces import generate_decision_trace


# Content templates for each persona
TEMPLATES = {
    "high_utilization": [
        {
            "key": "reduce_utilization",
            "title": "Strategies to Lower Your Credit Card Utilization",
            "content": (
                "High credit card utilization can negatively impact your credit score. "
                "Here are strategies to reduce it:\n\n"
                "• Pay more than the minimum payment each month\n"
                "• Consider a balance transfer to a card with lower interest\n"
                "• Create a payment plan to systematically reduce your balance\n"
                "• Avoid new charges on high-utilization cards\n"
                "• Aim to keep utilization below 30% for optimal credit health"
            ),
            "always_include": True
        },
        {
            "key": "credit_scores",
            "title": "How Credit Utilization Affects Your Credit Score",
            "content": (
                "Credit utilization is a key factor in your credit score calculation, "
                "accounting for about 30% of your FICO score.\n\n"
                "• Keeping utilization below 30% is ideal\n"
                "• Utilization above 50% can significantly impact your score\n"
                "• Utilization above 80% is considered very high risk\n"
                "• Your score updates as your utilization changes\n"
                "• Even small reductions can help improve your score over time"
            ),
            "always_include": True
        },
        {
            "key": "autopay",
            "title": "Avoid Missed Payments with Autopay",
            "content": (
                "Setting up autopay ensures you never miss a payment and avoid late fees.\n\n"
                "• Automatically pay your minimum payment each month\n"
                "• Set up to pay more than minimum to reduce balance faster\n"
                "• Choose payment date that aligns with your payday\n"
                "• Monitor your account to ensure payments process correctly\n"
                "• Consider setting up alerts for payment confirmations"
            ),
            "always_include": False,
            "condition": "overdue_or_interest"
        }
    ],
    "subscription_heavy": [
        {
            "key": "audit_subscriptions",
            "title": "Review Your Recurring Subscriptions",
            "content": (
                "You have multiple recurring subscriptions. Here's a checklist to review them:\n\n"
                "• List all your active subscriptions\n"
                "• Identify services you no longer use\n"
                "• Calculate your total monthly subscription cost\n"
                "• Prioritize which subscriptions provide the most value\n"
                "• Consider canceling unused services to save money"
            ),
            "always_include": True
        },
        {
            "key": "negotiation",
            "title": "How to Reduce Subscription Costs",
            "content": (
                "Many subscription services offer discounts or can be negotiated. Here's how:\n\n"
                "• Contact customer service to ask about promotional rates\n"
                "• Switch to annual plans for better per-month pricing\n"
                "• Look for student, family, or bundle discounts\n"
                "• Consider sharing family plans with trusted friends/family\n"
                "• Review your usage and downgrade to lower tiers if needed"
            ),
            "always_include": False,
            "condition": "high_spend"
        },
        {
            "key": "bill_alerts",
            "title": "Track Your Recurring Charges",
            "content": (
                "Set up alerts to track when subscriptions renew and how much they cost.\n\n"
                "• Enable email notifications for recurring charges\n"
                "• Set calendar reminders before renewal dates\n"
                "• Review your bank statements monthly for subscription charges\n"
                "• Use budgeting apps to track subscription spending\n"
                "• Regularly audit your subscriptions (quarterly or annually)"
            ),
            "always_include": True
        }
    ],
    "neutral": [
        {
            "key": "financial_habits",
            "title": "Build Healthy Financial Habits",
            "content": (
                "Establishing good financial habits can help you achieve your goals.\n\n"
                "• Create a monthly budget and track your spending\n"
                "• Build an emergency fund with 3-6 months of expenses\n"
                "• Set up automatic savings transfers\n"
                "• Review your financial goals regularly\n"
                "• Educate yourself about personal finance topics"
            ),
            "always_include": True
        },
        {
            "key": "savings_tips",
            "title": "Simple Ways to Save Money",
            "content": (
                "Small changes can add up to significant savings over time.\n\n"
                "• Review your recurring expenses monthly\n"
                "• Cook at home more often\n"
                "• Use cashback apps and credit card rewards\n"
                "• Compare prices before major purchases\n"
                "• Set specific savings goals to stay motivated"
            ),
            "always_include": True
        },
        {
            "key": "credit_education",
            "title": "Understanding Credit and Debt",
            "content": (
                "A solid understanding of credit can help you make better financial decisions.\n\n"
                "• Learn how credit scores are calculated\n"
                "• Understand the difference between good and bad debt\n"
                "• Know your credit utilization ratio\n"
                "• Check your credit report regularly\n"
                "• Use credit responsibly to build a strong credit history"
            ),
            "always_include": True
        }
    ]
}


def get_templates_for_persona(persona_type: str) -> List[Dict]:
    """
    Get content templates for a persona.
    
    Args:
        persona_type: Persona type (high_utilization, subscription_heavy, neutral)
        
    Returns:
        List of template dictionaries
    """
    return TEMPLATES.get(persona_type, TEMPLATES["neutral"])


def select_template(key: str, templates: List[Dict]) -> Optional[Dict]:
    """
    Select a specific template by key.
    
    Args:
        key: Template key
        templates: List of template dictionaries
        
    Returns:
        Template dictionary or None if not found
    """
    for template in templates:
        if template.get("key") == key:
            return template
    return None


def get_user_persona(user_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[str]:
    """
    Get assigned persona for a user.
    
    Args:
        user_id: User ID
        conn: Database connection (creates new if None)
        
    Returns:
        Persona type or None if not assigned
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT persona_type FROM personas WHERE user_id = ?
        """, (user_id,))
        
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        if close_conn:
            conn.close()


def store_recommendation(user_id: int, title: str, content: str, rationale: str,
                        persona_matched: str, conn: Optional[sqlite3.Connection] = None) -> int:
    """
    Store recommendation in database.
    
    Args:
        user_id: User ID
        title: Recommendation title
        content: Recommendation content
        rationale: Data-driven rationale
        persona_matched: Persona type
        conn: Database connection (creates new if None)
        
    Returns:
        Recommendation ID
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO recommendations (
                user_id, title, content, rationale, persona_matched
            ) VALUES (?, ?, ?, ?, ?)
        """, (user_id, title, content, rationale, persona_matched))
        
        recommendation_id = cursor.lastrowid
        conn.commit()
        
        return recommendation_id
    finally:
        if close_conn:
            conn.close()


def generate_recommendations(user_id: int, conn: Optional[sqlite3.Connection] = None) -> List[int]:
    """
    Generate 2-3 personalized recommendations for a user.
    
    Args:
        user_id: User ID
        conn: Database connection (creates new if None)
        
    Returns:
        List of recommendation IDs
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        # Get user persona
        persona = get_user_persona(user_id, conn)
        if not persona:
            # If no persona assigned, assign one
            from personas import assign_persona
            persona = assign_persona(user_id, conn)
        
        # Get user signals for rationale generation
        signals_list = get_user_signals(user_id, conn)
        # Convert to dict for easier lookup
        signals_dict = {}
        for signal in signals_list:
            signals_dict[signal['signal_type']] = signal
        
        # Get templates for persona
        templates = get_templates_for_persona(persona)
        
        # Select recommendations
        recommendations = []
        used_titles = set()
        
        # Always include templates marked as always_include
        for template in templates:
            if template.get("always_include", False):
                key = template.get("key")
                if key not in used_titles:
                    recommendations.append(template)
                    used_titles.add(key)
        
        # Check conditional templates
        for template in templates:
            if template.get("key") in used_titles:
                continue
            
            condition = template.get("condition")
            if condition == "overdue_or_interest":
                overdue = signals_dict.get('credit_overdue', {}).get('value', 0) or 0
                interest = signals_dict.get('credit_interest_charges', {}).get('value', 0) or 0
                if overdue == 1.0 or interest > 0:
                    recommendations.append(template)
                    used_titles.add(template.get("key"))
            elif condition == "high_spend":
                monthly_spend = signals_dict.get('subscription_monthly_spend', {}).get('value', 0) or 0
                if monthly_spend >= 75.0:
                    recommendations.append(template)
                    used_titles.add(template.get("key"))
        
        # Ensure we have at least 2 recommendations
        if len(recommendations) < 2:
            # Add more templates if needed
            for template in templates:
                if template.get("key") not in used_titles:
                    recommendations.append(template)
                    used_titles.add(template.get("key"))
                    if len(recommendations) >= 3:
                        break
        
        # Limit to 2-3 recommendations
        recommendations = recommendations[:3]
        
        # Generate and store recommendations
        recommendation_ids = []
        
        for template in recommendations:
            # Generate rationale
            rationale = generate_rationale(user_id, {
                'title': template['title'],
                'persona_matched': persona
            }, signals_dict, conn)
            
            # Store recommendation
            rec_id = store_recommendation(
                user_id,
                template['title'],
                template['content'],
                rationale,
                persona,
                conn
            )
            
            recommendation_ids.append(rec_id)
            
            # Generate decision trace
            generate_decision_trace(
                user_id,
                rec_id,
                persona,
                template,
                signals_dict,
                conn
            )
        
        return recommendation_ids
        
    finally:
        if close_conn:
            conn.close()


def generate_recommendations_for_all_users(conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Generate recommendations for all users in the database.
    
    Args:
        conn: Database connection (creates new if None)
        
    Returns:
        Summary dictionary with results
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users")
        user_ids = [row[0] for row in cursor.fetchall()]
        
        summary = {
            'users_processed': 0,
            'total_recommendations': 0,
            'results': []
        }
        
        for user_id in user_ids:
            print(f"Generating recommendations for user {user_id}...")
            rec_ids = generate_recommendations(user_id, conn)
            summary['users_processed'] += 1
            summary['total_recommendations'] += len(rec_ids)
            summary['results'].append({
                'user_id': user_id,
                'recommendation_count': len(rec_ids),
                'recommendation_ids': rec_ids
            })
            print(f"  ✓ Generated {len(rec_ids)} recommendations")
        
        return summary
        
    finally:
        if close_conn:
            conn.close()


if __name__ == "__main__":
    """Run recommendation generation for all users."""
    print("=" * 60)
    print("SpendSense - Recommendation Generation")
    print("=" * 60)
    print()
    
    summary = generate_recommendations_for_all_users()
    
    print()
    print("=" * 60)
    print("Generation Summary:")
    print(f"  Users processed: {summary['users_processed']}")
    print(f"  Total recommendations: {summary['total_recommendations']}")
    print("=" * 60)

