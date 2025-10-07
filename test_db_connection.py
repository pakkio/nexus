#!/usr/bin/env python3
"""
Test script to verify database connection in app.py
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_db_connection():
    """Test database connection directly"""
    print("Testing database connection...")
    
    # Import after loading environment variables
    from db_manager import DbManager
    
    # Get configuration from environment
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'nexus_rpg'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'connection_timeout': int(os.getenv('DB_TIMEOUT', 10))
    }
    
    use_mockup = os.getenv('NEXUS_USE_MOCKUP', 'true').lower() == 'true'
    
    print(f"Using mockup mode: {use_mockup}")
    if not use_mockup:
        print(f"Database config: {db_config}")
    
    try:
        # Create DbManager instance
        db_manager = DbManager(config=db_config, use_mockup=use_mockup)
        
        # Test connection
        conn = db_manager.connect()
        print("✓ Database connection successful!")
        
        if not use_mockup:
            # Test schema
            db_manager.ensure_db_schema()
            print("✓ Database schema verified/created!")
            
            # Test basic operations
            story = db_manager.get_storyboard()
            print(f"✓ Storyboard loaded: {story.get('name', 'Unknown')}")
        
        # Close connection
        if conn and hasattr(conn, 'close'):
            conn.close()
        
        return True
        
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def test_app_initialization():
    """Test app.py initialization"""
    print("\nTesting app initialization...")
    
    try:
        from app import initialize_game_system
        game_system = initialize_game_system()
        print("✓ App initialized successfully!")
        print(f"✓ Game system has DB: {hasattr(game_system, 'db')}")
        return True
    except Exception as e:
        print(f"✗ App initialization failed: {e}")
        return False

if __name__ == "__main__":
    print("Nexus RPG - Database Connection Test")
    print("="*50)
    
    db_success = test_db_connection()
    app_success = test_app_initialization()
    
    print("\n" + "="*50)
    if db_success and app_success:
        print("✓ All tests passed! Database is ready for use.")
        sys.exit(0)
    else:
        print("✗ Some tests failed.")
        sys.exit(1)