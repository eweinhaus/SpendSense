"""
FastAPI application for SpendSense MVP.
Web interface for operator dashboard and user detail pages.
"""

import sqlite3
import json
import os
from pathlib import Path
from typing import Optional, Dict, List
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
from .database import get_db_connection, init_database
from .personas import get_user_signals
from .eligibility import filter_recommendations, has_consent
from .recommendations import generate_recommendations
from .partner_offers import get_eligible_offers
from .compliance import (
    log_consent_change, operator_auth, get_consent_audit_log,
    get_compliance_metrics, get_recent_compliance_issues,
    check_recommendation_compliance, get_all_recommendations_with_compliance,
    get_recommendation_compliance_detail, generate_consent_audit_report,
    generate_recommendation_compliance_report, generate_compliance_summary_report
)
from .auth import (
    get_current_user, login_user, logout_user, get_session_secret_key,
    get_user_by_email, get_user_by_id
)
from .user_data import (
    get_user_persona_summary, get_user_signal_summary, get_user_account_summary,
    calculate_quick_stats, get_user_transaction_insights
)
from .icon_helper import render_icon, render_icon_safe


# Get the directory where this file is located
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Initialize FastAPI app
app = FastAPI(title="SpendSense MVP", description="Operator Dashboard")

# Add session middleware for authentication (Phase 8A)
app.add_middleware(
    SessionMiddleware,
    secret_key=get_session_secret_key(),
    max_age=86400,  # 24 hours
    same_site="lax",
    https_only=False  # Set to True in production with HTTPS
)

# Setup templates and static files
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Add custom Jinja2 filter for JSON formatting
def tojsonpretty(value):
    """Format JSON data as pretty-printed string."""
    if value is None:
        return "{}"
    return json.dumps(value, indent=2, default=str)

# Register filter on the Jinja2 environment
# Register it immediately and also in startup event for safety
templates.env.filters['tojsonpretty'] = tojsonpretty

# Add icon helper functions to template globals
templates.env.globals['render_icon'] = render_icon
templates.env.globals['icon'] = render_icon_safe

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    try:
        # Initialize database synchronously (FastAPI handles this)
        init_database()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️  Warning: Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        print("   Application will continue, but database operations may fail")
    
    # Ensure filter is registered (safety check)
    templates.env.filters['tojsonpretty'] = tojsonpretty
    
    # Ensure icon helpers are registered
    templates.env.globals['render_icon'] = render_icon
    templates.env.globals['icon'] = render_icon_safe


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


