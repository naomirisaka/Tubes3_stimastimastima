# frontend/views.py

import flet as ft
from frontend.controller import get_controller, get_applicant_summary_from_detail_id
import os
import subprocess
import platform
import webbrowser
import fitz 
import re

def extract_pdf_text(pdf_path: str) -> str:
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text.strip()
    except Exception as e:
        return f"Error reading PDF: {e}"
    
def show_pdf_as_text(page: ft.Page, pdf_path: str, applicant_name: str = ""):
    extracted_text = extract_pdf_text(pdf_path)

    section_headers = ["Summary", "Skills", "Experience", "Education", "Accomplishments"]
    for header in section_headers:
        pattern = fr"(?i)^{header}\s*$"
        extracted_text = re.sub(pattern, f"\n{header}", extracted_text, flags=re.MULTILINE)

    dialog = ft.AlertDialog(
        title=ft.Text(f"📄 {applicant_name}'s CV (Text View)"),
        content=ft.Container(
            content=ft.Column([
                ft.Text(extracted_text, selectable=True, size=12)
            ], scroll=ft.ScrollMode.AUTO),
            width=600,
            height=400,
            padding=10,
            bgcolor=ft.Colors.GREY_50,
            border_radius=8
        ),
        actions=[ft.TextButton("Close", on_click=lambda e: close_dialog(page))],
        modal=True
    )

    page.dialog = dialog
    dialog.open = True
    page.update()

# Simple PDF utilities (inline instead of separate module)
def open_pdf_with_system_viewer(pdf_path: str) -> bool:
    """Open PDF with system default viewer."""
    if not pdf_path or not os.path.exists(pdf_path):
        print(f"PDF file not found: {pdf_path}")
        return False
    
    try:
        system = platform.system().lower()
        
        if system == "windows":
            os.startfile(pdf_path)
        elif system == "darwin":  # macOS
            subprocess.run(['open', pdf_path], check=True)
        elif system == "linux":
            subprocess.run(['xdg-open', pdf_path], check=True)
        else:
            webbrowser.open(f'file://{os.path.abspath(pdf_path)}')
        
        print(f"Opened PDF: {pdf_path}")
        return True
        
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return False

def validate_pdf_path(pdf_path: str) -> tuple:
    """Validate PDF path and return status."""
    if not pdf_path:
        return False, "No PDF path provided"
    
    if not os.path.exists(pdf_path):
        return False, f"File not found: {pdf_path}"
    
    if not pdf_path.lower().endswith('.pdf'):
        return False, f"Not a PDF file: {pdf_path}"
    
    return True, "Valid PDF file"

def get_pdf_info(pdf_path: str) -> dict:
    """Get basic PDF file information."""
    if not os.path.exists(pdf_path):
        return {}
    
    try:
        stat = os.stat(pdf_path)
        return {
            "filename": os.path.basename(pdf_path),
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "exists": True
        }
    except Exception as e:
        return {"error": str(e), "exists": False}

