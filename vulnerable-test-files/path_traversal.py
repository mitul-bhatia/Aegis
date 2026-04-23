"""
Vulnerable Path Traversal Example
This file contains a path traversal vulnerability for testing Aegis
"""
import os

def read_file(filename):
    """
    Read a file from the uploads directory
    VULNERABLE: No path validation
    """
    # VULNERABLE: Direct path concatenation
    file_path = os.path.join("/var/uploads", filename)
    
    with open(file_path, 'r') as f:
        return f.read()

def serve_static_file(filepath):
    """
    Serve a static file
    VULNERABLE: No path sanitization
    """
    # VULNERABLE: User-controlled path
    base_dir = "/var/www/static"
    full_path = base_dir + "/" + filepath
    
    if os.path.exists(full_path):
        with open(full_path, 'rb') as f:
            return f.read()
    return None

def download_user_file(user_id, filename):
    """
    Download user's file
    VULNERABLE: Path traversal possible
    """
    # VULNERABLE: No validation of filename
    user_dir = f"/var/data/users/{user_id}"
    file_path = f"{user_dir}/{filename}"
    
    with open(file_path, 'rb') as f:
        return f.read()

if __name__ == "__main__":
    # Test the functions
    try:
        print(read_file("test.txt"))
    except:
        print("File not found")
