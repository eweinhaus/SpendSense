#!/usr/bin/env python3
"""
Render.com Deployment Script
Automates deployment of SpendSense to Render.com using the Render API
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any

# Render API Configuration
RENDER_API_BASE = "https://api.render.com/v1"
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "rnd_gwfg02Ys5ujjIIFglCVaFtNDFRdg")

# Service Configuration
SERVICE_NAME = "spendsense"
REPO_URL = "https://github.com/eweinhaus/SpendSense.git"
BRANCH = "improve_mvp"  # or "main"

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


def get_owner_id() -> Optional[str]:
    """Get the owner ID from the API"""
    try:
        result = api_request("GET", f"{RENDER_API_BASE}/owners")
        if result and len(result) > 0:
            return result[0].get("owner", {}).get("id")
    except Exception as e:
        print(f"Error getting owner ID: {e}")
    return None


def get_service_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Check if a service with the given name already exists"""
    try:
        services = api_request("GET", f"{RENDER_API_BASE}/services")
        if services:
            for service_data in services:
                service = service_data.get("service", {})
                if service.get("name") == name:
                    return service
    except Exception as e:
        print(f"Error checking for existing service: {e}")
    return None


def get_repo_id() -> Optional[str]:
    """Get the repository ID from Render"""
    try:
        owner_id = get_owner_id()
        if not owner_id:
            return None
        
        repos = api_request("GET", f"{RENDER_API_BASE}/repos")
        if repos:
            for repo_data in repos:
                repo = repo_data.get("repo", {})
                if "spendsense" in repo.get("name", "").lower() or "spendsense" in repo.get("url", "").lower():
                    return repo.get("id")
    except Exception as e:
        print(f"Error getting repo ID: {e}")
    return None


