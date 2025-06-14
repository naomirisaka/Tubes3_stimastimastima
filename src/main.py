# main.py - Entry point untuk ATS Application

import flet as ft
import sys
import os

# Add paths untuk import modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'frontend'))
sys.path.insert(0, os.path.join(current_dir, 'backend'))
sys.path.insert(0, os.path.join(current_dir, 'data_extractor'))

def main(page: ft.Page):
    """Main application entry point"""
    
    # Configure page
    page.title = "ATS CV Matcher - Matchify"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1200
    page.window_height = 800
    page.window_resizable = True
    page.scroll = ft.ScrollMode.AUTO
    
    # Import views after path setup
    try:
        from views import home_view
        
        # Initialize the home view
        home_view(page)
        
    except ImportError as e:
        # Show error if imports fail
        error_text = ft.Text(
            f"Error importing modules: {e}\n\n"
            "Please ensure all required modules are installed:\n"
            "- flet\n"
            "- PyMuPDF (fitz)\n"
            "- mysql-connector-python",
            color=ft.Colors.RED,
            size=16
        )
        page.add(ft.Container(
            content=error_text,
            padding=20,
            alignment=ft.alignment.center
        ))
    
    except Exception as e:
        # Show general error
        error_text = ft.Text(
            f"Application error: {e}",
            color=ft.Colors.RED,
            size=16
        )
        page.add(ft.Container(
            content=error_text,
            padding=20,
            alignment=ft.alignment.center
        ))

if __name__ == "__main__":
    print("🚀 Starting ATS CV Matcher Application...")
    print("📄 Matchify - Advanced CV Matching System")
    print("-" * 50)
    
    try:
        # Run the Flet app
        ft.app(target=main)
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Ensure Flet is installed: pip install flet")
        print("2. Check if all required modules are present")
        print("3. Verify database connection settings")