def get_all_users_with_personas(
    search: Optional[str] = None, 
    persona_filter: Optional[str] = None,
    utilization_min: Optional[int] = None,
    utilization_max: Optional[int] = None,
    subscription_min: Optional[int] = None,
    subscription_max: Optional[int] = None
) -> List[Dict]:
    """Get all users with their persona assignments and quick stats.
    
    Args:
        search: Optional search term to filter by name (case-insensitive)
        persona_filter: Optional persona type to filter by
        utilization_min: Optional minimum utilization percentage (0-100)
        utilization_max: Optional maximum utilization percentage (0-100)
        subscription_min: Optional minimum subscription count
        subscription_max: Optional maximum subscription count
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Build query with optional filters
        query = """
            SELECT DISTINCT u.id, u.name, u.email, u.consent_given, p.persona_type
            FROM users u
            LEFT JOIN personas p ON u.id = p.user_id
            LEFT JOIN signals util_sig ON u.id = util_sig.user_id AND util_sig.signal_type = 'credit_utilization_max'
            LEFT JOIN signals sub_sig ON u.id = sub_sig.user_id AND sub_sig.signal_type = 'subscription_count'
            WHERE 1=1
        """
        params = []
        
        if search:
            query += " AND (u.name LIKE ? OR u.email LIKE ?)"
            search_term = f"%{search}%"
            params.extend([search_term, search_term])
        
        if persona_filter:
            query += " AND (p.persona_type = ? OR (p.persona_type IS NULL AND ? = 'neutral'))"
            params.extend([persona_filter, persona_filter])
        
        if utilization_min is not None:
            query += " AND (util_sig.value >= ? OR util_sig.value IS NULL)"
            params.append(float(utilization_min))
        
        if utilization_max is not None:
            query += " AND (util_sig.value <= ? OR util_sig.value IS NULL)"
            params.append(float(utilization_max))
        
        if subscription_min is not None:
            query += " AND (CAST(sub_sig.value AS INTEGER) >= ? OR sub_sig.value IS NULL)"
            params.append(subscription_min)
        
        if subscription_max is not None:
            query += " AND (CAST(sub_sig.value AS INTEGER) <= ? OR sub_sig.value IS NULL)"
            params.append(subscription_max)
        
        query += " ORDER BY u.id"
        
        cursor.execute(query, params)
        
        users = []
        for row in cursor.fetchall():
            user_id, name, email, consent_given, persona_type = row
            
            # Get quick stats
            stats = get_user_quick_stats(user_id)
            
            users.append({
                'id': user_id,
                'name': name,
                'email': email,
                'consent_given': bool(consent_given),
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
                
                # Get credit card details from signal metadata (which includes historical balance)
                metadata = util_signal.get('metadata', {})
                cards = metadata.get('cards', [])
                
                if cards:
                    # Use the card with highest utilization (first in list should be sorted)
                    card_data = cards[0] if cards else {}
                    account_id = card_data.get('account_id', '')
                    balance = card_data.get('balance', 0)  # Historical balance from signal
                    limit = card_data.get('limit', 0)
                    is_overdue = card_data.get('is_overdue', False)
                    
                    last_4 = account_id[-4:] if len(account_id) >= 4 else "XXXX"
                    
                    # Get APR from database
                    cursor.execute("""
                        SELECT cc.apr
                        FROM accounts a
                        LEFT JOIN credit_cards cc ON a.id = cc.account_id
                        WHERE a.account_id = ? AND a.user_id = ?
                        LIMIT 1
                    """, (account_id, user_id))
                    
                    apr_row = cursor.fetchone()
                    apr = apr_row[0] if apr_row and apr_row[0] else None
                    
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
                else:
                    # Fallback to current balance if no card data in metadata
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
    """Get persona assignment with criteria and window-based signal information."""
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
        
        persona_type, criteria_matched, assigned_at = row
        
        # Get signals by window to show which signals/windows contributed to assignment
        cursor.execute("""
            SELECT signal_type, window
            FROM signals
            WHERE user_id = ?
            ORDER BY window, signal_type
        """, (user_id,))
        
        signal_windows = {'30d': set(), '180d': set()}
        for signal_row in cursor.fetchall():
            signal_type, window = signal_row
            # Extract base signal type (remove window suffix if present)
            base_type = signal_type
            if signal_type.endswith('_30d'):
                base_type = signal_type[:-4]
                window = '30d'
            elif signal_type.endswith('_180d'):
                base_type = signal_type[:-5]
                window = '180d'
            
            # Determine which window this signal belongs to
            target_window = window or '30d'  # Default to 30d if no window specified
            
            # Only include relevant signals based on persona type
            if persona_type == 'high_utilization':
                if 'credit_utilization' in base_type or 'credit_interest' in base_type or 'credit_overdue' in base_type:
                    signal_windows[target_window].add(base_type)
            elif persona_type == 'variable_income_budgeter':
                if 'income' in base_type or 'cash_flow' in base_type or 'median_pay' in base_type:
                    signal_windows[target_window].add(base_type)
            elif persona_type == 'savings_builder':
                if 'savings' in base_type or 'credit_utilization' in base_type:
                    signal_windows[target_window].add(base_type)
            elif persona_type == 'financial_newcomer':
                if 'credit_utilization' in base_type:
                    signal_windows[target_window].add(base_type)
            elif persona_type == 'subscription_heavy':
                if 'subscription' in base_type:
                    signal_windows[target_window].add(base_type)
        
        # Convert sets to sorted lists and remove empty windows
        signal_windows = {k: sorted(list(v)) for k, v in signal_windows.items() if v}
        
        return {
            'persona_type': persona_type,
            'criteria_matched': criteria_matched,
            'assigned_at': assigned_at,
            'signal_windows': signal_windows if signal_windows else None
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
        # Get current consent status before updating (for audit log)
        cursor = conn.cursor()
        cursor.execute("SELECT consent_given FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        previous_status = bool(result[0]) if result else False
        
        # Log consent change before updating
        action = 'granted' if consent else 'revoked'
        log_consent_change(user_id, action, 'operator', previous_status, conn)
        
        # Update consent status
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
def dashboard(
    request: Request, 
    search: Optional[str] = None, 
    persona_filter: Optional[str] = None,
    utilization_min: Optional[str] = None,
    utilization_max: Optional[str] = None,
    subscription_min: Optional[str] = None,
    subscription_max: Optional[str] = None
):
    """Dashboard page showing all users with enhanced stats.
    
    Query parameters:
        search: Optional search term to filter users by name
        persona_filter: Optional persona type to filter by
        utilization_min: Optional minimum utilization percentage (as string, will be converted to int)
        utilization_max: Optional maximum utilization percentage (as string, will be converted to int)
        subscription_min: Optional minimum subscription count (as string, will be converted to int)
        subscription_max: Optional maximum subscription count (as string, will be converted to int)
    """
    try:
        # Convert string parameters to int or None
        util_min = int(utilization_min) if utilization_min and utilization_min.strip() else None
        util_max = int(utilization_max) if utilization_max and utilization_max.strip() else None
        sub_min = int(subscription_min) if subscription_min and subscription_min.strip() else None
        sub_max = int(subscription_max) if subscription_max and subscription_max.strip() else None
        
        users = get_all_users_with_personas(
            search=search, 
            persona_filter=persona_filter,
            utilization_min=util_min,
            utilization_max=util_max,
            subscription_min=sub_min,
            subscription_max=sub_max
        )
        
        # Calculate quick stats for dashboard (always use all users, not filtered)
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Total users
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            # Personas breakdown
            cursor.execute("""
                SELECT persona_type, COUNT(*) as count
                FROM personas
                GROUP BY persona_type
            """)
            persona_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Consent stats
            cursor.execute("SELECT COUNT(*) FROM users WHERE consent_given = 1")
            users_with_consent = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE consent_given = 0")
            users_without_consent = cursor.fetchone()[0]
            
            # Recent activity (get last 5 users by ID, without filters)
            all_users = get_all_users_with_personas()
            recent_users = all_users[-5:] if len(all_users) > 5 else all_users
            
            stats = {
                'total_users': total_users,
                'persona_counts': persona_counts,
                'users_with_consent': users_with_consent,
                'users_without_consent': users_without_consent,
                'recent_users': recent_users
            }
        finally:
            conn.close()
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "users": users,
            "stats": stats,
            "current_search": search or "",
            "current_persona_filter": persona_filter or "",
            "current_utilization_min": util_min,
            "current_utilization_max": util_max,
            "current_subscription_min": sub_min,
            "current_subscription_max": sub_max
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
        
        # Ensure filter is registered (safety check before rendering)
        if 'tojsonpretty' not in templates.env.filters:
            templates.env.filters['tojsonpretty'] = tojsonpretty
        
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


# ============================================================================
# Phase 8B: Compliance & Audit Interface Routes (Operator Only)
# ============================================================================

@app.get("/compliance/consent-audit", response_class=HTMLResponse, dependencies=[Depends(operator_auth)])
def consent_audit_log(request: Request, 
                     user_id: Optional[int] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     action: Optional[str] = None):
    """Display consent audit log (operator only)."""
    try:
        audit_log = get_consent_audit_log(user_id, start_date, end_date, action)
        
        # Get all users for filter dropdown
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM users ORDER BY name")
            users = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
        finally:
            conn.close()
        
        return templates.TemplateResponse("compliance/consent_audit.html", {
            "request": request,
            "audit_log": audit_log,
            "users": users,
            "filters": {
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date,
                "action": action
            }
        })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_code": 500,
            "error_message": f"Error loading audit log: {str(e)}"
        })


@app.get("/compliance/consent-audit/{user_id}", response_class=HTMLResponse, dependencies=[Depends(operator_auth)])
def consent_audit_user(request: Request, user_id: int):
    """Display user-specific consent history (operator only)."""
    try:
        audit_log = get_consent_audit_log(user_id=user_id)
        
        # Get user info
        user = get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return templates.TemplateResponse("compliance/consent_audit.html", {
            "request": request,
            "audit_log": audit_log,
            "user": user,
            "filters": {"user_id": user_id}
        })
    except HTTPException:
        raise
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_code": 500,
            "error_message": f"Error loading user audit log: {str(e)}"
        })


@app.get("/compliance/consent-audit/export", dependencies=[Depends(operator_auth)])
def export_consent_audit(request: Request, format: str = "csv"):
    """Export consent audit log (CSV/JSON, operator only)."""
    from datetime import datetime
    import csv
    import io
    
    try:
        audit_log = get_consent_audit_log()
        
        if format.lower() == "json":
            return JSONResponse({
                "report_date": datetime.now().isoformat(),
                "total_records": len(audit_log),
                "data": audit_log
            })
        else:  # CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "ID", "User ID", "User Name", "Action", "Timestamp", 
                "Changed By", "Previous Status"
            ])
            
            # Write data
            for entry in audit_log:
                writer.writerow([
                    entry['id'],
                    entry['user_id'],
                    entry['user_name'],
                    entry['action'],
                    entry['timestamp'],
                    entry['changed_by'],
                    entry['previous_status']
                ])
            
            output.seek(0)
            from fastapi.responses import Response
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=consent_audit_{datetime.now().strftime('%Y%m%d')}.csv"
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting audit log: {str(e)}")


@app.get("/compliance/dashboard", response_class=HTMLResponse, dependencies=[Depends(operator_auth)])
def compliance_dashboard(request: Request):
    """Display compliance dashboard (operator only)."""
    try:
        metrics = get_compliance_metrics()
        recent_issues = get_recent_compliance_issues()
        
        return templates.TemplateResponse("compliance/dashboard.html", {
            "request": request,
            "metrics": metrics,
            "recent_issues": recent_issues
        })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_code": 500,
            "error_message": f"Error loading compliance dashboard: {str(e)}"
        })


@app.get("/compliance/recommendations", response_class=HTMLResponse, dependencies=[Depends(operator_auth)])
def recommendation_compliance(request: Request,
                             status: Optional[str] = None,
                             user_id: Optional[int] = None,
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None):
    """Display recommendation compliance review (operator only)."""
    try:
        recommendations = get_all_recommendations_with_compliance(
            status=status, user_id=user_id, start_date=start_date, end_date=end_date
        )
        
        # Get all users for filter dropdown
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM users ORDER BY name")
            users = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
        finally:
            conn.close()
        
        return templates.TemplateResponse("compliance/recommendation_compliance.html", {
            "request": request,
            "recommendations": recommendations,
            "users": users,
            "filters": {
                "status": status,
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date
            }
        })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_code": 500,
            "error_message": f"Error loading compliance review: {str(e)}"
        })


@app.get("/compliance/recommendations/{id}", response_class=HTMLResponse, dependencies=[Depends(operator_auth)])
def recommendation_compliance_detail(request: Request, id: int):
    """Display detailed compliance report for a recommendation (operator only)."""
    try:
        detail = get_recommendation_compliance_detail(id)
        
        if not detail:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        
        return templates.TemplateResponse("compliance/recommendation_compliance_detail.html", {
            "request": request,
            "detail": detail
        })
    except HTTPException:
        raise
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_code": 500,
            "error_message": f"Error loading compliance detail: {str(e)}"
        })


@app.get("/compliance/recommendations/export", dependencies=[Depends(operator_auth)])
def export_recommendation_compliance(request: Request, format: str = "csv"):
    """Export recommendation compliance report (CSV/JSON, operator only)."""
    from datetime import datetime
    import csv
    import io
    
    try:
        recommendations = get_all_recommendations_with_compliance()
        
        if format.lower() == "json":
            return JSONResponse({
                "report_date": datetime.now().isoformat(),
                "total_records": len(recommendations),
                "data": recommendations
            })
        else:  # CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "ID", "User ID", "User Name", "Title", "Created At",
                "Compliant", "Active Consent", "Eligibility Check",
                "Required Disclaimer", "Complete Trace", "Rationale Cites Data"
            ])
            
            # Write data
            for rec in recommendations:
                checks = rec.get('checks', {})
                writer.writerow([
                    rec['id'],
                    rec['user_id'],
                    rec['user_name'],
                    rec['title'],
                    rec['created_at'],
                    rec['compliant'],
                    checks.get('active_consent', False),
                    checks.get('eligibility_check', False),
                    checks.get('required_disclaimer', False),
                    checks.get('complete_trace', False),
                    checks.get('rationale_cites_data', False)
                ])
            
            output.seek(0)
            from fastapi.responses import Response
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=recommendation_compliance_{datetime.now().strftime('%Y%m%d')}.csv"
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting compliance report: {str(e)}")


@app.get("/compliance/reports/consent", dependencies=[Depends(operator_auth)])
def export_consent_report(request: Request, format: str = "csv"):
    """Generate consent audit report (CSV/JSON, operator only)."""
    from fastapi.responses import Response
    
    try:
        report = generate_consent_audit_report(format=format)
        
        if report['format'] == 'json':
            return JSONResponse(report)
        else:  # CSV
            from datetime import datetime
            return Response(
                content=report['data'],
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=consent_audit_{datetime.now().strftime('%Y%m%d')}.csv"
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")


@app.get("/compliance/reports/recommendations", dependencies=[Depends(operator_auth)])
def export_recommendation_compliance_report_route(request: Request, format: str = "csv"):
    """Generate recommendation compliance report (CSV/JSON, operator only)."""
    from fastapi.responses import Response
    
    try:
        report = generate_recommendation_compliance_report(format=format)
        
        if report['format'] == 'json':
            return JSONResponse(report)
        else:  # CSV
            from datetime import datetime
            return Response(
                content=report['data'],
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=recommendation_compliance_{datetime.now().strftime('%Y%m%d')}.csv"
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")


@app.get("/compliance/reports/summary", dependencies=[Depends(operator_auth)])
def export_compliance_summary(request: Request, format: str = "markdown"):
    """Generate compliance summary report (Markdown/JSON, operator only)."""
    from fastapi.responses import Response
    
    try:
        report = generate_compliance_summary_report(format=format)
        
        if report['format'] == 'json':
            return JSONResponse(report)
        else:  # Markdown
            from datetime import datetime
            return Response(
                content=report['data'],
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f"attachment; filename=compliance_summary_{datetime.now().strftime('%Y%m%d')}.md"
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")


# ============================================================================
# Phase 8A: End-User Authentication Routes
# ============================================================================

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Display login page."""
    # If already logged in, redirect to dashboard
    user_id = request.session.get("user_id")
    if user_id:
        return RedirectResponse(url="/portal/dashboard", status_code=303)
    
    return templates.TemplateResponse("user/login.html", {
        "request": request
    })


