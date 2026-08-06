"""
Device Fingerprinting System
Generates and manages device fingerprints for anti-abuse
Uses browser fingerprinting + IP tracking + device storage
"""
import hashlib
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        import codecs
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except Exception:
        pass

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Optional[Client] = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None


class DeviceFingerprint:
    """
    Device fingerprinting for anti-abuse
    Generates unique identifiers based on browser characteristics
    """
    
    @staticmethod
    def generate_fingerprint(fingerprint_data: Dict) -> str:
        """
        Generate a device fingerprint hash from browser characteristics
        
        Args:
            fingerprint_data: Dict containing user_agent, screen_resolution, timezone, language
        
        Returns:
            SHA256 hash of the fingerprint data
        """
        # Create a normalized string from the data
        fingerprint_string = "|".join([
            fingerprint_data.get('user_agent', ''),
            fingerprint_data.get('screen_resolution', ''),
            fingerprint_data.get('timezone', ''),
            fingerprint_data.get('language', ''),
            fingerprint_data.get('platform', ''),
            fingerprint_data.get('color_depth', ''),
            fingerprint_data.get('pixel_ratio', '')
        ])
        
        # Generate SHA256 hash
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()
    
    @staticmethod
    def is_suspicious_device_count(user_email: str, new_fingerprint: str) -> tuple[bool, str]:
        """
        Check if user has too many devices in short time
        
        Args:
            user_email: User's email
            new_fingerprint: New device fingerprint
        
        Returns:
            (is_suspicious, reason)
        """
        if not supabase:
            return False, ""
        
        try:
            # Get all device fingerprints for this user in last 24 hours
            time_threshold = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            
            res = supabase.table('device_fingerprints') \
                .select('*') \
                .eq('user_email', user_email) \
                .gte('last_seen', time_threshold) \
                .execute()
            
            devices = res.data or []
            
            # Count unique fingerprints
            unique_fingerprints = set(d['fingerprint_hash'] for d in devices)
            unique_fingerprints.add(new_fingerprint)
            
            # If more than 3 devices in 24 hours, suspicious
            if len(unique_fingerprints) > 3:
                return True, f"Multiple devices detected: {len(unique_fingerprints)} in 24 hours"
            
            # If same fingerprint from different IP, suspicious
            existing_devices = [d for d in devices if d['fingerprint_hash'] == new_fingerprint]
            if existing_devices:
                ips = set(d['ip_address'] for d in existing_devices)
                if len(ips) > 2:
                    return True, f"Same device from multiple IPs: {len(ips)} in 24 hours"
            
            return False, ""
            
        except Exception as e:
            print(f"Error checking device count: {e}")
            return False, ""
    
    @staticmethod
    def register_device(user_email: str, fingerprint_data: Dict, ip_address: str):
        """
        Register a device for a user
        
        Args:
            user_email: User's email
            fingerprint_data: Browser characteristics
            ip_address: User's IP address
        """
        if not supabase:
            return
        
        try:
            fingerprint_hash = DeviceFingerprint.generate_fingerprint(fingerprint_data)
            
            # Check if this device already exists
            existing = supabase.table('device_fingerprints') \
                .select('*') \
                .eq('user_email', user_email) \
                .eq('fingerprint_hash', fingerprint_hash) \
                .execute()
            
            if existing.data:
                # Update last_seen
                supabase.table('device_fingerprints') \
                    .update({
                        'last_seen': datetime.now(timezone.utc).isoformat(),
                        'ip_address': ip_address
                    }) \
                    .eq('id', existing.data[0]['id']) \
                    .execute()
            else:
                # Insert new device
                # Check if this should be primary (first device)
                all_devices = supabase.table('device_fingerprints') \
                    .select('*') \
                    .eq('user_email', user_email) \
                    .execute()
                
                is_primary = len(all_devices.data) == 0
                
                supabase.table('device_fingerprints') \
                    .insert({
                        'user_email': user_email,
                        'fingerprint_hash': fingerprint_hash,
                        'user_agent': fingerprint_data.get('user_agent'),
                        'screen_resolution': fingerprint_data.get('screen_resolution'),
                        'timezone': fingerprint_data.get('timezone'),
                        'language': fingerprint_data.get('language'),
                        'ip_address': ip_address,
                        'is_primary': is_primary,
                        'last_seen': datetime.now(timezone.utc).isoformat()
                    }) \
                    .execute()
            
            # Log suspicious activity if needed
            is_suspicious, reason = DeviceFingerprint.is_suspicious_device_count(user_email, fingerprint_hash)
            if is_suspicious:
                supabase.table('suspicious_activity') \
                    .insert({
                        'user_email': user_email,
                        'activity_type': 'multiple_devices',
                        'description': reason,
                        'severity': 'medium',
                        'ip_address': ip_address,
                        'device_fingerprint': fingerprint_hash
                    }) \
                    .execute()
            
        except Exception as e:
            print(f"Error registering device: {e}")
    
    @staticmethod
    def verify_device(user_email: str, fingerprint_data: Dict, ip_address: str) -> tuple[bool, str]:
        """
        Verify if a device is allowed for this user
        
        Args:
            user_email: User's email
            fingerprint_data: Browser characteristics
            ip_address: User's IP address
        
        Returns:
            (is_allowed, reason)
        """
        if not supabase:
            return True, ""
        
        try:
            fingerprint_hash = DeviceFingerprint.generate_fingerprint(fingerprint_data)
            
            # Check if this device is registered
            existing = supabase.table('device_fingerprints') \
                .select('*') \
                .eq('user_email', user_email) \
                .eq('fingerprint_hash', fingerprint_hash) \
                .execute()
            
            if existing.data:
                # Device is registered, check if account is locked
                user = supabase.table('users') \
                    .select('status') \
                    .eq('email', user_email) \
                    .single() \
                    .execute()
                
                if user.data and user.data.get('status') == 'locked':
                    return False, "Account is locked due to suspicious activity"
                
                return True, ""
            
            # New device - check if suspicious
            is_suspicious, reason = DeviceFingerprint.is_suspicious_device_count(user_email, fingerprint_hash)
            if is_suspicious:
                return False, f"Suspicious activity: {reason}"
            
            # Allow new device but register it
            DeviceFingerprint.register_device(user_email, fingerprint_data, ip_address)
            return True, ""
            
        except Exception as e:
            print(f"Error verifying device: {e}")
            return True, ""  # Allow on error to not block legitimate users
    
    @staticmethod
    def get_user_devices(user_email: str) -> list:
        """
        Get all devices for a user
        
        Args:
            user_email: User's email
        
        Returns:
            List of device records
        """
        if not supabase:
            return []
        
        try:
            res = supabase.table('device_fingerprints') \
                .select('*') \
                .eq('user_email', user_email) \
                .order('last_seen', desc=True) \
                .execute()
            
            return res.data or []
            
        except Exception as e:
            print(f"Error getting user devices: {e}")
            return []


# Test the device fingerprinting system
if __name__ == "__main__":
    print("=== Device Fingerprinting System ===")
    
    # Test fingerprint generation
    test_data = {
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'screen_resolution': '1920x1080',
        'timezone': 'Asia/Kolkata',
        'language': 'en-US',
        'platform': 'Win32',
        'color_depth': '24',
        'pixel_ratio': '1'
    }
    
    fingerprint = DeviceFingerprint.generate_fingerprint(test_data)
    print(f"\nGenerated fingerprint: {fingerprint[:16]}...")
    
    # Test device verification
    is_allowed, reason = DeviceFingerprint.verify_device(
        "test@example.com",
        test_data,
        "192.168.1.1"
    )
    print(f"Device verification: {is_allowed}")
    if reason:
        print(f"Reason: {reason}")
    
    print("\n=== Device Fingerprinting System Working ===")