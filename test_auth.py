#!/usr/bin/env python3
"""
Simple authentication test to debug login issues
"""

import streamlit_authenticator as stauth

def test_password_hash():
    print("Testing password hashing...")
    
    # Test password
    password = "secret"
    
    # Generate hash
    hashed = stauth.Hasher([password]).generate()
    print(f"Generated hash for '{password}': {hashed[0]}")
    
    # Test verification
    try:
        # Create authenticator with test credentials
        config = {
            'credentials': {
                'usernames': {
                    'team1': {
                        'email': 'team1@test.com',
                        'name': 'Team 1',
                        'password': hashed[0]
                    }
                }
            },
            'cookie': {
                'name': 'test_cookie',
                'key': 'test_key_12345678901234567890',
                'expiry_days': 30
            },
            'preauthorized': []
        }
        
        authenticator = stauth.Authenticate(
            config['credentials'],
            config['cookie']['name'],
            config['cookie']['key'],
            config['cookie']['expiry_days']
        )
        
        print("Authenticator created successfully")
        print(f"Available usernames: {list(config['credentials']['usernames'].keys())}")
        
        # Test manual verification
        import bcrypt
        test_hash = hashed[0].encode('utf-8')
        test_password = password.encode('utf-8')
        
        if bcrypt.checkpw(test_password, test_hash):
            print("✅ Password verification works!")
        else:
            print("❌ Password verification failed!")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_password_hash()