@app.post("/login", response_class=HTMLResponse)
async def login(request: Request):
    """Handle login form submission."""
    # If already logged in, redirect to dashboard
    user_id = request.session.get("user_id")
    if user_id:
        return RedirectResponse(url="/portal/dashboard", status_code=303)
    
    form_data = await request.form()
    identifier = form_data.get("identifier", "").strip()
    
    if not identifier:
        return templates.TemplateResponse("user/login.html", {
            "request": request,
            "error_message": "Please enter an email or user ID"
        })
    
    # Try to find user by email or ID
    user = None
    
    # Try as user ID first (integer)
    try:
        user_id = int(identifier)
        user = get_user_by_id(user_id)
    except ValueError:
        # Not an integer, try as email
        user = get_user_by_email(identifier)
    
    if not user:
        return templates.TemplateResponse("user/login.html", {
            "request": request,
            "error_message": f"User not found: {identifier}"
        })
    
    # Login successful - set session
    login_user(request, user["id"])
    
    # Redirect to user dashboard
    return RedirectResponse(url="/portal/dashboard", status_code=303)


@app.post("/logout")
def logout(request: Request):
    """Handle logout."""
    logout_user(request)
    return RedirectResponse(url="/login", status_code=303)


# ============================================================================
# Phase 8A: Protected User Routes (require authentication)
# ============================================================================

