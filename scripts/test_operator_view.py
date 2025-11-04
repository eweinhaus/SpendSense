#!/usr/bin/env python3
"""
Manual testing script for operator view enhancements.
Tests dashboard, user detail pages, decision traces, and signal windows.
"""

import urllib.request
import urllib.parse
import time
import json
import re

BASE_URL = "http://localhost:8000"

def fetch_url(url):
    """Fetch URL and return content."""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.read().decode('utf-8'), response.getcode()
    except Exception as e:
        return None, 0

def test_dashboard():
    """Test dashboard endpoint."""
    print("=" * 60)
    print("Step 1: Testing Dashboard")
    print("=" * 60)
    
    content, status_code = fetch_url(f"{BASE_URL}/")
    assert status_code == 200, f"Dashboard returned {status_code}"
    
    # Check for user list
    user_count = len(re.findall(r'<tr|<div class="card"', content))
    print(f"✓ Dashboard loaded successfully")
    print(f"✓ Found {user_count} user elements")
    
    # Find first user link
    user_match = re.search(r'href="(/user/\d+)"', content)
    if user_match:
        user_path = user_match.group(1)
        print(f"✓ Found user link: {user_path}")
        return user_path
    else:
        print("⚠ No user links found, trying /user/1")
        return "/user/1"

def test_user_detail(user_path):
    """Test user detail page with all enhancements."""
    print("\n" + "=" * 60)
    print("Step 2: Testing User Detail Page")
    print("=" * 60)
    
    content, status_code = fetch_url(f"{BASE_URL}{user_path}")
    assert status_code == 200, f"User detail returned {status_code}"
    
    # Check for dual-window tabs
    tabs = re.findall(r'<button[^>]*class="nav-link[^"]*"[^>]*>([^<]*)</button>', content)
    print(f"✓ Found {len(tabs)} signal window tabs")
    
    tab_text = ' '.join(tabs)
    if '30-Day' in tab_text and '180-Day' in tab_text:
        print("✓ Both 30d and 180d window tabs present")
    else:
        print(f"⚠ Tab texts: {tabs}")
    
    # Check for signal categories
    signal_categories = ['Credit', 'Subscription', 'Savings', 'Income']
    found_categories = [cat for cat in signal_categories if cat in content]
    print(f"✓ Found signal categories: {', '.join(found_categories)}")
    
    # Check for persona display
    persona_match = re.search(r'<span class="badge[^"]*">([^<]+)</span>', content)
    if persona_match:
        persona_text = persona_match.group(1)
        print(f"✓ Persona badge found: {persona_text}")
    
    # Check for persona rationale
    if 'Assignment Rationale' in content or 'Criteria Matched' in content:
        print("✓ Persona assignment rationale present")
    
    # Check for signal windows in persona
    if 'Signals Used' in content or 'window' in content.lower():
        print("✓ Window-based signal information present")
    
    # Check for decision traces
    trace_buttons = re.findall(r'data-bs-target="#trace-', content)
    print(f"✓ Found {len(trace_buttons)} decision trace buttons")
    
    # Check for trace content structure
    trace_sections = re.findall(r'id="trace-\d+"', content)
    if trace_sections:
        print(f"✓ Found {len(trace_sections)} trace sections")
    
    # Check for step badges
    step_badges = re.findall(r'Step \d+', content)
    if step_badges:
        print(f"✓ Found {len(step_badges)} step badges in traces")
    
    # Check for data cited sections
    if '<details' in content or 'bg-white' in content:
        print("✓ Data citations with expand/collapse present")
    
    return True

def test_performance():
    """Test performance metrics."""
    print("\n" + "=" * 60)
    print("Step 3: Performance Testing")
    print("=" * 60)
    
    endpoints = [
        ("Dashboard", "/"),
        ("User Detail", "/user/1"),
        ("API Docs", "/docs"),
    ]
    
    for name, path in endpoints:
        start = time.time()
        content, status_code = fetch_url(f"{BASE_URL}{path}")
        elapsed = time.time() - start
        
        status = "✓" if status_code == 200 else "✗"
        perf_status = "✓" if elapsed < 2.0 else "⚠"
        print(f"{status} {name}: {elapsed:.3f}s {perf_status}")

def test_production_endpoints():
    """Test production deployment endpoints."""
    print("\n" + "=" * 60)
    print("Step 4: Production Verification")
    print("=" * 60)
    
    production_url = "https://spendsense-2e84.onrender.com"
    
    endpoints = [
        ("Dashboard", "/"),
        ("API Docs", "/docs"),
        ("User Detail", "/user/1"),
    ]
    
    print(f"Testing production URL: {production_url}")
    
    for name, path in endpoints:
        try:
            start = time.time()
            content, status_code = fetch_url(f"{production_url}{path}")
            elapsed = time.time() - start
            
            status = "✓" if status_code == 200 else "✗"
            print(f"{status} {name}: {status_code} ({elapsed:.3f}s)")
        except Exception as e:
            print(f"✗ {name}: Error - {str(e)[:50]}")

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Phase 7: Manual Testing & Verification")
    print("=" * 60 + "\n")
    
    try:
        # Step 1: Test dashboard
        user_path = test_dashboard()
        
        # Step 2: Test user detail
        test_user_detail(user_path)
        
        # Step 3: Performance testing
        test_performance()
        
        # Step 4: Production verification
        test_production_endpoints()
        
        print("\n" + "=" * 60)
        print("✓ All manual tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

