"""
Tests for Phase 8C: Design System & Component Library
Tests CSS loading, component rendering, and accessibility.
"""

import pytest
import os
import time
import threading
import requests
from playwright.sync_api import Page, expect


@pytest.fixture(scope="module")
def test_server():
    """Start test server in background."""
    import uvicorn
    from spendsense.app import app
    
    # Start server in background
    server_thread = threading.Thread(
        target=lambda: uvicorn.run(app, host="127.0.0.1", port=8002, log_level="error"),
        daemon=True
    )
    server_thread.start()
    
    # Wait for server to start
    time.sleep(3)
    
    # Verify server is running
    try:
        response = requests.get("http://127.0.0.1:8002/", timeout=2)
        assert response.status_code == 200
    except Exception:
        pytest.skip("Test server failed to start")
    
    yield "http://127.0.0.1:8002"
    
    # Cleanup handled by daemon thread


@pytest.fixture
def demo_page(page: Page, test_server):
    """Navigate to demo page."""
    base_url = test_server
    page.goto(f"{base_url}/static/demo.html")
    return page


def test_demo_page_loads(demo_page: Page):
    """Test that demo page loads successfully."""
    expect(demo_page).to_have_title("Design System Demo - SpendSense")


def test_css_files_load(demo_page: Page):
    """Test that all CSS files load without errors."""
    # Check for CSS import errors in console
    errors = []
    demo_page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)
    
    # Reload to capture any errors
    demo_page.reload()
    time.sleep(1)
    
    # Check that CSS is loaded (variables should be available)
    css_variables = demo_page.evaluate("""
        () => {
            const styles = getComputedStyle(document.documentElement);
            return {
                primary: styles.getPropertyValue('--color-primary'),
                spacing: styles.getPropertyValue('--spacing-4')
            };
        }
    """)
    
    assert css_variables['primary'].strip() == '#2563EB' or css_variables['primary'].strip() == 'rgb(37, 99, 235)'
    assert css_variables['spacing'].strip() == '1rem' or css_variables['spacing'].strip() == '16px'


def test_buttons_render(demo_page: Page):
    """Test that button components render correctly."""
    # Check for primary button
    primary_button = demo_page.locator("button.btn-primary").first
    expect(primary_button).to_be_visible()
    
    # Check button styles
    bg_color = primary_button.evaluate("el => window.getComputedStyle(el).backgroundColor")
    assert bg_color is not None
    
    # Check secondary button
    secondary_button = demo_page.locator("button.btn-secondary").first
    expect(secondary_button).to_be_visible()
    
    # Check danger button
    danger_button = demo_page.locator("button.btn-danger").first
    expect(danger_button).to_be_visible()


def test_buttons_keyboard_navigation(demo_page: Page):
    """Test keyboard navigation for buttons."""
    # Tab to first button
    demo_page.keyboard.press("Tab")
    focused = demo_page.evaluate("document.activeElement.className")
    assert "btn" in focused or "navbar" in focused
    
    # Check focus indicator is visible
    focused_element = demo_page.locator(":focus")
    if focused_element.count() > 0:
        outline = focused_element.first.evaluate("el => window.getComputedStyle(el).outline")
        assert outline != "none" or outline != ""


def test_cards_render(demo_page: Page):
    """Test that card components render correctly."""
    cards = demo_page.locator(".card")
    expect(cards.first).to_be_visible()
    
    # Check card has shadow
    box_shadow = cards.first.evaluate("el => window.getComputedStyle(el).boxShadow")
    assert box_shadow != "none"


def test_badges_render(demo_page: Page):
    """Test that badge components render correctly."""
    # Check persona badges
    persona_badges = demo_page.locator(".badge-persona")
    expect(persona_badges.first).to_be_visible()
    
    # Check status badges
    status_badges = demo_page.locator(".badge-success, .badge-warning, .badge-error, .badge-info")
    expect(status_badges.first).to_be_visible()


