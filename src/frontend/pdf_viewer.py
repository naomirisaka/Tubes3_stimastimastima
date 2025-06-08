# frontend/pdf_viewer.py

import flet as ft
import os
import base64
from pdf_utils import validate_pdf_path, get_pdf_info, open_pdf_with_system_viewer

class PDFViewerDialog:
    """PDF Viewer Dialog for displaying PDFs within the app."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.dialog = None
    
    def show_pdf(self, pdf_path: str, applicant_name: str = ""):
        """
        Show PDF in a dialog.
        
        Args:
            pdf_path: Path to the PDF file
            applicant_name: Name of the applicant (for title)
        """
        # Validate PDF first
        is_valid, message = validate_pdf_path(pdf_path)
        
        if not is_valid:
            self._show_error_dialog(f"Cannot open PDF: {message}")
            return
        
        # Get PDF info
        pdf_info = get_pdf_info(pdf_path)
        
        # Create dialog content
        dialog_content = self._create_pdf_dialog_content(pdf_path, applicant_name, pdf_info)
        
        # Create and show dialog
        self.dialog = ft.AlertDialog(
            title=ft.Text(f"CV: {applicant_name}" if applicant_name else "CV Viewer"),
            content=dialog_content,
            actions=[
                ft.TextButton("Open Externally", on_click=lambda e: self._open_external(pdf_path)),
                ft.TextButton("Close", on_click=self._close_dialog)
            ],
            modal=True,
            adaptive=True
        )
        
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()
    
    def _create_pdf_dialog_content(self, pdf_path: str, applicant_name: str, pdf_info: dict) -> ft.Container:
        """Create the content for the PDF dialog."""
        
        content_items = []
        
        # PDF Info
        if pdf_info:
            info_text = f"📄 {pdf_info.get('filename', 'Unknown')}\n"
            info_text += f"💾 Size: {pdf_info.get('size_mb', 0)} MB"
            
            content_items.append(
                ft.Container(
                    content=ft.Text(info_text, size=12),
                    padding=10,
                    bgcolor=ft.Colors.BLUE_50,
                    border_radius=5
                )
            )
        
        # PDF Viewer Options
        content_items.extend([
            ft.Divider(),
            
            ft.Text("Choose how to view the PDF:", weight=ft.FontWeight.W_500),
            
            ft.ElevatedButton(
                "🖥️ Open in System PDF Viewer",
                icon=ft.Icons.OPEN_IN_NEW,
                on_click=lambda e: self._open_external(pdf_path),
                style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_100)
            ),
            
            ft.ElevatedButton(
                "🌐 Open in Web Browser", 
                icon=ft.Icons.WEB,
                on_click=lambda e: self._open_in_browser(pdf_path),
                style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_100)
            ),
            
            ft.Divider(),
            
            ft.Text(f"📁 Path: {pdf_path}", size=10, color=ft.Colors.GREY_600),
        ])
        
        return ft.Container(
            content=ft.Column(content_items, spacing=10),
            width=400,
            height=300
        )
    
    def _open_external(self, pdf_path: str):
        """Open PDF in external viewer."""
        success = open_pdf_with_system_viewer(pdf_path)
        
        if success:
            self.page.snack_bar = ft.SnackBar(
                ft.Text("PDF opened in external viewer"), 
                bgcolor=ft.Colors.GREEN_400
            )
        else:
            self.page.snack_bar = ft.SnackBar(
                ft.Text("Failed to open PDF"), 
                bgcolor=ft.Colors.RED_400
            )
        
        self.page.snack_bar.open = True
        self.page.update()
        self._close_dialog()
    
    def _open_in_browser(self, pdf_path: str):
        """Open PDF in web browser."""
        from pdf_utils import open_pdf_in_browser
        
        success = open_pdf_in_browser(pdf_path)
        
        if success:
            self.page.snack_bar = ft.SnackBar(
                ft.Text("PDF opened in browser"), 
                bgcolor=ft.Colors.GREEN_400
            )
        else:
            self.page.snack_bar = ft.SnackBar(
                ft.Text("Failed to open PDF in browser"), 
                bgcolor=ft.Colors.RED_400
            )
        
        self.page.snack_bar.open = True
        self.page.update()
        self._close_dialog()
    
    def _show_error_dialog(self, error_message: str):
        """Show error dialog."""
        error_dialog = ft.AlertDialog(
            title=ft.Text("PDF Error"),
            content=ft.Text(error_message),
            actions=[ft.TextButton("OK", on_click=lambda e: self._close_error_dialog())],
            modal=True
        )
        
        self.page.dialog = error_dialog
        error_dialog.open = True
        self.page.update()
    
    def _close_error_dialog(self):
        """Close error dialog."""
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()
    
    def _close_dialog(self, e=None):
        """Close the PDF dialog."""
        if self.dialog:
            self.dialog.open = False
            self.page.update()

class PDFPreviewCard:
    """Simple PDF preview card component."""
    
    def __init__(self, pdf_path: str, applicant_name: str = ""):
        self.pdf_path = pdf_path
        self.applicant_name = applicant_name
    
    def create_card(self) -> ft.Card:
        """Create a PDF preview card."""
        pdf_info = get_pdf_info(self.pdf_path)
        is_valid, message = validate_pdf_path(self.pdf_path)
        
        if not is_valid:
            return ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED, size=30),
                        ft.Text("PDF Not Available", color=ft.Colors.RED),
                        ft.Text(message, size=10, color=ft.Colors.GREY)
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
        
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.PICTURE_AS_PDF, color=ft.Colors.RED_600, size=40),
                    ft.Text(
                        pdf_info.get('filename', 'CV.pdf'), 
                        weight=ft.FontWeight.W_500,
                        text_align=ft.TextAlign.CENTER
                    ),
                    ft.Text(
                        f"{pdf_info.get('size_mb', 0)} MB", 
                        size=12, 
                        color=ft.Colors.GREY_600
                    ),
                    ft.ElevatedButton(
                        "Open PDF",
                        icon=ft.Icons.OPEN_IN_NEW,
                        on_click=lambda e: open_pdf_with_system_viewer(self.pdf_path)
                    )
                ], 
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10),
                padding=20,
                width=200,
                height=150,
                alignment=ft.alignment.center
            )
        )