@app.get("/portal/dashboard", response_class=HTMLResponse)
def user_dashboard(request: Request, user: Dict = Depends(get_current_user)):
    """User's personalized dashboard."""
    try:
        user_id = user["id"]
        
        # Get persona
        persona = get_user_persona_summary(user_id)
        
        # Get signal summary
        signals = get_user_signal_summary(user_id)
        
        # Get account summary
        accounts = get_user_account_summary(user_id)
        
        # Calculate quick stats
        stats = calculate_quick_stats(user_id)
        
        # Get top recommendations (only if consent granted)
        recommendations = []
        if user.get("consent_given"):
            recommendations = get_recommendations_for_user(user_id)
            # Limit to top 5 for preview
            recommendations = recommendations[:5]
        
        return templates.TemplateResponse("user/dashboard.html", {
            "request": request,
            "user": user,
            "persona": persona,
            "signals": signals,
            "accounts": accounts,
            "stats": stats,
            "recommendations": recommendations
        })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_code": 500,
            "error_message": f"Error loading dashboard: {str(e)}"
        })


@app.get("/portal/recommendations", response_class=HTMLResponse)
def user_recommendations(request: Request, user: Dict = Depends(get_current_user)):
    """User's recommendation feed."""
    try:
        user_id = user["id"]
        
        # Check consent - redirect if no consent
        if not user.get("consent_given"):
            return templates.TemplateResponse("user/recommendations.html", {
                "request": request,
                "user": user,
                "no_consent": True,
                "recommendations": [],
                "partner_offers": []
            })
        
        # Get all recommendations
        recommendations = get_recommendations_for_user(user_id)
        
        # Get partner offers
        partner_offers = get_eligible_offers(user_id)
        # Limit to top 3
        partner_offers = partner_offers[:3]
        
        return templates.TemplateResponse("user/recommendations.html", {
            "request": request,
            "user": user,
            "no_consent": False,
            "recommendations": recommendations,
            "partner_offers": partner_offers
        })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_code": 500,
            "error_message": f"Error loading recommendations: {str(e)}"
        })


