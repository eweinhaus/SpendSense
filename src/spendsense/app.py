"""
FastAPI application for SpendSense MVP.
Web interface for operator dashboard and user detail pages.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .database import get_db_connection
from .personas import get_user_signals
from .eligibility import filter_recommendations, has_consent
from .recommendations import generate_recommendations
from .partner_offers import get_eligible_offers


# Get the directory where this file is located
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Initialize FastAPI app
app = FastAPI(title="SpendSense MVP", description="Operator Dashboard")

# Setup templates and static files
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Pydantic models for request/response
class ConsentRequest(BaseModel):
    consent: bool


# Helper functions for database queries
def get_user(user_id: int) -> Optional[Dict]:
    """Get user by ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, email, consent_given, created_at
            FROM users WHERE id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            'id': row[0],
            'name': row[1],
            'email': row[2],
            'consent_given': bool(row[3]),
            'created_at': row[4]
        }
    finally:
        conn.close()


def get_all_users_with_personas() -> List[Dict]:
    """Get all users with their persona assignments and quick stats."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.name, u.email, p.persona_type
            FROM users u
            LEFT JOIN personas p ON u.id = p.user_id
            ORDER BY u.id
        """)
        
        users = []
        for row in cursor.fetchall():
            user_id, name, email, persona_type = row
            
            # Get quick stats
            stats = get_user_quick_stats(user_id)
            
            users.append({
                'id': user_id,
                'name': name,
                'email': email,
                'persona_type': persona_type or 'neutral',
                'utilization': stats.get('utilization', 'N/A'),
                'subscription_count': stats.get('subscription_count', 0)
            })
        
        return users
    finally:
        conn.close()