def show_pdf_dialog(page: ft.Page, pdf_path: str, applicant_name: str = ""):
    """Show PDF viewing options dialog."""
    print(f"Showing PDF dialog for: {pdf_path}")
    
    # Validate PDF first
    is_valid, message = validate_pdf_path(pdf_path)
    
    if not is_valid:
        # Show error dialog
        error_dialog = ft.AlertDialog(
            title=ft.Text("PDF Error"),
            content=ft.Text(f"Cannot open PDF: {message}"),
            actions=[
                ft.TextButton("OK", on_click=lambda e: close_dialog(page))
            ],
            modal=True
        )
        page.dialog = error_dialog
        error_dialog.open = True
        page.update()
        return
    
    # Get PDF info
    pdf_info = get_pdf_info(pdf_path)
    
    def open_system_and_close(e):
        """Open with system viewer and close dialog."""
        success = open_pdf_with_system_viewer(pdf_path)
        page.snack_bar = ft.SnackBar(
            ft.Text("PDF opened successfully" if success else "Failed to open PDF"),
            bgcolor=ft.Colors.GREEN_400 if success else ft.Colors.RED_400
        )
        page.snack_bar.open = True
        close_dialog(page)
    
    def copy_path_and_close(e):
        """Copy path to clipboard and close dialog."""
        try:
            page.set_clipboard(pdf_path)
            page.snack_bar = ft.SnackBar(
                ft.Text("Path copied to clipboard"),
                bgcolor=ft.Colors.BLUE_400
            )
            page.snack_bar.open = True
        except:
            page.snack_bar = ft.SnackBar(
                ft.Text("Could not copy to clipboard"),
                bgcolor=ft.Colors.RED_400
            )
            page.snack_bar.open = True
        close_dialog(page)
    
    # Create dialog content
    dialog_content = ft.Column([
        # PDF Info
        ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.PICTURE_AS_PDF, color=ft.Colors.RED_600, size=24),
                    ft.Text(pdf_info.get('filename', 'CV.pdf'), 
                           weight=ft.FontWeight.W_500, size=16)
                ], spacing=10),
                ft.Text(f"💾 Size: {pdf_info.get('size_mb', 0)} MB", size=12),
                ft.Text(f"📁 Location: {os.path.dirname(pdf_path)}", size=10, color=ft.Colors.GREY_600),
            ], spacing=5),
            padding=10,
            bgcolor=ft.Colors.BLUE_50,
            border_radius=8
        ),
        
        ft.Divider(),
        
        ft.Text("Choose how to view the PDF:", weight=ft.FontWeight.W_500),
        
        # Viewing options
        ft.Column([
            ft.ElevatedButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.DESCRIPTION, size=20),
                    ft.Text("View as Text")
                ], spacing=10),
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.GREEN_200,
                    color=ft.Colors.GREEN_800,
                    padding=ft.padding.symmetric(horizontal=20, vertical=10)
                ),
                on_click=lambda e: show_pdf_as_text(page, pdf_path, applicant_name),
                width=300
            ),          
            ft.ElevatedButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.PICTURE_AS_PDF, size=20),
                    ft.Text("Open with System PDF Viewer")
                ], spacing=10),
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.BLUE_100,
                    color=ft.Colors.BLUE_800,
                    padding=ft.padding.symmetric(horizontal=20, vertical=10)
                ),
                on_click=open_system_and_close,
                width=300
            ),
            
            ft.ElevatedButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.COPY, size=20),
                    ft.Text("Copy File Path")
                ], spacing=10),
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.PURPLE_100,
                    color=ft.Colors.PURPLE_800,
                    padding=ft.padding.symmetric(horizontal=20, vertical=10)
                ),
                on_click=copy_path_and_close,
                width=300
            ),
        ], spacing=10),
        
        ft.Divider(),
        
        # Path display
        ft.Container(
            content=ft.Column([
                ft.Text("Full Path:", size=12, weight=ft.FontWeight.W_500),
                ft.Text(pdf_path, size=10, color=ft.Colors.GREY_700)
            ], spacing=2),
            padding=8,
            bgcolor=ft.Colors.GREY_50,
            border_radius=4
        )
    ], spacing=10)
    
    # Create and show dialog
    dialog = ft.AlertDialog(
        title=ft.Text(f"📄 {applicant_name}'s CV" if applicant_name else "📄 CV Viewer"),
        content=ft.Container(
            content=dialog_content,
            width=350,
            height=400
        ),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: close_dialog(page))
        ],
        modal=True
    )
    
    page.dialog = dialog
    dialog.open = True
    page.update()
    print(f"PDF dialog shown for: {applicant_name}")

def close_dialog(page: ft.Page):
    """Close any open dialog."""
    if page.dialog:
        page.dialog.open = False
        page.update()

