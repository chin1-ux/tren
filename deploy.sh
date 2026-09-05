#!/bin/bash
# Trendrop Production Deployment Script

echo "=== STARTING DEPLOYMENT ==="

# 1. Verify Environment Files
echo "Verifying environment files..."
if [ ! -f "backend/.env" ]; then
    echo "ERROR: backend/.env is missing!"
    exit 1
fi

# 2. Install Backend Dependencies
echo "Installing backend dependencies..."
pip install -r backend/requirements.txt

# 3. Database Migration & Policy Upgrades
echo "Running database migration and setup..."
python backend/database_setup.py
if [ $? -ne 0 ]; then
    echo "ERROR: Database setup failed!"
    exit 1
fi

# 4. Run API Health Verification
echo "Running health checks..."
python backend/test_health.py
if [ $? -ne 0 ]; then
    echo "ERROR: Health checks failed!"
    exit 1
fi

echo "=== DEPLOYMENT COMPLETED SUCCESSFULLY ==="
exit 0