def get_user_quick_stats(user_id: int) -> Dict:
    """Get quick stats for dashboard display."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Get credit utilization
        cursor.execute("""
            SELECT value FROM signals
            WHERE user_id = ? AND signal_type = 'credit_utilization_max'
            LIMIT 1
        """, (user_id,))
        util_row = cursor.fetchone()
        utilization = f"{util_row[0]:.0f}%" if util_row and util_row[0] is not None else "N/A"
        
        # Get subscription count
        cursor.execute("""
            SELECT value FROM signals
            WHERE user_id = ? AND signal_type = 'subscription_count'
            LIMIT 1
        """, (user_id,))
        sub_row = cursor.fetchone()
        subscription_count = int(sub_row[0]) if sub_row and sub_row[0] is not None else 0
        
        return {
            'utilization': utilization,
            'subscription_count': subscription_count
        }
    finally:
        conn.close()


def get_user_signals_display(user_id: int) -> Dict:
    """Get formatted signals for display, grouped by window (30d and 180d)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Get all signals grouped by window
        cursor.execute("""
            SELECT signal_type, value, metadata, window
            FROM signals
            WHERE user_id = ?
            ORDER BY signal_type, window
        """, (user_id,))
        
        # Group signals by window
        signals_by_window = {'30d': {}, '180d': {}}
        
        for row in cursor.fetchall():
            signal_type, value, metadata_json, window = row
            metadata = json.loads(metadata_json) if metadata_json else {}
            
            # Extract base signal type (remove window suffix)
            base_type = signal_type
            if signal_type.endswith('_30d'):
                base_type = signal_type[:-4]
            elif signal_type.endswith('_180d'):
                base_type = signal_type[:-5]
            
            # Store in appropriate window based on window column or signal_type suffix
            target_window = None
            if window:
                target_window = window
            elif signal_type.endswith('_30d'):
                target_window = '30d'
            elif signal_type.endswith('_180d'):
                target_window = '180d'
            
            if target_window:
                signals_by_window[target_window][base_type] = {
                    'signal_type': signal_type,
                    'value': value,
                    'metadata': metadata
                }
            else:
                # Legacy signal without window - add to both
                signals_by_window['30d'][base_type] = {
                    'signal_type': signal_type,
                    'value': value,
                    'metadata': metadata
                }
                signals_by_window['180d'][base_type] = {
                    'signal_type': signal_type,
                    'value': value,
                    'metadata': metadata
                }
        
        result = {'30d': {}, '180d': {}}
        
        # Process each window
        for window in ['30d', '180d']:
            signals_dict = signals_by_window[window]
            window_result = {}
            
            # Credit signals
            util_key = 'credit_utilization_max'
            if util_key in signals_dict:
                util_signal = signals_dict[util_key]
                utilization = util_signal.get('value', 0) or 0
                
                # Get credit card details
                cursor.execute("""
                    SELECT a.account_id, a.current_balance, a."limit", cc.is_overdue, cc.apr
                    FROM accounts a
                    LEFT JOIN credit_cards cc ON a.id = cc.account_id
                    WHERE a.user_id = ? AND a.type = 'credit'
                    ORDER BY (a.current_balance / NULLIF(a."limit", 0)) DESC
                    LIMIT 1
                """, (user_id,))
                
                card_row = cursor.fetchone()
                if card_row:
                    account_id, balance, limit, is_overdue, apr = card_row
                    last_4 = account_id[-4:] if len(account_id) >= 4 else "XXXX"
                    
                    interest = signals_dict.get('credit_interest_charges', {}).get('value', 0) or 0
                    
                    window_result['credit'] = {
                        'card_name': f"Card ending in {last_4}",
                        'utilization': utilization,
                        'balance': balance or 0,
                        'limit': limit or 0,
                        'interest_charges': interest,
                        'is_overdue': bool(is_overdue) if is_overdue is not None else False,
                        'apr': apr
                    }
            
            # Subscription signals
            if 'subscription_count' in signals_dict:
                count_signal = signals_dict['subscription_count']
                count = count_signal.get('value', 0) or 0
                
                if count > 0:
                    monthly_spend = signals_dict.get('subscription_monthly_spend', {}).get('value', 0) or 0
                    share = signals_dict.get('subscription_share', {}).get('value', 0) or 0
                    
                    # Get merchant names
                    merchants = []
                    if 'subscription_merchants' in signals_dict:
                        metadata = signals_dict['subscription_merchants'].get('metadata', {})
                        merchants = metadata.get('merchants', [])
                    
                    window_result['subscription'] = {
                        'count': int(count),
                        'merchants': merchants,
                        'monthly_spend': monthly_spend,
                        'share': share
                    }
            
            # Savings signals
            savings_data = {}
            if 'savings_net_inflow' in signals_dict:
                savings_data['net_inflow'] = signals_dict['savings_net_inflow'].get('value', 0) or 0
            if 'savings_growth_rate' in signals_dict:
                savings_data['growth_rate'] = signals_dict['savings_growth_rate'].get('value', 0) or 0
            if 'emergency_fund_coverage' in signals_dict:
                savings_data['emergency_fund_coverage'] = signals_dict['emergency_fund_coverage'].get('value', 0) or 0
            
            if savings_data:
                window_result['savings'] = savings_data
            
            # Income signals
            income_data = {}
            if 'income_frequency' in signals_dict:
                metadata = signals_dict['income_frequency'].get('metadata', {})
                income_data['frequency'] = metadata.get('frequency', 'irregular')
            if 'income_variability' in signals_dict:
                income_data['variability'] = signals_dict['income_variability'].get('value', 0) or 0
            if 'cash_flow_buffer' in signals_dict:
                income_data['cash_flow_buffer'] = signals_dict['cash_flow_buffer'].get('value', 0) or 0
            if 'median_pay_gap' in signals_dict:
                income_data['median_pay_gap'] = signals_dict['median_pay_gap'].get('value', 0) or 0
            
            if income_data:
                window_result['income'] = income_data
            
            result[window] = window_result
        
        return result
        
    finally:
        conn.close()


def get_user_persona_display(user_id: int) -> Optional[Dict]:
    """Get persona assignment with criteria."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT persona_type, criteria_matched, assigned_at
            FROM personas WHERE user_id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            'persona_type': row[0],
            'criteria_matched': row[1],
            'assigned_at': row[2]
        }
    finally:
        conn.close()


def get_recommendations_for_user(user_id: int) -> List[Dict]:
    """Get all recommendations for a user with eligibility filtering and consent check."""
    # Check consent first - return empty list if no consent
    if not has_consent(user_id):
        return []
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, content, rationale, persona_matched, created_at
            FROM recommendations
            WHERE user_id = ?
            ORDER BY created_at
        """, (user_id,))
        
        recommendations = []
        for row in cursor.fetchall():
            rec_id, title, content, rationale, persona_matched, created_at = row
            recommendations.append({
                'id': rec_id,
                'title': title,
                'content': content,
                'rationale': rationale,
                'persona_matched': persona_matched,
                'created_at': created_at
            })
        
        # Filter by eligibility
        eligible_recs = filter_recommendations(user_id, recommendations, conn)
        
        return eligible_recs
    finally:
        conn.close()