@app.post("/portal/recommendations/{rec_id}/feedback")
async def recommendation_feedback(rec_id: int, request: Request, user: Dict = Depends(get_current_user)):
    """Handle user feedback on recommendations."""
    try:
        form_data = await request.form()
        feedback_type = form_data.get("feedback_type", "")
        comment = form_data.get("comment", "")
        
        # For MVP, just return success
        # In production, this would store feedback in database
        return JSONResponse({
            "success": True,
            "message": "Thank you for your feedback!"
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.get("/portal/profile", response_class=HTMLResponse)
def user_profile(request: Request, user: Dict = Depends(get_current_user), window: str = "30d"):
    """User's detailed financial profile."""
    try:
        user_id = user["id"]
        
        # Validate window parameter
        if window not in ["30d", "180d"]:
            window = "30d"
        
        # Get signals for specified window
        signals_display = get_user_signals_display(user_id)
        signals = signals_display.get(window, {})
        
        # Get account summary
        accounts = get_user_account_summary(user_id)
        
        # Get transaction insights
        days = 30 if window == "30d" else 180
        transaction_insights = get_user_transaction_insights(user_id, days=days)
        
        return templates.TemplateResponse("user/profile.html", {
            "request": request,
            "user": user,
            "window": window,
            "signals": signals,
            "accounts": accounts,
            "transaction_insights": transaction_insights
        })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_code": 500,
            "error_message": f"Error loading profile: {str(e)}"
        })


