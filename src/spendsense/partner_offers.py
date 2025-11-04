"""
Partner offers module for SpendSense MVP.
Provides eligible partner offers based on user profile and eligibility checks.
"""

import sqlite3
import logging
from typing import List, Dict, Optional, Tuple
from .database import get_db_connection
from .eligibility import check_eligibility, estimate_annual_income, get_user_accounts
from .personas import get_user_signals

# Configure logging
logger = logging.getLogger(__name__)


# Partner offers catalog
OFFER_CATALOG = [
    {
        "id": "balance_transfer_card",
        "title": "Balance Transfer Credit Card",
        "description": "Transfer high-interest credit card debt to a card with 0% introductory APR for 12-18 months",
        "type": "credit_card",
        "eligibility_requirements": {
            "min_utilization": 50.0,  # High utilization threshold
            "min_credit_score": 650,  # If available
            "exclude_accounts": ["balance_transfer_card"],
            "personas": ["high_utilization"]  # Preferred personas
        },
        "benefits": [
            "Lower or 0% interest rate during promotional period",
            "Save on interest charges",
            "Help pay down debt faster"
        ]
    },
    {
        "id": "high_yield_savings",
        "title": "High-Yield Savings Account (HYSA)",
        "description": "Earn 4-5% APY on your savings compared to 0.01% with traditional savings accounts",
        "type": "savings_account",
        "eligibility_requirements": {
            "min_savings": 0,  # No minimum, but prefer users building savings
            "exclude_accounts": ["high_yield_savings", "savings"],
            "personas": ["savings_builder", "variable_income_budgeter"]
        },
        "benefits": [
            "Earn 40-50x more interest than traditional savings",
            "FDIC insured up to $250,000",
            "Easy access to funds when needed"
        ]
    },
    {
        "id": "budgeting_app",
        "title": "Budgeting App Subscription",
        "description": "Track spending, set budgets, and achieve financial goals with automated budgeting tools",
        "type": "app_subscription",
        "eligibility_requirements": {
            "personas": ["variable_income_budgeter", "subscription_heavy", "financial_newcomer"]
        },
        "benefits": [
            "Automated expense tracking",
            "Budget alerts and notifications",
            "Goal setting and progress tracking",
            "Financial insights and reports"
        ]
    },
    {
        "id": "subscription_management_tool",
        "title": "Subscription Management Tool",
        "description": "Track, manage, and cancel subscriptions all in one place to reduce recurring expenses",
        "type": "app_subscription",
        "eligibility_requirements": {
            "min_subscription_count": 3,  # Prefer users with multiple subscriptions
            "personas": ["subscription_heavy"]
        },
        "benefits": [
            "Track all subscriptions in one place",
            "Identify unused subscriptions",
            "Cancel subscriptions easily",
            "Save money on recurring charges"
        ]
    }
]


