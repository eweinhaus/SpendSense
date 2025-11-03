"""
SpendSense MVP Package

A take-home assignment project for building an explainable, consent-aware system
that detects behavioral patterns from transaction data, assigns user personas,
and delivers personalized financial education recommendations.
"""

__version__ = "0.1.0"

# Import main modules for easier access (using relative imports)
from .database import (
    get_db_connection,
    init_database,
    validate_schema,
)
from .detect_signals import (
    detect_credit_signals,
    detect_subscription_signals,
    store_signal,
)
from .personas import (
    assign_persona,
    get_user_signals,
    store_persona_assignment,
)
from .recommendations import generate_recommendations
from .rationales import generate_rationale
from .traces import generate_decision_trace

__all__ = [
    "get_db_connection",
    "init_database",
    "validate_schema",
    "detect_credit_signals",
    "detect_subscription_signals",
    "store_signal",
    "assign_persona",
    "get_user_signals",
    "store_persona_assignment",
    "generate_recommendations",
    "generate_rationale",
    "generate_decision_trace",
]