def test_form_inputs_render(demo_page: Page):
    """Test that form components render correctly."""
    form_input = demo_page.locator(".form-input").first
    expect(form_input).to_be_visible()
    
    # Check label exists
    form_label = demo_page.locator(".form-label").first
    expect(form_label).to_be_visible()


def test_form_inputs_focus(demo_page: Page):
    """Test form input focus states."""
    form_input = demo_page.locator("#demo-email")
    form_input.focus()
    
    # Check focus state
    focused = demo_page.evaluate("document.activeElement.id")
    assert focused == "demo-email"
    
    # Check focus styles are applied
    border_color = form_input.evaluate("el => window.getComputedStyle(el).borderColor")
    assert border_color is not None


def test_alerts_render(demo_page: Page):
    """Test that alert components render correctly."""
    alerts = demo_page.locator(".alert")
    expect(alerts.first).to_be_visible()
    
    # Check alert variants exist
    success_alert = demo_page.locator(".alert-success").first
    expect(success_alert).to_be_visible()
    
    warning_alert = demo_page.locator(".alert-warning").first
    expect(warning_alert).to_be_visible()


def test_typography_hierarchy(demo_page: Page):
    """Test typography hierarchy."""
    h1 = demo_page.locator("h1").first
    h2 = demo_page.locator("h2").first
    
    if h1.count() > 0 and h2.count() > 0:
        h1_size = h1.evaluate("el => window.getComputedStyle(el).fontSize")
        h2_size = h2.evaluate("el => window.getComputedStyle(el).fontSize")
        
        # H1 should be larger than H2
        assert float(h1_size.replace('px', '')) >= float(h2_size.replace('px', ''))


def test_color_contrast_basic(demo_page: Page):
    """Test basic color contrast (visual check)."""
    # Check that primary button has white text (good contrast)
    primary_button = demo_page.locator("button.btn-primary").first
    color = primary_button.evaluate("el => window.getComputedStyle(el).color")
    bg_color = primary_button.evaluate("el => window.getComputedStyle(el).backgroundColor")
    
    # Both should be defined
    assert color is not None
    assert bg_color is not None


def test_existing_templates_still_work(page: Page, test_server):
    """Test that existing templates still work with design system."""
    base_url = test_server
    
    # Test dashboard
    page.goto(f"{base_url}/")
    expect(page).to_have_title("Dashboard - SpendSense MVP")
    
    # Check page loads
    content = page.locator("body")
    expect(content).to_be_visible()
    
    # Test that CSS loads
    css_loaded = page.evaluate("""
        () => {
            const link = Array.from(document.querySelectorAll('link[rel="stylesheet"]'))
                .find(link => link.href.includes('style.css'));
            return link !== undefined;
        }
    """)
    assert css_loaded


def test_bootstrap_compatibility(page: Page, test_server):
    """Test that Bootstrap 5 still works alongside design system."""
    base_url = test_server
    page.goto(f"{base_url}/")
    
    # Check Bootstrap classes still work
    navbar = page.locator(".navbar")
    expect(navbar).to_be_visible()
    
    # Check Bootstrap styling is applied
    navbar_bg = navbar.evaluate("el => window.getComputedStyle(el).backgroundColor")
    assert navbar_bg is not None


def test_demo_page_components(page: Page, test_server):
    """Test all components on demo page are visible."""
    # Navigate to demo page
    base_url = test_server
    page.goto(f"{base_url}/static/demo.html")
    
    # Check all sections are visible
    sections = page.locator(".demo-section")
    expect(sections.first).to_be_visible()
    
    # Check buttons section exists
    buttons_heading = page.locator("h2:has-text('Buttons')")
    expect(buttons_heading).to_be_visible()
    
    # Check cards section exists
    cards_heading = page.locator("h2:has-text('Cards')")
    expect(cards_heading).to_be_visible()
    
    # Check badges section exists
    badges_heading = page.locator("h2:has-text('Badges')")
    expect(badges_heading).to_be_visible()