def create_web_service(owner_id: str, repo_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Create a new web service on Render"""
    service_config = {
        "type": "web_service",
        "name": SERVICE_NAME,
        "ownerId": owner_id,
        "repo": REPO_URL,
        "branch": BRANCH,
        "autoDeploy": "yes",
        "serviceDetails": {
            "buildCommand": "pip install -r requirements.txt",
            "startCommand": "gunicorn -w 2 -k uvicorn.workers.UvicornWorker spendsense.app:app --bind 0.0.0.0:$PORT",
            "plan": "starter",  # or "free" for free tier
            "env": "python",
            "region": "ohio",
            "envSpecificDetails": {
                "buildCommand": "pip install -r requirements.txt",
                "startCommand": "gunicorn -w 2 -k uvicorn.workers.UvicornWorker spendsense.app:app --bind 0.0.0.0:$PORT"
            }
        },
        "envVars": [
            {
                "key": "PYTHONPATH",
                "value": "/opt/render/project/src/src"
            },
            {
                "key": "DATABASE_URL",
                "value": "sqlite:///spendsense.db"
            },
            {
                "key": "DEBUG",
                "value": "False"
            },
            {
                "key": "OPENAI_API_KEY",
                "value": "",  # User needs to set this manually
                "sync": False
            }
        ]
    }
    
    if repo_id:
        service_config["repoId"] = repo_id
    
    try:
        print(f"Creating service '{SERVICE_NAME}'...")
        result = api_request("POST", f"{RENDER_API_BASE}/services", service_config)
        if result:
            return result.get("service")
        return None
    except Exception as e:
        print(f"Error creating service: {e}")
        return None


def update_service_env_vars(service_id: str, env_vars: list):
    """Update environment variables for a service"""
    try:
        # Get current env vars
        current_vars = api_request("GET", f"{RENDER_API_BASE}/services/{service_id}/env-vars")
        if not current_vars:
            current_vars = []
        
        # Update each env var
        for var in env_vars:
            var_key = var["key"]
            var_value = var.get("value", "")
            
            # Check if var already exists
            existing_var = None
            for cv in current_vars:
                if cv.get("key") == var_key:
                    existing_var = cv
                    break
            
            if existing_var:
                # Update existing
                result = api_request("PATCH", 
                    f"{RENDER_API_BASE}/services/{service_id}/env-vars/{existing_var['id']}",
                    {"value": var_value})
                if result:
                    print(f"  Updated env var: {var_key}")
            else:
                # Create new
                result = api_request("POST", 
                    f"{RENDER_API_BASE}/services/{service_id}/env-vars",
                    var)
                if result:
                    print(f"  Created env var: {var_key}")
    except Exception as e:
        print(f"Error updating env vars: {e}")


def deploy_service(service_id: str):
    """Trigger a deployment for a service"""
    try:
        print(f"Triggering deployment for service {service_id}...")
        deploy = api_request("POST", 
            f"{RENDER_API_BASE}/services/{service_id}/deploys",
            {"clearCache": False})
        if deploy:
            deploy_id = deploy.get("deploy", {}).get("id")
            print(f"✅ Deployment triggered! Deploy ID: {deploy_id}")
            return deploy_id
        return None
    except Exception as e:
        print(f"Error triggering deployment: {e}")
        return None


def main():
    print("=" * 60)
    print("SpendSense - Render.com Deployment")
    print("=" * 60)
    print()
    
    # Check if service already exists
    existing_service = get_service_by_name(SERVICE_NAME)
    
    if existing_service:
        service_id = existing_service.get("id")
        service_url = existing_service.get("serviceDetails", {}).get("url", "N/A")
        print(f"✅ Service '{SERVICE_NAME}' already exists!")
        print(f"   Service ID: {service_id}")
        print(f"   URL: {service_url}")
        print()
        print("Updating environment variables...")
        env_vars = [
            {"key": "PYTHONPATH", "value": "/opt/render/project/src/src"},
            {"key": "DATABASE_URL", "value": "sqlite:///spendsense.db"},
            {"key": "DEBUG", "value": "False"}
        ]
        update_service_env_vars(service_id, env_vars)
        print()
        print("Note: OPENAI_API_KEY must be set manually in Render dashboard")
        print()
        deploy_choice = input("Trigger a new deployment? (y/n): ").strip().lower()
        if deploy_choice == 'y':
            deploy_service(service_id)
    else:
        print(f"Creating new service '{SERVICE_NAME}'...")
        owner_id = get_owner_id()
        if not owner_id:
            print("❌ Error: Could not get owner ID. Please check your API key.")
            sys.exit(1)
        
        print(f"Owner ID: {owner_id}")
        repo_id = get_repo_id()
        if repo_id:
            print(f"Repository ID: {repo_id}")
        
        service = create_web_service(owner_id, repo_id)
        
        if service:
            service_id = service.get("id")
            service_url = service.get("serviceDetails", {}).get("url", "Will be available after deployment")
            print()
            print("✅ Service created successfully!")
            print(f"   Service ID: {service_id}")
            print(f"   Dashboard: {service.get('dashboardUrl', 'N/A')}")
            print(f"   URL: {service_url}")
            print()
            print("⚠️  Important: Set OPENAI_API_KEY manually in Render dashboard:")
            print(f"   https://dashboard.render.com/web/{service_id}")
            print()
            print("Deployment will start automatically...")
            print("Monitor progress at:", service.get("dashboardUrl", "N/A"))
        else:
            print()
            print("❌ Failed to create service via API.")
            print()
            print("Please create the service manually using one of these methods:")
            print()
            print("Option 1: Blueprint Deployment (Recommended)")
            print("  1. Go to https://dashboard.render.com")
            print("  2. Click 'New' → 'Blueprint'")
            print("  3. Connect GitHub repository")
            print("  4. Select SpendSense repository")
            print("  5. Render will detect render.yaml automatically")
            print()
            print("Option 2: Manual Web Service")
            print("  1. Go to https://dashboard.render.com")
            print("  2. Click 'New' → 'Web Service'")
            print("  3. Connect GitHub repository")
            print("  4. Use settings from render.yaml")
            print()
            sys.exit(1)
    
    print()
    print("=" * 60)
    print("Deployment Setup Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

