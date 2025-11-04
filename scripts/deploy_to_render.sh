#!/bin/bash
# Render.com Deployment Helper Script
# This script helps automate the Render.com deployment process

set -e

echo "=========================================="
echo "SpendSense - Render.com Deployment Helper"
echo "=========================================="
echo ""

# Check if render CLI is installed
if ! command -v render &> /dev/null; then
    echo "⚠️  Render CLI not found. Installing..."
    echo ""
    echo "To install Render CLI:"
    echo "  npm install -g render-cli"
    echo ""
    echo "Or use the web dashboard: https://dashboard.render.com"
    echo ""
    echo "For manual deployment, follow these steps:"
    echo "1. Go to https://dashboard.render.com"
    echo "2. Click 'New' → 'Web Service'"
    echo "3. Connect your GitHub repository"
    echo "4. Use render.yaml configuration or set:"
    echo "   - Build Command: pip install -r requirements.txt"
    echo "   - Start Command: gunicorn -w 2 -k uvicorn.workers.UvicornWorker spendsense.app:app --bind 0.0.0.0:\$PORT"
    echo "5. Set environment variables:"
    echo "   - PYTHONPATH=/opt/render/project/src"
    echo "   - DATABASE_URL=sqlite:///spendsense.db"
    echo "   - DEBUG=False"
    echo "   - OPENAI_API_KEY=your_key_here"
    echo "6. Deploy!"
    echo ""
    exit 1
fi

# Check if logged in
if ! render auth status &> /dev/null; then
    echo "🔐 Please log in to Render:"
    render auth login
fi

echo "✅ Render CLI ready"
echo ""

# Check if service exists
SERVICE_NAME="spendsense"
if render services list | grep -q "$SERVICE_NAME"; then
    echo "📦 Service '$SERVICE_NAME' found"
    echo "🔄 Updating deployment..."
    render deploy --service "$SERVICE_NAME"
else
    echo "📦 Creating new service '$SERVICE_NAME'..."
    echo ""
    echo "Please create the service manually using render.yaml:"
    echo "  render services create --yaml render.yaml"
    echo ""
    echo "Or use the web dashboard with the configuration in render.yaml"
fi

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Verify deployment in Render dashboard"
echo "2. Check service logs for any errors"
echo "3. Test production URL"
echo "4. Run production verification tests"
echo ""

