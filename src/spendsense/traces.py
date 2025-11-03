"""
Decision trace module for SpendSense MVP.
Generates and stores decision traces for auditability.
"""

import sqlite3
import json
from typing import Dict, List, Optional
from datetime import datetime
from .database import get_db_connection


def store_decision_trace(user_id: int, recommendation_id: int, step: int,
                        reasoning: str, data_cited: Optional[Dict] = None,
                        conn: Optional[sqlite3.Connection] = None) -> int:
    """
    Store a single decision trace step.
    
    Args:
        user_id: User ID
        recommendation_id: Recommendation ID
        step: Step number (1-4)
        reasoning: Human-readable reasoning
        data_cited: Dictionary of data points used (optional)
        conn: Database connection (creates new if None)
        
    Returns:
        Trace ID
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        data_cited_json = json.dumps(data_cited) if data_cited else None
        
        cursor.execute("""
            INSERT INTO decision_traces (
                user_id, recommendation_id, step, reasoning, data_cited
            ) VALUES (?, ?, ?, ?, ?)
        """, (user_id, recommendation_id, step, reasoning, data_cited_json))
        
        trace_id = cursor.lastrowid
        conn.commit()
        
        return trace_id
    finally:
        if close_conn:
            conn.close()


def generate_decision_trace(user_id: int, recommendation_id: int, persona: str,
                           recommendation: Dict, signals: Dict,
                           conn: Optional[sqlite3.Connection] = None) -> List[Dict]:
    """
    Generate complete decision trace (4 steps) for a recommendation.
    
    Steps:
    1. Signal detected → Value
    2. Persona assigned → Criteria matched
    3. Recommendation selected → Reason
    4. Rationale generated → Data cited
    
    Args:
        user_id: User ID
        recommendation_id: Recommendation ID
        persona: Persona type
        recommendation: Recommendation dictionary
        signals: Dictionary of signal types to signal data
        conn: Database connection (creates new if None)
        
    Returns:
        List of trace step dictionaries
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        trace_steps = []
        
        # Step 1: Signal detection
        if persona == "high_utilization":
            utilization = signals.get('credit_utilization_max', {}).get('value', 0) or 0
            reasoning = f"credit_utilization_max detected → {utilization:.0f}%"
            data_cited = {"signal_type": "credit_utilization_max", "value": utilization}
        elif persona == "subscription_heavy":
            count = signals.get('subscription_count', {}).get('value', 0) or 0
            reasoning = f"subscription_count detected → {int(count)} recurring merchants"
            data_cited = {"signal_type": "subscription_count", "value": count}
        else:
            reasoning = "No specific signals detected → Neutral persona"
            data_cited = {"signal_type": "none", "value": None}
        
        trace_id_1 = store_decision_trace(user_id, recommendation_id, 1, reasoning, data_cited, conn)
        trace_steps.append({
            'step': 1,
            'reasoning': reasoning,
            'data_cited': data_cited
        })
        
        # Step 2: Persona assignment
        # Get criteria from personas table
        cursor = conn.cursor()
        cursor.execute("""
            SELECT criteria_matched FROM personas WHERE user_id = ?
        """, (user_id,))
        result = cursor.fetchone()
        criteria = result[0] if result else "No criteria matched"
        
        reasoning = f"{persona} persona assigned → {criteria}"
        data_cited = {"persona": persona, "criteria": criteria}
        
        trace_id_2 = store_decision_trace(user_id, recommendation_id, 2, reasoning, data_cited, conn)
        trace_steps.append({
            'step': 2,
            'reasoning': reasoning,
            'data_cited': data_cited
        })
        
        # Step 3: Recommendation selection
        title = recommendation.get('title', 'Unknown')
        reasoning = f"'{title}' selected → Matches persona focus"
        data_cited = {
            "recommendation_id": recommendation_id,
            "title": title,
            "persona": persona
        }
        
        trace_id_3 = store_decision_trace(user_id, recommendation_id, 3, reasoning, data_cited, conn)
        trace_steps.append({
            'step': 3,
            'reasoning': reasoning,
            'data_cited': data_cited
        })
        
        # Step 4: Rationale generation
        # Extract key data points from signals
        rationale_data = {}
        if persona == "high_utilization":
            utilization = signals.get('credit_utilization_max', {}).get('value', 0) or 0
            interest = signals.get('credit_interest_charges', {}).get('value', 0) or 0
            rationale_data = {
                "utilization": utilization,
                "interest_charges": interest
            }
        elif persona == "subscription_heavy":
            count = signals.get('subscription_count', {}).get('value', 0) or 0
            monthly_spend = signals.get('subscription_monthly_spend', {}).get('value', 0) or 0
            share = signals.get('subscription_share', {}).get('value', 0) or 0
            rationale_data = {
                "subscription_count": count,
                "monthly_spend": monthly_spend,
                "share": share
            }
        
        reasoning = "Rationale generated → Cited specific user data"
        data_cited = rationale_data
        
        trace_id_4 = store_decision_trace(user_id, recommendation_id, 4, reasoning, data_cited, conn)
        trace_steps.append({
            'step': 4,
            'reasoning': reasoning,
            'data_cited': data_cited
        })
        
        return trace_steps
        
    finally:
        if close_conn:
            conn.close()


def get_decision_trace(user_id: int, recommendation_id: int,
                      conn: Optional[sqlite3.Connection] = None) -> List[Dict]:
    """
    Retrieve decision trace for a recommendation.
    
    Args:
        user_id: User ID
        recommendation_id: Recommendation ID
        conn: Database connection (creates new if None)
        
    Returns:
        List of trace step dictionaries
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT step, reasoning, data_cited
            FROM decision_traces
            WHERE user_id = ? AND recommendation_id = ?
            ORDER BY step
        """, (user_id, recommendation_id))
        
        traces = []
        for row in cursor.fetchall():
            step, reasoning, data_cited_json = row
            data_cited = json.loads(data_cited_json) if data_cited_json else {}
            traces.append({
                'step': step,
                'reasoning': reasoning,
                'data_cited': data_cited
            })
        
        return traces
    finally:
        if close_conn:
            conn.close()

