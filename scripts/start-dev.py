#!/usr/bin/env python3
"""
Development startup script for Personal Finance Dashboard
This script properly loads environment variables and starts the application.
"""

import os
import sys
import subprocess

# Try to import dotenv, but handle gracefully if not available
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    print("⚠️  python-dotenv not available. Loading environment manually...")
    DOTENV_AVAILABLE = False

def load_env_file(env_file='.env'):
    """Load environment variables from .env file manually if dotenv is not available"""
    if not os.path.exists(env_file):
        return False
    
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('\'"')
                    os.environ[key.strip()] = value
        return True
    except Exception as e:
        print(f"Error loading .env file: {e}")
        return False

def main():
    print("🚀 Starting Personal Finance Dashboard Development Environment")
    print("=" * 60)
    
    # Load environment variables from .env file
    if os.path.exists('.env'):
        if DOTENV_AVAILABLE:
            load_dotenv('.env')
            print("✅ Loaded environment variables from .env file (using python-dotenv)")
        else:
            if load_env_file('.env'):
                print("✅ Loaded environment variables from .env file (manual parsing)")
            else:
                print("❌ Failed to load .env file")
    else:
        print("❌ .env file not found. Creating from template...")
        subprocess.run(['cp', 'env.example', '.env'])
        if DOTENV_AVAILABLE:
            load_dotenv('.env')
        else:
            load_env_file('.env')
        print("✅ Created .env file from template")
    
    # Set default values for required environment variables if not set
    defaults = {
        'DB_ENCRYPTION_KEY': 'zmJgYyCDjrG1UFNyxqGx5ar0xzIJFTdT20FcQ12M-qE=',
        'SECRET_KEY': 'dev-secret-key-change-in-production',
        'DATABASE_URL': 'postgresql://financeuser:financepass@localhost:5433/personal_finance',
        'FLASK_ENV': 'development',
        'OLLAMA_BASE_URL': 'http://localhost:11434',
        'ENABLE_FILE_UPLOAD': 'true',
        'ENABLE_LLM_PARSING': 'true',
        'LLM_DEFAULT_MODEL': 'llama2:7b-chat'
    }
    
    for key, default_value in defaults.items():
        if not os.getenv(key):
            os.environ[key] = default_value
            print(f"✅ Set default value for {key}")
    
    print("✅ All required environment variables are set")
    
    # Check if Ollama is running
    try:
        result = subprocess.run(['pgrep', '-f', 'ollama serve'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("🔄 Starting Ollama service...")
            try:
                subprocess.Popen(['ollama', 'serve'], stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
                import time
                time.sleep(3)
                print("✅ Ollama service started")
            except FileNotFoundError:
                print("⚠️  Ollama not found. Install Ollama or use Docker mode.")
        else:
            print("✅ Ollama service is running")
    except Exception as e:
        print(f"⚠️  Could not check/start Ollama: {e}")
    
    # Start PostgreSQL database in Docker
    print("🔄 Starting PostgreSQL database in Docker...")
    try:
        subprocess.run(['docker-compose', 'up', 'db', '-d'], 
                      check=True, capture_output=True)
        print("✅ PostgreSQL database started")
        
        # Wait for database to be ready
        print("⏳ Waiting for database to be ready...")
        import time
        time.sleep(8)
        
    except subprocess.CalledProcessError as e:
        print("❌ Failed to start PostgreSQL database")
        print("Make sure Docker is running and try: docker-compose up db -d")
        return 1
    except FileNotFoundError:
        print("❌ Docker or docker-compose not found")
        return 1
    
    # Run database migrations
    print("🔄 Running database migrations...")
    try:
        env = os.environ.copy()
        env['FLASK_APP'] = 'app.py'
        result = subprocess.run(['flask', 'db', 'upgrade'], 
                              env=env, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Database migrations completed")
        else:
            print("⚠️  Database migrations had issues (this might be normal for first run)")
            print("Error:", result.stderr[:200] + "..." if len(result.stderr) > 200 else result.stderr)
    except subprocess.CalledProcessError:
        print("⚠️  Database migrations failed (this might be normal for first run)")
    except FileNotFoundError:
        print("⚠️  Flask command not found. Database migrations skipped.")
    
    # Start the Flask application
    print("🔄 Starting Flask application...")
    print("📱 Application will be available at: http://localhost:5000")
    print("🔍 Health check: http://localhost:5000/health")
    print("📊 Dashboard: http://localhost:5000/dashboard")
    print("\n🛑 Press Ctrl+C to stop the application")
    print("=" * 60)
    
    try:
        # Set environment variables and start the app
        env = os.environ.copy()
        env.update({
            'FLASK_ENV': 'development',
            'FLASK_DEBUG': '1'
        })
        
        subprocess.run(['python', 'app.py'], env=env)
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down application...")
        return 0
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 