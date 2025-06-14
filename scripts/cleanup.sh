#!/bin/bash

# Personal Finance App Cleanup Script
# This script removes unnecessary files and keeps the project lean for production

echo "🧹 Cleaning up Personal Finance App..."

# Remove development files
echo "📁 Removing development files..."
rm -rf .pytest_cache/
rm -rf __pycache__/
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

# Remove old PDF files (keep only necessary test files)
echo "📄 Removing old PDF files..."
rm -f *.pdf
rm -f Federal_Bank_Decrypted.pdf

# Remove old app.py and related files
echo "🗂️ Removing old application files..."
if [ -f "app.py" ]; then
    mv app.py app_old.py.backup
    echo "   Backed up old app.py to app_old.py.backup"
fi

# Remove old requirements
if [ -f "requirements.txt" ]; then
    mv requirements.txt requirements_old.txt.backup
    echo "   Backed up old requirements.txt to requirements_old.txt.backup"
fi

# Remove upload directory contents but keep the directory
echo "📤 Cleaning upload directory..."
rm -rf uploads/*
touch uploads/.gitkeep

# Remove old data files - transactions.json removed for security
echo "🗄️ Cleaning old data files..."
# transactions.json removed - all data stored in database only

# Remove unnecessary parsers (since we're focusing on manual entry)
echo "📝 Archiving PDF parsers..."
mkdir -p archive/parsers
if [ -d "parsers" ]; then
    cp -r parsers/* archive/parsers/
    # Keep only the __init__.py for potential future use
    find parsers/ -name "*.py" ! -name "__init__.py" -delete
fi

# Remove old documentation
echo "📚 Cleaning old documentation..."
if [ -d "docs" ]; then
    rm -rf docs/
fi

# Remove old templates
echo "🎨 Cleaning old templates..."
if [ -f "templates/index.html" ]; then
    mv templates/index.html templates/index_old.html.backup
fi

if [ -f "templates/transactions.html" ]; then
    mv templates/transactions.html templates/transactions_old.html.backup
fi

if [ -f "templates/review.html" ]; then
    mv templates/review.html templates/review_old.html.backup
fi

# Create new structure with renamed files
echo "🔄 Setting up new structure..."

# Rename new files to replace old ones
if [ -f "app_new.py" ]; then
    mv app_new.py app.py
    echo "   Renamed app_new.py to app.py"
fi

if [ -f "requirements_new.txt" ]; then
    mv requirements_new.txt requirements.txt
    echo "   Renamed requirements_new.txt to requirements.txt"
fi

if [ -f "templates/index_new.html" ]; then
    mv templates/index_new.html templates/index.html
    echo "   Renamed index_new.html to index.html"
fi

if [ -f "README_NEW.md" ]; then
    mv README_NEW.md README.md
    echo "   Renamed README_NEW.md to README.md"
fi

# Update .gitignore for production
echo "📝 Updating .gitignore..."
cat >> .gitignore << 'EOF'

# Production specific
*.backup
archive/
.env
personal_finance.db

# Docker
.dockerignore

# Terraform
terraform/.terraform/
terraform/*.tfstate
terraform/*.tfstate.backup
terraform/tfplan

# AWS
.aws/credentials

# IDE
.vscode/
.idea/

EOF

# Create production-ready file structure
echo "📂 Creating production file structure..."
mkdir -p logs
mkdir -p scripts
mkdir -p migrations
touch logs/.gitkeep
touch migrations/.gitkeep

# Set proper permissions
echo "🔐 Setting permissions..."
chmod +x scripts/*.sh

# Initialize Flask-Migrate if not already done
echo "🗄️ Checking database migrations..."
if [ ! -d "migrations" ]; then
    echo "   Initializing Flask-Migrate..."
    export FLASK_APP=app.py
    flask db init
fi

# Final cleanup
echo "🗑️ Final cleanup..."
find . -name ".DS_Store" -delete
find . -name "Thumbs.db" -delete

echo "✅ Cleanup completed!"
echo ""
echo "📊 Project structure is now production-ready:"
echo "   - Old files backed up with .backup extension"
echo "   - PDF parsers archived in archive/parsers/"
echo "   - New lean structure focused on manual entry"
echo "   - Docker and Terraform ready for deployment"
echo ""
echo "🚀 Next steps:"
echo "   1. Test the application: docker-compose up --build"
echo "   2. Deploy to AWS: ./scripts/deploy.sh production"
echo "   3. Remove .backup files once everything works"
echo ""
echo "💡 To restore old functionality:"
echo "   1. Restore parsers: cp archive/parsers/* parsers/"
echo "   2. Restore old app: mv app_old.py.backup app_old.py" 