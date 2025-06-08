# frontend/views.py

import flet as ft
from frontend.controller import get_controller, get_applicant_summary_from_detail_id
import os
import subprocess

def home_view(page: ft.Page):
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

    def render_search_results():
        result_column.controls.clear()
        
        # Show search metadata if available
        if last_search_metadata:
            meta = last_search_metadata
            stats_info = f"🔍 Algorithm: {meta.get('algorithm_used', 'N/A').upper()} | "
            stats_info += f"⏱️ Time: {meta.get('exact_time_ms', 0):.1f}ms | "
            stats_info += f"📄 Scanned: {meta.get('cvs_scanned', 0)} CVs | "
            stats_info += f"🎯 Exact matches: {meta.get('total_exact_matches', 0)}"
            
            if meta.get('fuzzy_matches_found', 0) > 0:
                stats_info += f" | 🔍 Fuzzy: {meta.get('fuzzy_matches_found', 0)} keywords"
            
            stats_text.value = stats_info
            result_column.controls.append(
                ft.Container(
                    content=stats_text,
                    padding=10,
                    bgcolor=ft.Colors.BLUE_50,
                    border_radius=10,
                    margin=ft.margin.only(bottom=10)
                )
            )
        
        # Show CV results
        for i, cv in enumerate(last_search_results, 1):
            # Create keyword breakdown display
            keyword_display = []
            for keyword, count in cv.get('keywords', {}).items():
                if count > 0:
                    keyword_display.append(f"{keyword}: {count}")
            
            keyword_text = " | ".join(keyword_display[:3])  # Show top 3 keywords
            if len(cv.get('keywords', {})) > 3:
                keyword_text += "..."
            
            result_column.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(f"#{i}", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_600),
                                ft.Text(cv.get('applicant_name', 'Unknown'), 
                                        size=16, weight=ft.FontWeight.W_500),
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
                            
                            ft.Row([
                                ft.ElevatedButton(
                                    "📄 View Summary", 
                                    on_click=lambda e, detail_id=cv.get('detail_id'): show_summary(detail_id),
                                    style=ft.ButtonStyle(
                                        bgcolor=ft.Colors.BLUE_100,
                                        color=ft.Colors.BLUE_800
                                    )
                                ),
                                ft.ElevatedButton(
                                    "📁 Open CV", 
                                    on_click=lambda e, cv_path=cv.get('cv_path'): open_cv_file(cv_path),
                                    style=ft.ButtonStyle(
                                        bgcolor=ft.Colors.GREEN_100,
                                        color=ft.Colors.GREEN_800
                                    )
                                ) if cv.get('cv_path') else None
                            ], spacing=10)
                        ], spacing=8),
                        padding=15
                    ),
                    elevation=2
                )
            )
        
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

    def on_search(e):
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
            # Perform search using new backend
            search_result = controller.search_top_matches(keywords, algo, top_n)
            
            nonlocal last_search_results, last_search_metadata
            
            if isinstance(search_result, dict) and "matches" in search_result:
                last_search_results = search_result["matches"]
                last_search_metadata = search_result["metadata"]
            else:
                last_search_results = search_result if search_result else []
                last_search_metadata = {}
            
            render_search_results()
            
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
                render_search_results()
                return

            result_column.controls.clear()
            result_column.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            # Header
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.PERSON, size=30, color=ft.Colors.BLUE_600),
                                    ft.Text(f"{summary['first_name']} {summary['last_name']}", 
                                           size=24, weight=ft.FontWeight.BOLD)
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
                            
                            # Sections
                            create_summary_section("📝 Summary", summary['summary']),
                            create_summary_section("🧠 Skills", summary['skills']),
                            create_summary_section("💼 Experience", summary['experience']),
                            create_summary_section("🎓 Education", summary['education']),
                            create_summary_section("🏆 Accomplishments", summary['accomplishments']),
                            
                            # Action buttons
                            ft.Row([
                                ft.ElevatedButton(
                                    "⬅ Back to Results", 
                                    on_click=go_back_to_results,
                                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREY_200)
                                ),
                                ft.ElevatedButton(
                                    "📁 Open CV File", 
                                    on_click=lambda e: open_cv_file(summary.get('cv_path')),
                                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_200)
                                ) if summary.get('cv_path') else None
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=10)
                        ], spacing=15),
                        padding=20
                    ),
                    elevation=3
                )
            )
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
            page.update()

    def create_summary_section(title, content):
        if not content or content.strip() == "":
            content = "Not available"
        
        # Truncate long content
        display_content = content[:300] + "..." if len(content) > 300 else content
        
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_700),
                ft.Text(display_content, size=14, color=ft.Colors.GREY_800)
            ], spacing=5),
            padding=10,
            bgcolor=ft.Colors.GREY_50,
            border_radius=8,
            border=ft.border.all(1, ft.Colors.GREY_300)
        )

    def go_back_to_results(e):
        render_search_results()

    def open_cv_file(cv_path):
        if not cv_path or not os.path.exists(cv_path):
            page.snack_bar = ft.SnackBar(ft.Text("CV file not found"), bgcolor=ft.Colors.RED_400)
            page.snack_bar.open = True
            page.update()
            return
        
        try:
            if os.name == 'nt':  # Windows
                os.startfile(cv_path)
            elif os.name == 'posix':  # macOS and Linux
                subprocess.call(['open' if 'darwin' in os.uname().sysname.lower() else 'xdg-open', cv_path])
            
            page.snack_bar = ft.SnackBar(ft.Text("Opening CV file..."), bgcolor=ft.Colors.GREEN_400)
            page.snack_bar.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error opening file: {str(e)}"), bgcolor=ft.Colors.RED_400)
            page.snack_bar.open = True
            page.update()

    # UI Components
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
        "Welcome to the Smartest CV Finder in the Galaxy 🚀",
        size=20,
        weight=ft.FontWeight.W_600,
        text_align=ft.TextAlign.CENTER
    )

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

    slider_row = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            ft.Text("1"),
            ft.Slider(
                ref=cv_count,
                min=1,
                max=50,
                divisions=49,
                label="{value}",
                on_change=update_cv_input,
                width=150,
                value=10
            ),
            ft.Text("50"),
            ft.TextField(
                ref=cv_input,
                value="10",
                label="Top CVs",
                width=100,
                on_change=update_slider
            )
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

    # Initialize with database stats
    try:
        stats = controller.get_database_stats()
        if stats:
            db_info = f"📊 Database: {stats.get('total_applications', 0)} CVs, {stats.get('total_applicants', 0)} applicants"
            stats_text.value = db_info
    except:
        stats_text.value = "📊 Database: Ready"

    layout = ft.Column([
        navbar,
        ft.Container(welcome_text, alignment=ft.alignment.center),
        ft.Container(keyword_input_field, alignment=ft.alignment.center),
        control_row,
        ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[search_button]),
        ft.Container(stats_text, alignment=ft.alignment.center, padding=ft.padding.only(top=10)),
        ft.Container(result_column, padding=20)
    ], spacing=25)

    page.add(layout)