def get_decision_traces_for_user(user_id: int) -> Dict[int, List[Dict]]:
    """Get all decision traces for a user's recommendations."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT recommendation_id, step, reasoning, data_cited
            FROM decision_traces
            WHERE user_id = ?
            ORDER BY recommendation_id, step
        """, (user_id,))
        
        traces_by_rec = {}
        for row in cursor.fetchall():
            rec_id, step, reasoning, data_cited_json = row
            data_cited = json.loads(data_cited_json) if data_cited_json else {}
            
            if rec_id not in traces_by_rec:
                traces_by_rec[rec_id] = []
            
            traces_by_rec[rec_id].append({
                'step': step,
                'reasoning': reasoning,
                'data_cited': data_cited
            })
        
        return traces_by_rec
    finally:
        conn.close()


def update_consent(user_id: int, consent: bool) -> bool:
    """Update user consent status."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET consent_given = ? WHERE id = ?
        """, (1 if consent else 0, user_id))
        
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def refresh_recommendations_for_user(user_id: int, consent_enabled: bool) -> None:
    """Regenerate recommendations based on consent status."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM recommendations WHERE user_id = ?", (user_id,))
        rec_ids = [row[0] for row in cursor.fetchall()]
        if rec_ids:
            placeholders = ",".join(["?"] * len(rec_ids))
            cursor.execute(
                f"DELETE FROM decision_traces WHERE recommendation_id IN ({placeholders})",
                rec_ids,
            )
            cursor.execute(
                f"DELETE FROM recommendations WHERE id IN ({placeholders})",
                rec_ids,
            )
            conn.commit()
        if consent_enabled:
            generate_recommendations(user_id, conn)
            conn.commit()
    finally:
        conn.close()


# API Endpoints
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    """Dashboard page showing all users."""
    try:
        users = get_all_users_with_personas()
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "users": users
        })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_code": 500,
            "error_message": f"Error loading dashboard: {str(e)}"
        })


@app.get("/user/{user_id}", response_class=HTMLResponse)
def user_detail(request: Request, user_id: int):
    """User detail page with signals, persona, recommendations."""
    try:
        # Get user
        user = get_user(user_id)
        if not user:
            response = templates.TemplateResponse("error.html", {
                "request": request,
                "error_code": 404,
                "error_message": f"User {user_id} not found"
            })
            response.status_code = 404
            return response
        
        # Get signals
        signals = get_user_signals_display(user_id)
        
        # Get persona
        persona = get_user_persona_display(user_id)
        
        # Get recommendations (with eligibility filtering)
        recommendations = get_recommendations_for_user(user_id)
        
        # Get decision traces
        traces = get_decision_traces_for_user(user_id)
        
        # Get partner offers (only if user has consent)
        partner_offers = []
        if has_consent(user_id):
            partner_offers = get_eligible_offers(user_id)
        
        return templates.TemplateResponse("user_detail.html", {
            "request": request,
            "user": user,
            "signals": signals,
            "persona": persona,
            "recommendations": recommendations,
            "traces": traces,
            "partner_offers": partner_offers
        })
    except HTTPException:
        raise
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_code": 500,
            "error_message": f"Error loading user details: {str(e)}"
        })


@app.post("/consent/{user_id}")
def toggle_consent(user_id: int, consent_data: ConsentRequest):
    """Toggle consent status for a user."""
    try:
        # Verify user exists
        user = get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update consent
        success = update_consent(user_id, consent_data.consent)
        
        if success:
            refresh_recommendations_for_user(user_id, consent_data.consent)
            return {"success": True, "consent_given": consent_data.consent}
        else:
            return {"success": False, "error": "Failed to update consent"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating consent: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

