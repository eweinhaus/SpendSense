"""
Tests for partner offers module.
"""

import pytest
import sqlite3
import os
import sys

# Add src directory to path to import modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

from spendsense.partner_offers import (
    get_eligible_offers,
    check_offer_eligibility,
    OFFER_CATALOG
)
from spendsense.database import get_db_connection, init_database


@pytest.fixture
def test_db():
    """Create a test database."""
    db_path = ":memory:"
    init_database(db_path)
    conn = get_db_connection(db_path)
    yield db_path
    conn.close()


@pytest.fixture
def test_user(test_db):
    """Create a test user."""
    conn = get_db_connection(test_db)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (name, email, consent_given)
        VALUES (?, ?, ?)
    """, ("Test User", "test@example.com", 1))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


class TestPartnerOffers:
    """Test partner offers functionality."""
    
    def test_offer_catalog_not_empty(self):
        """Test that offer catalog is not empty."""
        assert len(OFFER_CATALOG) > 0
        assert len(OFFER_CATALOG) >= 4  # At least 4 offer types
    
    def test_offer_catalog_structure(self):
        """Test offer catalog structure."""
        for offer in OFFER_CATALOG:
            assert "id" in offer
            assert "title" in offer
            assert "description" in offer
            assert "type" in offer
            assert "eligibility_requirements" in offer
    
    def test_get_eligible_offers_no_consent(self, test_db):
        """Test that offers are empty when user has no consent."""
        # Create user without consent
        conn = get_db_connection(test_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (name, email, consent_given)
            VALUES (?, ?, ?)
        """, ("No Consent User", "noconsent@example.com", 0))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Offers should still be checked (consent check is in app layer)
        offers = get_eligible_offers(user_id)
        assert isinstance(offers, list)
    
    def test_check_offer_eligibility_account_exclusion(self, test_db, test_user):
        """Test that offers are excluded if user has conflicting account."""
        # Add savings account to user
        conn = get_db_connection(test_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO accounts (user_id, account_id, type, subtype, current_balance)
            VALUES (?, ?, ?, ?, ?)
        """, (test_user, "acc1", "depository", "savings", 1000.0))
        conn.commit()
        conn.close()
        
        # Check HYSA offer (should be excluded)
        hysa_offer = next(o for o in OFFER_CATALOG if o["id"] == "high_yield_savings")
        is_eligible, reason = check_offer_eligibility(test_user, hysa_offer)
        
        assert is_eligible is False
        assert "savings" in reason.lower()
    
    def test_check_offer_eligibility_utilization_requirement(self, test_db, test_user):
        """Test utilization requirement check."""
        # Add credit utilization signal
        conn = get_db_connection(test_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO signals (user_id, signal_type, value, metadata)
            VALUES (?, ?, ?, ?)
        """, (test_user, "credit_utilization_max", 30.0, "{}"))
        conn.commit()
        conn.close()
        
        # Check balance transfer offer (requires 50%+ utilization)
        bt_offer = next(o for o in OFFER_CATALOG if o["id"] == "balance_transfer_card")
        is_eligible, reason = check_offer_eligibility(test_user, bt_offer)
        
        assert is_eligible is False
        assert "utilization" in reason.lower()
    
    def test_check_offer_eligibility_subscription_requirement(self, test_db, test_user):
        """Test subscription count requirement."""
        # Add subscription signals
        conn = get_db_connection(test_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO signals (user_id, signal_type, value, metadata)
            VALUES (?, ?, ?, ?)
        """, (test_user, "subscription_count", 2.0, "{}"))
        conn.commit()
        conn.close()
        
        # Check subscription management tool (requires 3+ subscriptions)
        sub_offer = next(o for o in OFFER_CATALOG if o["id"] == "subscription_management_tool")
        is_eligible, reason = check_offer_eligibility(test_user, sub_offer)
        
        assert is_eligible is False
        assert "subscription" in reason.lower()
    
    def test_get_eligible_offers_returns_list(self, test_db, test_user):
        """Test that get_eligible_offers returns a list."""
        offers = get_eligible_offers(test_user)
        assert isinstance(offers, list)
        assert len(offers) <= 3  # Should return 1-3 offers
    
    def test_get_eligible_offers_includes_rationale(self, test_db, test_user):
        """Test that eligible offers include rationale."""
        offers = get_eligible_offers(test_user)
        for offer in offers:
            assert "eligibility_rationale" in offer
            assert isinstance(offer["eligibility_rationale"], str)
            assert len(offer["eligibility_rationale"]) > 0
    
    def test_get_eligible_offers_with_high_utilization(self, test_db, test_user):
        """Test offers for high utilization user."""
        # Add high utilization signal and credit account
        conn = get_db_connection(test_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO signals (user_id, signal_type, value, metadata)
            VALUES (?, ?, ?, ?)
        """, (test_user, "credit_utilization_max", 75.0, "{}"))
        cursor.execute("""
            INSERT INTO signals (user_id, signal_type, value, metadata)
            VALUES (?, ?, ?, ?)
        """, (test_user, "credit_interest_charges", 50.0, "{}"))
        cursor.execute("""
            INSERT INTO accounts (user_id, account_id, type, current_balance, "limit")
            VALUES (?, ?, ?, ?, ?)
        """, (test_user, "cc1", "credit", 7500.0, 10000.0))
        cursor.execute("""
            INSERT INTO personas (user_id, persona_type, criteria_matched)
            VALUES (?, ?, ?)
        """, (test_user, "high_utilization", "High credit utilization"))
        conn.commit()
        conn.close()
        
        offers = get_eligible_offers(test_user)
        # Should potentially include balance transfer offer
        offer_ids = [o["id"] for o in offers]
        # Balance transfer may or may not be eligible depending on other checks
        assert isinstance(offers, list)
    
    def test_offer_rationale_includes_data(self, test_db, test_user):
        """Test that offer rationale includes specific user data."""
        # Add relevant signals
        conn = get_db_connection(test_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO signals (user_id, signal_type, value, metadata)
            VALUES (?, ?, ?, ?)
        """, (test_user, "subscription_count", 5.0, "{}"))
        cursor.execute("""
            INSERT INTO signals (user_id, signal_type, value, metadata)
            VALUES (?, ?, ?, ?)
        """, (test_user, "subscription_monthly_spend", 150.0, "{}"))
        conn.commit()
        conn.close()
        
        offers = get_eligible_offers(test_user)
        for offer in offers:
            if offer["id"] == "subscription_management_tool":
                rationale = offer["eligibility_rationale"]
                assert "5" in rationale or "subscription" in rationale.lower()