@app.get("/portal/consent", response_class=HTMLResponse)
def user_consent_page(request: Request, user: Dict = Depends(get_current_user)):
    """Consent management page."""
    try:
        return templates.TemplateResponse("user/consent.html", {
            "request": request,
            "user": user
        })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_code": 500,
            "error_message": f"Error loading consent page: {str(e)}"
        })


@app.post("/portal/consent", response_class=HTMLResponse)
async def user_consent_update(request: Request, user: Dict = Depends(get_current_user)):
    """Update user consent status."""
    try:
        user_id = user["id"]
        form_data = await request.form()
        consent = form_data.get("consent") == "true"
        
        # Update consent
        success = update_consent(user_id, consent)
        
        if success:
            # Regenerate recommendations if consent granted, remove if revoked
            refresh_recommendations_for_user(user_id, consent)
            
            # Redirect back to consent page with success message
            return RedirectResponse(url="/portal/consent?success=1", status_code=303)
        else:
            return templates.TemplateResponse("user/consent.html", {
                "request": request,
                "user": user,
                "error_message": "Failed to update consent"
            })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_code": 500,
            "error_message": f"Error updating consent: {str(e)}"
        })


# ============================================================================
# Phase 8A: Calculator Routes
# ============================================================================

@app.get("/portal/calculators", response_class=HTMLResponse)
def calculators_hub(request: Request, user: Dict = Depends(get_current_user)):
    """Calculator hub page."""
    try:
        return templates.TemplateResponse("user/calculators.html", {
            "request": request,
            "user": user
        })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_code": 500,
            "error_message": f"Error loading calculators: {str(e)}"
        })