def home_view(page: ft.Page):
    showing_summary = ft.Ref[bool]()
    showing_summary.current = False

    results_per_page = 5
    current_page = 0

    page.padding = ft.padding.only(left=0, right=0, top=0, bottom=20)
    page.scroll = ft.ScrollMode.AUTO

    # Get controller instance
    controller = get_controller()

    result_column = ft.Column()
    stats_text = ft.Text("", size=12, color=ft.Colors.GREY_600)

    # Ref untuk kontrol interaktif
    cv_count = ft.Ref[ft.Slider]()
    cv_input = ft.Ref[ft.TextField]()
    keyword_input = ft.Ref[ft.TextField]()
    algorithm_selector = ft.Ref[ft.Dropdown]()

    def update_cv_input(e):
        cv_input.current.value = str(int(e.control.value))
        page.update()

    def update_slider(e):
        try:
            val = int(e.control.value)
            if 1 <= val <= 50:
                cv_count.current.value = val
                page.update()
        except:
            pass

    last_search_results = []
    last_search_metadata = {}

    def open_cv_dialog(cv_path: str, applicant_name: str = ""):
        """Open CV file with enhanced dialog."""
        print(f"Opening CV dialog for: {applicant_name} - {cv_path}")
        
        if not cv_path:
            page.snack_bar = ft.SnackBar(
                ft.Text("No CV path available"), 
                bgcolor=ft.Colors.RED_400
            )
            page.snack_bar.open = True
            page.update()
            return
        
        # Show the PDF dialog
        show_pdf_dialog(page, cv_path, applicant_name)

    def render_search_metadata():
        """Render search metadata/info (algorithm, time, etc)."""
        if not last_search_metadata:
            return
        
        meta = last_search_metadata
        stats_info = f"🔍 Algorithm: {meta.get('algorithm_used', 'N/A').upper()} | "
        stats_info += f"⏱️ Time: {meta.get('exact_time_ms', 0):.1f}ms | "
        stats_info += f"📄 Scanned: {meta.get('cvs_scanned', 0)} CVs | "
        stats_info += f"🎯 Exact matches: {meta.get('total_exact_matches', 0)}"

        if meta.get('fuzzy_matches_found', 0) > 0:
            stats_info += f" | 🔍 Fuzzy: {meta.get('fuzzy_matches_found', 0)} keywords"
            stats_info += f" | ⏱️ Fuzzy Time: {meta['fuzzy_time_ms']:.1f}ms"

        stats_text.value = stats_info
        result_column.controls.append(
            ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(size=18, color=ft.Colors.BLUE_600),
                            stats_text
                        ], spacing=5),
                        padding=10,
                        bgcolor=ft.Colors.BLUE_50,
                        border_radius=20,
                    )
                ]
            )
        )

    def on_search(e):
        showing_summary.current = False
        keywords = (keyword_input.current.value or "").strip()
        algo = (algorithm_selector.current.value or "").strip()
        top_n = int(cv_count.current.value or 10)

        if not keywords:
            page.snack_bar = ft.SnackBar(ft.Text("Please enter keywords!"), bgcolor=ft.Colors.RED_400)
            page.snack_bar.open = True
            page.update()
            return
        
        if not algo:
            page.snack_bar = ft.SnackBar(ft.Text("Please select an algorithm!"), bgcolor=ft.Colors.RED_400)
            page.snack_bar.open = True
            page.update()
            return

        # Show loading
        result_column.controls.clear()

        if algo == "BM" and len(keywords) <= 3:
            warning = ft.Text(
                "⚠️ Warning: Searching with short keyword (<= 3) using Boyer-Moore may be slow.",
                size=14,
                color=ft.Colors.ORANGE_600,
                text_align=ft.TextAlign.CENTER
            )
            result_column.controls.append(
                ft.Container(
                    content=warning,
                    alignment=ft.alignment.center,
                    padding=10
                )
            )
            
        result_column.controls.append(
            ft.Container(
                content=ft.Row([
                    ft.ProgressRing(width=20, height=20),
                    ft.Text("Searching CVs...", size=16)
                ], alignment=ft.MainAxisAlignment.CENTER),
                padding=20,
                alignment=ft.alignment.center
            )
        )
        page.update()

        try:
            search_result = controller.search_top_matches(keywords, algo, top_n)
            
            nonlocal last_search_results, last_search_metadata
            
            if isinstance(search_result, dict) and "matches" in search_result:
                last_search_results = search_result["matches"]
                last_search_metadata = search_result["metadata"]
            else:
                last_search_results = search_result if search_result else []
                last_search_metadata = {}
            
            current_page = 0
            render_paginated_results()

            
        except Exception as e:
            result_column.controls.clear()
            result_column.controls.append(
                ft.Container(
                    content=ft.Text(f"Search error: {str(e)}", color=ft.Colors.RED_600),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
            page.update()

    def show_summary(detail_id):
        showing_summary.current = True
        if not detail_id:
            page.snack_bar = ft.SnackBar(ft.Text("Invalid CV selection"), bgcolor=ft.Colors.RED_400)
            page.snack_bar.open = True
            page.update()
            return

        # Show loading
        result_column.controls.clear()
        result_column.controls.append(
            ft.Container(
                content=ft.Row([
                    ft.ProgressRing(width=20, height=20),
                    ft.Text("Loading CV summary...", size=16)
                ], alignment=ft.MainAxisAlignment.CENTER),
                padding=20,
                alignment=ft.alignment.center
            )
        )
        page.update()

        try:
            summary = get_applicant_summary_from_detail_id(detail_id)
            if not summary:
                page.snack_bar = ft.SnackBar(ft.Text("Summary not found"), bgcolor=ft.Colors.RED_400)
                page.snack_bar.open = True
                render_paginated_results()
                return

            cv_path = summary.get('cv_path', '')
            pdf_exists = bool(cv_path and os.path.exists(cv_path))
            applicant_name = f"{summary['first_name']} {summary['last_name']}"

            result_column.controls.clear()
            result_column.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            # Header
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.PERSON, size=30, color=ft.Colors.BLUE_600),
                                    ft.Text(applicant_name, size=24, weight=ft.FontWeight.BOLD)
                                ]),
                                bgcolor=ft.Colors.BLUE_50,
                                padding=15,
                                border_radius=10
                            ),
                            
                            # Contact Info
                            ft.Row([
                                ft.Text(f"📞 {summary['phone']}", size=14),
                                ft.Text(f"🏢 {summary['role']}", size=14, weight=ft.FontWeight.W_500)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            
                            ft.Text(f"🏠 {summary['address']}", size=14),
                            
                            # PDF Status
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(
                                        ft.Icons.PICTURE_AS_PDF if pdf_exists else ft.icons.ERROR,
                                        color=ft.Colors.GREEN if pdf_exists else ft.Colors.RED,
                                        size=20
                                    ),
                                    ft.Text(
                                        f"📄 {os.path.basename(cv_path) if pdf_exists else 'PDF Not Available'}",
                                        weight=ft.FontWeight.W_500,
                                        color=ft.Colors.GREEN if pdf_exists else ft.Colors.RED
                                    )
                                ], spacing=10),
                                padding=10,
                                bgcolor=ft.Colors.GREEN_50 if pdf_exists else ft.Colors.RED_50,
                                border_radius=8
                            ),
                            
                            # Summary sections
                            create_summary_section("📝 Summary", summary['summary']),
                            create_summary_section("🧠 Skills", summary['skills']),
                            create_summary_section("💼 Experience", summary['experience']),
                            create_summary_section("🎓 Education", summary['education']),
                            create_summary_section("🏆 Accomplishments", summary['accomplishments']),
                            
                            # Action buttons
                            ft.Row([
                                ft.ElevatedButton(
                                    "📁 View CV", 
                                    on_click=lambda e: open_cv_dialog(cv_path, applicant_name),
                                    style=ft.ButtonStyle(bgcolor=ft.Colors.PURPLE_100),
                                    disabled=not pdf_exists
                                ),
                                ft.ElevatedButton(
                                    "⬅ Back", 
                                    on_click=lambda e: (
                                        setattr(showing_summary, "current", False),
                                        render_paginated_results()
                                    ),
                                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_200)
                                )
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=10)
                        ], spacing=15),
                        padding=20
                    ),
                    elevation=3
                )
            )

            page.controls.clear()
            page.add(build_layout())
            page.update()
            
        except Exception as e:
            result_column.controls.clear()
            result_column.controls.append(
                ft.Container(
                    content=ft.Text(f"Error loading summary: {str(e)}", color=ft.Colors.RED_600),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
            page.controls.clear()
            page.add(build_layout())
            page.update()

    def create_summary_section(title: str, content: str):
        """Create a collapsible CV section with Read more / Show less."""

        original_content = content or ""
        is_empty = not original_content.strip()

        if is_empty:
            content = "Not available"
            is_trimmed = False
        else:
            MAX_LENGTH = 300
            is_trimmed = len(original_content) > MAX_LENGTH
            content = original_content.strip()

        short_content = content[:300] + "..." if is_trimmed else content

        # State
        full_text = ft.Text(content, size=14, color=ft.Colors.GREY_800, visible=False)
        short_text = ft.Text(short_content, size=14, color=ft.Colors.GREY_800, visible=True)
        toggle_btn = ft.Ref[ft.TextButton]()

        def toggle_visibility(e):
            full_text.visible = not full_text.visible
            short_text.visible = not short_text.visible
            toggle_btn.current.text = "Show less" if full_text.visible else "Read more"
            e.page.update()

        section_content = [
            ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_700),
            short_text,
            full_text,
        ]

        if is_trimmed:
            section_content.append(
                ft.Row(
                    [ft.TextButton("Read more", ref=toggle_btn, on_click=toggle_visibility)],
                    alignment=ft.MainAxisAlignment.END
                )
            )

        return ft.Container(
            content=ft.Column(section_content, spacing=5),
            padding=10,
            bgcolor=ft.Colors.GREY_50,
            border_radius=8,
            border=ft.border.all(1, ft.Colors.GREY_300)
        )
    
    # Komponen input
    keyword_input_field = ft.TextField(
        ref=keyword_input,
        width=400,
        label="Enter Keywords",
        hint_text="Example: Python, SQL, React, Machine Learning",
        border_radius=20,
        bgcolor="#F1C6E7",
        filled=True
    )

    algorithm_selector_dropdown = ft.Dropdown(
        ref=algorithm_selector,
        label="Select Algorithm",
        options=[
            ft.dropdown.Option("KMP", "KMP (Knuth-Morris-Pratt)"),
            ft.dropdown.Option("BM", "BM (Boyer-Moore)"),
            ft.dropdown.Option("AC", "AC (Aho-Corasick)")
        ],
        bgcolor="#B7E5DD",
        border_radius=20,
        width=250
    )

    slider_control = ft.Slider(
        ref=cv_count,
        min=1,
        max=50,
        divisions=49,
        label="{value}",
        on_change=update_cv_input,
        width=150,
        value=10
    )

    cv_text_field = ft.TextField(
        ref=cv_input,
        value="10",
        label="Top CVs",
        width=100,
        on_change=update_slider
    )

    slider_row = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            ft.Text("1"),
            slider_control,
            ft.Text("50"),
            cv_text_field
        ]
    )

    control_row = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        controls=[algorithm_selector_dropdown, slider_row],
        spacing=20
    )

    search_button = ft.ElevatedButton(
        text="🔍 Search CVs",
        style=ft.ButtonStyle(
            bgcolor="#FDCEDF", 
            shape=ft.RoundedRectangleBorder(radius=20),
            padding=ft.padding.symmetric(horizontal=30, vertical=15)
        ),
        on_click=on_search
    )
    
    page_info_label = ft.Text("", size=12, color=ft.Colors.GREY_600)

    def go_to_page(target_page):
        nonlocal current_page
        current_page = target_page
        render_paginated_results()

    def render_paginated_results():
        result_column.controls.clear()

        render_search_metadata()

        if not last_search_results:
            result_column.controls.append(
                ft.Container(
                    content=ft.Text("No results found. Try different keywords or algorithms.",
                                    text_align=ft.TextAlign.CENTER),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
            page.update()
            return

        # Hitung total halaman
        total_results = len(last_search_results)
        total_pages = (total_results + results_per_page - 1) // results_per_page

        # Clamp halaman saat ini
        nonlocal current_page
        if current_page >= total_pages:
            current_page = total_pages - 1
        if current_page < 0:
            current_page = 0

        # Ambil hasil sesuai halaman
        start_idx = current_page * results_per_page
        end_idx = min(start_idx + results_per_page, total_results)
        paginated_results = last_search_results[start_idx:end_idx]

        # Tampilkan hasil
        if not paginated_results:
            result_column.controls.append(
                ft.Text("No results found.")
            )
        else:
            for i, cv in enumerate(paginated_results, start=start_idx + 1):
                keyword_display = []
                for keyword, count in cv.get('keywords', {}).items():
                    if count > 0:
                        keyword_display.append(f"{keyword}: {count}")
                
                keyword_text = " | ".join(keyword_display[:3])
                if len(cv.get('keywords', {})) > 3:
                    keyword_text += "..."
                
                # Check if PDF exists
                cv_path = cv.get('cv_path', '')
                pdf_exists = bool(cv_path and os.path.exists(cv_path))
                applicant_name = cv.get('applicant_name', 'Unknown')
                
                result_column.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(f"#{i}", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_600),
                                    ft.Text(applicant_name, size=16, weight=ft.FontWeight.W_500),
                                    ft.Container(
                                        content=ft.Text(f"Score: {cv.get('match', 0)}", 
                                                    color=ft.Colors.WHITE, size=12),
                                        bgcolor=ft.Colors.GREEN_600,
                                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                        border_radius=10
                                    )
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                
                                ft.Text(f"🏢 {cv.get('application_role', 'Not specified')}", 
                                    size=14, color=ft.Colors.GREY_700),
                                
                                ft.Text(f"🎯 {keyword_text}", 
                                    size=12, color=ft.Colors.GREY_600),
                                
                                # PDF Status
                                ft.Row([
                                    ft.Icon(
                                        ft.Icons.PICTURE_AS_PDF if pdf_exists else ft.icons.ERROR,
                                        color=ft.Colors.GREEN if pdf_exists else ft.Colors.RED,
                                        size=16
                                    ),
                                    ft.Text(
                                        "PDF Available" if pdf_exists else "PDF Not Found",
                                        size=10,
                                        color=ft.Colors.GREEN if pdf_exists else ft.Colors.RED
                                    )
                                ], spacing=5),
                                
                                ft.Row([
                                    ft.ElevatedButton(
                                        "📄 Summary", 
                                        on_click=lambda e, detail_id=cv.get('detail_id'): show_summary(detail_id),
                                        style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_100, color=ft.Colors.BLUE_800)
                                    ),
                                    ft.ElevatedButton(
                                        "📁 View CV", 
                                        on_click=lambda e, path=cv_path, name=applicant_name: open_cv_dialog(path, name),
                                        style=ft.ButtonStyle(bgcolor=ft.Colors.PURPLE_100, color=ft.Colors.PURPLE_800),
                                        disabled=not pdf_exists
                                    )
                                    # ft.ElevatedButton(
                                    #     "🚀 Quick Open", 
                                    #     on_click=lambda e, path=cv_path: quick_open_cv(path),
                                    #     style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_100, color=ft.Colors.GREEN_800),
                                    #     disabled=not pdf_exists
                                    # )
                                ], spacing=8)
                            ], spacing=8),
                            padding=15
                        ),
                        elevation=2
                    )
                )

        # ⬇ Pagination Controls
        total_pages = max(1, (len(last_search_results) + results_per_page - 1) // results_per_page)

        page_info_label.value = f"Page {current_page + 1} / {total_pages}"

        pagination_row = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                page_info_label,
                ft.Row([
                    ft.ElevatedButton("Prev", on_click=lambda e: go_to_page(current_page - 1), disabled=current_page == 0),
                    ft.ElevatedButton("Next", on_click=lambda e: go_to_page(current_page + 1), disabled=current_page >= total_pages - 1)
                ])
            ]
        )
        result_column.controls.append(pagination_row)

        page.controls.clear()
        page.add(build_layout())
        page.update()

    def build_layout():
        print("showing_summary is", showing_summary.current)

        navbar = ft.Container(
            bgcolor="#A6DAFF",
            padding=20,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("📄 ATS CV Matcher", size=26, weight=ft.FontWeight.BOLD),
                    ft.Text("by stimastimastima", italic=True)
                ]
            ),
            expand=True,
        )

        welcome_text = ft.Text(
            "Welcome to StimaStimaStima CV Matcher!",
            size=24,
            weight=ft.FontWeight.W_600,
            text_align=ft.TextAlign.CENTER
        )

        return ft.Column(
            controls=([
                navbar
            ] + (
                [
                    ft.Container(welcome_text, alignment=ft.alignment.center),
                    ft.Container(keyword_input_field, alignment=ft.alignment.center),
                    control_row,
                    ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[search_button]),
                ] if not showing_summary.current else [
                    ft.Container(
                        content=ft.Text(
                            "📄 CV Summary",
                            size=32,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER
                        ),
                        alignment=ft.alignment.center,
                        padding=10
                    )
                ]
            ) + [
                ft.Container(result_column, padding=20)
            ]),
            spacing=25
        )

    # Initialize with database stats
    try:
        stats = controller.get_database_stats()
        if stats:
            db_info = f"📊 Database: {stats.get('total_applications', 0)} CVs, {stats.get('total_applicants', 0)} applicants"
            stats_text.value = db_info
    except:
        stats_text.value = "📊 Database: Ready"

    # layout = ft.Column(
    #     controls = (
    #         [navbar]
    #         + (
    #             # Jika tidak sedang lihat summary → tampilkan input
    #             [
    #                 ft.Container(welcome_text, alignment=ft.alignment.center),
    #                 ft.Container(keyword_input_field, alignment=ft.alignment.center),
    #                 control_row,
    #                 ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[search_button]),
    #             ] if not showing_summary.current else [
    #                 ft.Text("📄 CV Summary", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
    #             ]
    #         )
    #         + [ft.Container(result_column, padding=20)]
    #     ),
    #     spacing=25
    # )

    # Tampilkan info database sebagai tampilan awal
    result_column.controls.append(
        ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    content=ft.Row([
                        ft.Icon(size=18, color=ft.Colors.GREY_800),
                        stats_text
                    ], spacing=5),
                    padding=10,
                    bgcolor=ft.Colors.GREY_100,
                    border_radius=20,
                )
            ]
        )
    )

    page.add(build_layout())
