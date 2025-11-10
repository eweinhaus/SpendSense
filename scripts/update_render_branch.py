#!/usr/bin/env python3
"""
Update Render service branch using Render API
"""

import os
import sys
import json
import urllib.request
from typing import Optional, Dict

# Render API Configuration
RENDER_API_BASE = "https://api.render.com/v1"
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "rnd_gwfg02Ys5ujjIIFglCVaFtNDFRdg")

# Service Configuration
SERVICE_ID = "srv-d44njmq4d50c73el4brg"
NEW_BRANCH = "main"

# Headers for API requests
HEADERS = {
    "Authorization": f"Bearer {RENDER_API_KEY}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}


def api_request(method: str, url: str, data: Optional[Dict] = None) -> Optional[Dict]:
    """Make an API request to Render"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        req.get_method = lambda: method
        
        if data:
            req.data = json.dumps(data).encode('utf-8')
        
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else ""
        print(f"HTTP Error {e.code}: {error_body}")
        return None
    except Exception as e:
        print(f"Request error: {e}")
        return None


def get_service(service_id: str) -> Optional[Dict]:
    """Get service details"""
    return api_request("GET", f"{RENDER_API_BASE}/services/{service_id}")


def update_service_branch(service_id: str, branch: str) -> bool:
    """Update the branch for a service"""
    try:
        print(f"Updating service {service_id} to branch '{branch}'...")
        
        # Get current service details
        service = get_service(service_id)
        if not service:
            print("❌ Failed to get service details")
            return False
        
        service_data = service.get("service", {})
        current_branch = service_data.get("branch")
        
        print(f"Current branch: {current_branch}")
        print(f"New branch: {branch}")
        
        if current_branch == branch:
            print(f"✅ Service is already on branch '{branch}'")
            return True
        
        # Update the service branch
        # Note: Render API uses PATCH to update service
        # The API expects the branch in serviceDetails for web services
        update_data = {
            "branch": branch
        }
        
        result = api_request("PATCH", f"{RENDER_API_BASE}/services/{service_id}", update_data)
        
        if result:
            print(f"✅ Successfully updated branch to '{branch}'")
            return True
        else:
            print("❌ Failed to update branch")
            return False
            
    except Exception as e:
        print(f"❌ Error updating branch: {e}")
        return False


def trigger_deployment(service_id: str) -> bool:
    """Trigger a new deployment"""
    try:
        print(f"\nTriggering deployment for service {service_id}...")
        # Render API expects empty body or no body for deploy trigger
        deploy = api_request("POST", 
            f"{RENDER_API_BASE}/services/{service_id}/deploys",
            {})
        if deploy:
            deploy_id = deploy.get("deploy", {}).get("id")
            print(f"✅ Deployment triggered! Deploy ID: {deploy_id}")
            return True
        else:
            print("⚠️  Deployment trigger returned no result (may trigger automatically)")
            return True  # Still return True since auto-deploy is enabled
    except Exception as e:
        print(f"⚠️  Deployment trigger error (auto-deploy may handle this): {e}")
        return True  # Still return True since auto-deploy is enabled


def main():
    print("=" * 60)
    print("Update Render Service Branch")
    print("=" * 60)
    print(f"Service ID: {SERVICE_ID}")
    print(f"New Branch: {NEW_BRANCH}")
    print()
    
    # Update branch
    if update_service_branch(SERVICE_ID, NEW_BRANCH):
        # Trigger deployment
        trigger_deployment(SERVICE_ID)
        print("\n✅ Branch update complete!")
        print(f"Monitor deployment at: https://dashboard.render.com/web/{SERVICE_ID}")
    else:
        print("\n❌ Failed to update branch")
        sys.exit(1)


if __name__ == "__main__":
    main()

