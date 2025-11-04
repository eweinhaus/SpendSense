"""
End-to-end tests for Phase 8A using Playwright.
Tests the complete user flow from login to using calculators.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(scope="module")
def base_url():
    """Return the base URL for the application."""
    return "http://localhost:8000"


@pytest.mark.skipif(True, reason="Requires running server - use manual testing or CI")
def test_login_flow(page: Page, base_url):
    """Test complete login flow."""
    # Navigate to login page
    page.goto(f"{base_url}/login")
    
    # Check login page loaded
    expect(page).to_have_title("Login - SpendSense")
    expect(page.locator("h2")).to_contain_text("SpendSense Login")
    
    # Try to login with invalid user
    page.fill('input[name="identifier"]', "invalid@example.com")
    page.click('button[type="submit"]')
    
    # Should show error
    expect(page.locator(".alert-danger")).to_be_visible()
    expect(page.locator(".alert-danger")).to_contain_text("User not found")
    
    # Login with valid user (assuming user exists in test DB)
    page.fill('input[name="identifier"]', "1")
    page.click('button[type="submit"]')
    
    # Should redirect to dashboard
    expect(page).to_have_url(f"{base_url}/portal/dashboard")


@pytest.mark.skipif(True, reason="Requires running server")
def test_dashboard_display(page: Page, base_url):
    """Test dashboard displays correctly after login."""
    # Login first (assuming user 1 exists)
    page.goto(f"{base_url}/login")
    page.fill('input[name="identifier"]', "1")
    page.click('button[type="submit"]')
    
    # Wait for dashboard
    expect(page).to_have_url(f"{base_url}/portal/dashboard")
    expect(page.locator("h1")).to_contain_text("Welcome")
    
    # Check for persona display
    expect(page.locator(".card")).to_contain_text("Financial Profile")
    
    # Check for stats cards
    expect(page.locator("text=Emergency Fund")).to_be_visible()
    expect(page.locator("text=Credit Utilization")).to_be_visible()


@pytest.mark.skipif(True, reason="Requires running server")
def test_navigation_flow(page: Page, base_url):
    """Test navigation between pages."""
    # Login
    page.goto(f"{base_url}/login")
    page.fill('input[name="identifier"]', "1")
    page.click('button[type="submit"]')
    
    # Navigate to recommendations
    page.click('text=Recommendations')
    expect(page).to_have_url(f"{base_url}/portal/recommendations")
    
    # Navigate to profile
    page.click('text=Profile')
    expect(page).to_have_url(f"{base_url}/portal/profile")
    
    # Navigate to calculators
    page.click('text=Calculators')
    expect(page).to_have_url(f"{base_url}/portal/calculators")
    
    # Navigate back to dashboard
    page.click('text=Dashboard')
    expect(page).to_have_url(f"{base_url}/portal/dashboard")


@pytest.mark.skipif(True, reason="Requires running server")
def test_consent_management(page: Page, base_url):
    """Test consent management flow."""
    # Login
    page.goto(f"{base_url}/login")
    page.fill('input[name="identifier"]', "1")
    page.click('button[type="submit"]')
    
    # Navigate to consent page
    page.click('text=Consent')
    expect(page).to_have_url(f"{base_url}/portal/consent")
    
    # Check consent status is displayed
    expect(page.locator("text=Current Consent Status")).to_be_visible()
    
    # Toggle consent (if checkbox exists)
    consent_toggle = page.locator('input[name="consent"]')
    if consent_toggle.is_visible():
        current_state = consent_toggle.is_checked()
        consent_toggle.click()
        page.click('button[type="submit"]')
        
        # Should show success message
        expect(page.locator(".alert-success")).to_be_visible()


@pytest.mark.skipif(True, reason="Requires running server")
def test_emergency_fund_calculator(page: Page, base_url):
    """Test emergency fund calculator."""
    # Login
    page.goto(f"{base_url}/login")
    page.fill('input[name="identifier"]', "1")
    page.click('button[type="submit"]')
    
    # Navigate to calculators
    page.click('text=Calculators')
    page.click('text=Emergency Fund')
    
    # Fill calculator form
    page.fill('input[name="monthly_expenses"]', "2000")
    page.select_option('select[name="months"]', "6")
    page.click('button[type="submit"]')
    
    # Check results
    expect(page.locator("text=Results")).to_be_visible()
    expect(page.locator("text=12000")).to_be_visible()  # 2000 * 6


@pytest.mark.skipif(True, reason="Requires running server")
def test_logout(page: Page, base_url):
    """Test logout functionality."""
    # Login
    page.goto(f"{base_url}/login")
    page.fill('input[name="identifier"]', "1")
    page.click('button[type="submit"]')
    
    # Verify logged in
    expect(page).to_have_url(f"{base_url}/portal/dashboard")
    
    # Logout
    page.click('button:has-text("Logout")')
    
    # Should redirect to login
    expect(page).to_have_url(f"{base_url}/login")
    
    # Try to access protected route
    page.goto(f"{base_url}/portal/dashboard")
    
    # Should redirect back to login or show 401
    expect(page.url).to_contain("/login")

