import flet as ft
from frontend.controller import search_top_matches, get_applicant_summary_from_path

def home_view(page: ft.Page):
    page.padding = ft.padding.only(left=0, right=0, top=0, bottom=20)
    page.scroll = ft.ScrollMode.AUTO

    result_column = ft.Column()

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
            if 1 <= val <= 999:
                cv_count.current.value = val
                page.update()
        except:
            pass

    last_search_results = []

    def render_search_results():
        result_column.controls.clear()
        for m in last_search_results:
            result_column.controls.append(
                ft.Card(
                    content=ft.Column([
                        ft.Text(f"Match: {m['match']}"),
                        ft.Text(f"Keywords: {m['keywords']}"),
                        ft.TextButton("📄 Summary", on_click=lambda e, p=m['cv_path']: show_summary(p)),
                    ])
                )
            )
        page.update()

    def on_search(e):
        keywords = (keyword_input.current.value or "").strip()
        algo = (algorithm_selector.current.value or "").strip()
        top_n = int(cv_count.current.value or 10)

        nonlocal last_search_results
        last_search_results = search_top_matches(keywords, algo, top_n)
        render_search_results() 


        # matches = search_top_matches(keywords, algo, top_n)

        # result_column.controls.clear()
        # for m in matches:
        #     result_column.controls.append(
        #         ft.Card(
        #             content=ft.Column([
        #                 ft.Text(f"Match: {m['match']}"),
        #                 ft.Text(f"Keywords: {m['keywords']}"),
        #                 ft.TextButton("📄 Summary", on_click=lambda e, p=m['cv_path']: show_summary(p)),
        #             ])
        #         )
        #     )
        # page.update()

    def show_summary(cv_path):
        summary = get_applicant_summary_from_path(cv_path)
        if not summary:
            page.snack_bar = ft.SnackBar(ft.Text("Summary not found"))
            page.update()
            return

        result_column.controls.clear()
        result_column.controls.append(
            ft.Card(
                content=ft.Column([
                    ft.Text(f"👤 {summary['first_name']} {summary['last_name']}"),
                    ft.Text(f"📞 {summary['phone']}"),
                    ft.Text(f"🏠 {summary['address']}"),
                    ft.Text(f"📝 Summary: \n{summary['summary']}"),
                    ft.Text(f"🧠 Skills: \n{summary['skills']}"),
                    ft.Text(f"💼 Experience: \n{summary['experience']}"),
                    ft.Text(f"🎓 Education: \n{summary['education']}"),
                    ft.Text(f"🏆 Accomplishments: \n{summary['accomplishments']}"),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.ElevatedButton("⬅ Back", on_click=go_back_to_home)
                        ]
                    )
                ], spacing=10)
            )
        )
        page.update()

    def go_back_to_home(e):
        render_search_results()

    # UI components
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
        # border_radius=ft.BorderRadius(top_left=0, top_right=0, bottom_left=10, bottom_right=10)
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
        label="Masukkan Keyword",
        hint_text="Contoh: Python, SQL",
        border_radius=20,
        bgcolor="#F1C6E7",
        filled=True
    )

    algorithm_selector_dropdown = ft.Dropdown(
        ref=algorithm_selector,
        label="Pilih Algoritma",
        options=[ft.dropdown.Option("KMP"), ft.dropdown.Option("BM")],
        bgcolor="#B7E5DD",
        border_radius=20,
        width=200
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
                width=150
            ),
            ft.Text("50"),
            ft.TextField(
                ref=cv_input,
                value="10",
                label="Jumlah CV",
                width=100,
                on_change=update_slider
            )
        ]
    )

    control_row = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        controls=[algorithm_selector_dropdown, slider_row]
    )

    search_button = ft.ElevatedButton(
        text="🔍 Search",
        style=ft.ButtonStyle(bgcolor="#FDCEDF", shape=ft.RoundedRectangleBorder(radius=20)),
        on_click=on_search
    )

    layout = ft.Column([
        navbar,
        ft.Container(welcome_text, alignment=ft.alignment.center),
        ft.Container(keyword_input_field, alignment=ft.alignment.center),
        control_row,
        ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[search_button]),
        ft.Container(result_column, padding=20)
    ], spacing=25)

    page.add(layout)