def get_user_signals_dict(user_id: int, conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Get user signals as a dictionary for easier lookup.
    
    Args:
        user_id: User ID
        conn: Database connection (creates new if None)
        
    Returns:
        Dictionary of signal_type -> signal data
    """
    signals_list = get_user_signals(user_id, conn)
    signals_dict = {}
    for signal in signals_list:
        signals_dict[signal['signal_type']] = signal
    return signals_dict


def check_offer_eligibility(user_id: int, offer: Dict, conn: Optional[sqlite3.Connection] = None) -> Tuple[bool, str]:
    """
    Check if a user is eligible for a specific offer.
    
    Args:
        user_id: User ID
        offer: Offer dictionary from OFFER_CATALOG
        conn: Database connection (creates new if None)
        
    Returns:
        Tuple of (is_eligible: bool, rationale: str)
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        requirements = offer.get("eligibility_requirements", {})
        
        # Check persona match (preferred, not required)
        preferred_personas = requirements.get("personas", [])
        if preferred_personas:
            cursor = conn.cursor()
            cursor.execute("SELECT persona_type FROM personas WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            user_persona = result[0] if result else None
            # Persona match is preferred but not required
            persona_match = user_persona in preferred_personas if user_persona else False
        else:
            persona_match = True
        
        # Check account exclusions
        exclude_accounts = requirements.get("exclude_accounts", [])
        if exclude_accounts:
            accounts = get_user_accounts(user_id, conn)
            account_types = [acc['type'].lower() for acc in accounts]
            account_subtypes = [acc['subtype'].lower() if acc['subtype'] else '' 
                              for acc in accounts]
            all_account_identifiers = account_types + account_subtypes
            
            for excluded in exclude_accounts:
                if excluded.lower() in all_account_identifiers:
                    return False, f"User already has {excluded} account"
        
        # Check utilization requirements
        min_utilization = requirements.get("min_utilization")
        if min_utilization is not None:
            signals_dict = get_user_signals_dict(user_id, conn)
            utilization = signals_dict.get('credit_utilization_max', {}).get('value', 0) or 0
            if utilization < min_utilization:
                return False, f"Credit utilization ({utilization:.0f}%) below threshold ({min_utilization:.0f}%)"
        
        # Check subscription count requirements
        min_subscription_count = requirements.get("min_subscription_count")
        if min_subscription_count is not None:
            signals_dict = get_user_signals_dict(user_id, conn)
            sub_count = signals_dict.get('subscription_count', {}).get('value', 0) or 0
            if sub_count < min_subscription_count:
                return False, f"Subscription count ({int(sub_count)}) below threshold ({min_subscription_count})"
        
        # Check savings requirements
        min_savings = requirements.get("min_savings")
        if min_savings is not None:
            # This is a soft requirement - prefer users building savings
            # We'll use it in rationale generation but not block eligibility
            pass
        
        # Use existing eligibility system for comprehensive checks
        is_eligible, reason = check_eligibility(user_id, offer["title"], conn)
        
        if not is_eligible:
            return False, reason
        
        # Build rationale
        rationale_parts = []
        
        if offer["id"] == "balance_transfer_card":
            signals_dict = get_user_signals_dict(user_id, conn)
            utilization = signals_dict.get('credit_utilization_max', {}).get('value', 0) or 0
            interest = signals_dict.get('credit_interest_charges', {}).get('value', 0) or 0
            if utilization > 0:
                rationale_parts.append(f"Your credit utilization is {utilization:.0f}%")
            if interest > 0:
                rationale_parts.append(f"you're paying ${interest:.2f}/month in interest charges")
                estimated_savings = interest * 12  # Rough estimate
                rationale_parts.append(f"A balance transfer could save you approximately ${estimated_savings:.0f}/year in interest")
        
        elif offer["id"] == "high_yield_savings":
            signals_dict = get_user_signals_dict(user_id, conn)
            savings_balance = 0
            # Try to get savings account balance
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(current_balance) FROM accounts
                WHERE user_id = ? AND (type = 'depository' OR subtype = 'savings')
            """, (user_id,))
            result = cursor.fetchone()
            if result and result[0]:
                savings_balance = result[0]
            
            if savings_balance > 0:
                # Calculate potential earnings
                traditional_apy = 0.0001  # 0.01%
                hysa_apy = 0.045  # 4.5%
                traditional_earnings = savings_balance * traditional_apy
                hysa_earnings = savings_balance * hysa_apy
                additional_earnings = hysa_earnings - traditional_earnings
                rationale_parts.append(f"With your current savings balance of ${savings_balance:.2f}")
                rationale_parts.append(f"a high-yield savings account could earn you approximately ${additional_earnings:.2f} more per year")
        
        elif offer["id"] == "budgeting_app":
            rationale_parts.append("A budgeting app can help you track spending and achieve your financial goals")
        
        elif offer["id"] == "subscription_management_tool":
            signals_dict = get_user_signals_dict(user_id, conn)
            sub_count = signals_dict.get('subscription_count', {}).get('value', 0) or 0
            sub_spend = signals_dict.get('subscription_monthly_spend', {}).get('value', 0) or 0
            if sub_count > 0:
                rationale_parts.append(f"You have {int(sub_count)} active subscriptions")
            if sub_spend > 0:
                rationale_parts.append(f"totaling ${sub_spend:.2f}/month")
                rationale_parts.append(f"A subscription management tool can help you track and optimize ${sub_spend * 12:.2f}/year in recurring charges")
        
        rationale = ". ".join(rationale_parts) if rationale_parts else "This offer may be relevant to your financial situation."
        rationale += " Partner offers are provided for informational purposes. We may receive compensation."
        
        return True, rationale
        
    finally:
        if close_conn:
            conn.close()


def get_eligible_offers(user_id: int, conn: Optional[sqlite3.Connection] = None) -> List[Dict]:
    """
    Get eligible partner offers for a user.
    
    Args:
        user_id: User ID
        conn: Database connection (creates new if None)
        
    Returns:
        List of eligible offer dictionaries (1-3 offers)
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        eligible_offers = []
        
        for offer in OFFER_CATALOG:
            is_eligible, rationale = check_offer_eligibility(user_id, offer, conn)
            if is_eligible:
                offer_dict = offer.copy()
                offer_dict["eligibility_rationale"] = rationale
                eligible_offers.append(offer_dict)
        
        # Select 1-3 most relevant offers
        # Prioritize by persona match and relevance
        if len(eligible_offers) > 3:
            # Get user persona for prioritization
            cursor = conn.cursor()
            cursor.execute("SELECT persona_type FROM personas WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            user_persona = result[0] if result else None
            
            # Sort by persona match first
            prioritized = []
            for offer in eligible_offers:
                preferred_personas = offer.get("eligibility_requirements", {}).get("personas", [])
                if user_persona in preferred_personas:
                    prioritized.insert(0, offer)
                else:
                    prioritized.append(offer)
            
            eligible_offers = prioritized[:3]
        
        return eligible_offers
        
    finally:
        if close_conn:
            conn.close()

