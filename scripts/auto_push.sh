#!/bin/bash

# Pastikan berada di root project
PROJECT_ROOT=$(pwd)

echo "🔄 [Auto-Push] Detecting changes..."

# Add all changes
git add .

# Check if there are changes to commit
if git diff --cached --quiet; then
    echo "✅ No changes to push."
else
    TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
    echo "📝 Committing changes at $TIMESTAMP..."
    git commit -m "Auto-sync: Improvements and fixes at $TIMESTAMP"

    echo "🚀 Pushing to GitHub..."
    git push origin main
    echo "✅ Push successful."
fi