def calculate_emergency_fund(monthly_expenses: float, months: int = 6) -> Dict:
    """Calculate emergency fund target."""
    if monthly_expenses <= 0:
        return {"error": "Monthly expenses must be greater than 0"}
    
    target_3mo = monthly_expenses * 3
    target_6mo = monthly_expenses * 6
    target = monthly_expenses * months
    
    return {
        "target_3mo": target_3mo,
        "target_6mo": target_6mo,
        "target": target,
        "months": months,
        "monthly_expenses": monthly_expenses
    }


def calculate_debt_paydown(balance: float, apr: float, payment: float) -> Dict:
    """Calculate debt paydown schedule."""
    if balance <= 0:
        return {"error": "Balance must be greater than 0"}
    if apr < 0:
        return {"error": "APR must be non-negative"}
    if payment <= 0:
        return {"error": "Payment must be greater than 0"}
    
    monthly_rate = apr / 100 / 12
    if monthly_rate <= 0:
        # No interest
        months = int(balance / payment) + (1 if balance % payment > 0 else 0)
        total_interest = 0
    else:
        # Amortization formula: months = -log(1 - (balance * rate) / payment) / log(1 + rate)
        import math
        if payment <= balance * monthly_rate:
            return {"error": "Payment is too low to cover interest"}
        
        try:
            months = -math.log(1 - (balance * monthly_rate) / payment) / math.log(1 + monthly_rate)
            months = int(math.ceil(months))
            total_interest = (months * payment) - balance
        except (ValueError, ZeroDivisionError):
            return {"error": "Invalid calculation parameters"}
    
    return {
        "months": months,
        "total_interest": total_interest,
        "total_paid": balance + total_interest,
        "balance": balance,
        "apr": apr,
        "payment": payment
    }


def calculate_savings_goal(goal_amount: float, target_date: str, current_savings: float = 0, interest_rate: float = 0) -> Dict:
    """Calculate monthly savings needed for goal."""
    from datetime import datetime, date
    
    if goal_amount <= 0:
        return {"error": "Goal amount must be greater than 0"}
    if current_savings < 0:
        return {"error": "Current savings cannot be negative"}
    
    try:
        target = datetime.strptime(target_date, "%Y-%m-%d").date()
        today = date.today()
        months_remaining = (target.year - today.year) * 12 + (target.month - today.month)
        
        if months_remaining <= 0:
            return {"error": "Target date must be in the future"}
        
        remaining = goal_amount - current_savings
        if remaining <= 0:
            return {
                "months": 0,
                "monthly_savings": 0,
                "total_contributions": 0,
                "interest_earned": 0,
                "message": "You already have enough savings!"
            }
        
        # Simple calculation (ignoring compounding for simplicity)
        monthly_savings = remaining / months_remaining
        total_contributions = monthly_savings * months_remaining
        interest_earned = 0  # Simplified - would need compound interest calculation
        
        return {
            "months": months_remaining,
            "monthly_savings": monthly_savings,
            "total_contributions": total_contributions,
            "interest_earned": interest_earned,
            "goal_amount": goal_amount,
            "current_savings": current_savings,
            "remaining": remaining
        }
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}


@app.get("/portal/calculators/emergency-fund", response_class=HTMLResponse)
def emergency_fund_calculator(request: Request, user: Dict = Depends(get_current_user)):
    """Emergency fund calculator page."""
    try:
        # Pre-fill with user's monthly expenses if available
        stats = calculate_quick_stats(user["id"])
        prefill_expenses = stats.get("monthly_expenses", 0)
        
        return templates.TemplateResponse("user/calculator_emergency_fund.html", {
            "request": request,
            "user": user,
            "prefill_expenses": prefill_expenses
        })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_code": 500,
            "error_message": f"Error loading calculator: {str(e)}"
        })


