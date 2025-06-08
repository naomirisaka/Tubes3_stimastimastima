# frontend/pdf_utils.py

import os
import subprocess
import platform
import webbrowser
from pathlib import Path

def open_pdf_with_system_viewer(pdf_path: str) -> bool:
    """
    Open PDF with system default viewer.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not pdf_path or not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return False
    
    try:
        system = platform.system().lower()
        
        if system == "windows":
            # Windows - use os.startfile
            os.startfile(pdf_path)
            
        elif system == "darwin":  # macOS
            # macOS - use 'open' command
            subprocess.run(['open', pdf_path], check=True)
            
        elif system == "linux":
            # Linux - use xdg-open
            subprocess.run(['xdg-open', pdf_path], check=True)
            
        else:
            # Fallback - try webbrowser
            webbrowser.open(f'file://{os.path.abspath(pdf_path)}')
        
        print(f"✅ Opened PDF: {pdf_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error opening PDF: {e}")
        return False

def open_pdf_in_browser(pdf_path: str) -> bool:
    """
    Open PDF in web browser (alternative method).
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not pdf_path or not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return False
    
    try:
        # Convert to absolute path and open in browser
        abs_path = os.path.abspath(pdf_path)
        file_url = f'file:///{abs_path.replace(os.sep, "/")}'
        webbrowser.open(file_url)
        print(f"✅ Opened PDF in browser: {pdf_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error opening PDF in browser: {e}")
        return False

def validate_pdf_path(pdf_path: str) -> tuple[bool, str]:
    """
    Validate PDF path and return status.
    
    Args:
        pdf_path: Path to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not pdf_path:
        return False, "No PDF path provided"
    
    if not os.path.exists(pdf_path):
        return False, f"File not found: {pdf_path}"
    
    if not pdf_path.lower().endswith('.pdf'):
        return False, f"Not a PDF file: {pdf_path}"
    
    try:
        # Check if file is readable
        with open(pdf_path, 'rb') as f:
            f.read(4)  # Try to read first 4 bytes
        return True, "Valid PDF file"
        
    except Exception as e:
        return False, f"Cannot read file: {e}"

def get_pdf_info(pdf_path: str) -> dict:
    """
    Get basic PDF file information.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        dict: PDF information
    """
    if not os.path.exists(pdf_path):
        return {}
    
    try:
        stat = os.stat(pdf_path)
        return {
            "filename": os.path.basename(pdf_path),
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified": stat.st_mtime,
            "exists": True
        }
    except Exception as e:
        return {"error": str(e), "exists": False}