@app.post("/portal/calculators/emergency-fund", response_class=HTMLResponse)
async def emergency_fund_calculate(request: Request, user: Dict = Depends(get_current_user)):
    """Calculate emergency fund results."""
    try:
        form_data = await request.form()
        monthly_expenses = float(form_data.get("monthly_expenses", 0))
        months = int(form_data.get("months", 6))
        
        if months < 3 or months > 6:
            months = 6
        
        result = calculate_emergency_fund(monthly_expenses, months)
        
        return templates.TemplateResponse("user/calculator_emergency_fund.html", {
            "request": request,
            "user": user,
            "prefill_expenses": monthly_expenses,
            "result": result
        })
    except (ValueError, TypeError) as e:
        return templates.TemplateResponse("user/calculator_emergency_fund.html", {
            "request": request,
            "user": user,
            "error": "Invalid input. Please enter valid numbers."
        })


@app.get("/portal/calculators/debt-paydown", response_class=HTMLResponse)
def debt_paydown_calculator(request: Request, user: Dict = Depends(get_current_user)):
    """Debt paydown calculator page."""
    try:
        # Pre-fill with user's credit card data if available
        conn = get_db_connection()
        prefill_balance = 0
        prefill_apr = 0
        prefill_payment = 0
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.current_balance, cc.apr, cc.minimum_payment_amount
                FROM accounts a
                LEFT JOIN credit_cards cc ON a.id = cc.account_id
                WHERE a.user_id = ? AND a.type = 'credit'
                ORDER BY a.current_balance DESC
                LIMIT 1
            """, (user["id"],))
            
            row = cursor.fetchone()
            if row:
                prefill_balance = row[0] or 0
                prefill_apr = row[1] or 0
                prefill_payment = row[2] or 0
        finally:
            conn.close()
        
        return templates.TemplateResponse("user/calculator_debt_paydown.html", {
            "request": request,
            "user": user,
            "prefill_balance": prefill_balance,
            "prefill_apr": prefill_apr,
            "prefill_payment": prefill_payment
        })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_code": 500,
            "error_message": f"Error loading calculator: {str(e)}"
        })


@app.post("/portal/calculators/debt-paydown", response_class=HTMLResponse)
async def debt_paydown_calculate(request: Request, user: Dict = Depends(get_current_user)):
    """Calculate debt paydown results."""
    try:
        form_data = await request.form()
        balance = float(form_data.get("balance", 0))
        apr = float(form_data.get("apr", 0))
        payment = float(form_data.get("payment", 0))
        
        result = calculate_debt_paydown(balance, apr, payment)
        
        return templates.TemplateResponse("user/calculator_debt_paydown.html", {
            "request": request,
            "user": user,
            "prefill_balance": balance,
            "prefill_apr": apr,
            "prefill_payment": payment,
            "result": result
        })
    except (ValueError, TypeError) as e:
        return templates.TemplateResponse("user/calculator_debt_paydown.html", {
            "request": request,
            "user": user,
            "error": "Invalid input. Please enter valid numbers."
        })


@app.get("/portal/calculators/savings-goal", response_class=HTMLResponse)
def savings_goal_calculator(request: Request, user: Dict = Depends(get_current_user)):
    """Savings goal calculator page."""
    try:
        # Pre-fill with user's current savings if available
        accounts = get_user_account_summary(user["id"])
        prefill_savings = 0
        
        # Get savings account balance
        for key, acc in accounts.get("accounts_by_type", {}).items():
            if acc.get("type") in ["depository", "savings"]:
                prefill_savings += acc.get("balance", 0)
        
        return templates.TemplateResponse("user/calculator_savings_goal.html", {
            "request": request,
            "user": user,
            "prefill_savings": prefill_savings
        })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_code": 500,
            "error_message": f"Error loading calculator: {str(e)}"
        })


@app.post("/portal/calculators/savings-goal", response_class=HTMLResponse)
async def savings_goal_calculate(request: Request, user: Dict = Depends(get_current_user)):
    """Calculate savings goal results."""
    try:
        form_data = await request.form()
        goal_amount = float(form_data.get("goal_amount", 0))
        target_date = form_data.get("target_date", "")
        current_savings = float(form_data.get("current_savings", 0))
        
        result = calculate_savings_goal(goal_amount, target_date, current_savings)
        
        return templates.TemplateResponse("user/calculator_savings_goal.html", {
            "request": request,
            "user": user,
            "prefill_savings": current_savings,
            "result": result
        })
    except (ValueError, TypeError) as e:
        return templates.TemplateResponse("user/calculator_savings_goal.html", {
            "request": request,
            "user": user,
            "error": "Invalid input. Please enter valid numbers and date."
        })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

