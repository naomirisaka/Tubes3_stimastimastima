import flet as ft

def home_view(page: ft.Page):
    page.padding = ft.padding.only(left=0, right=0, top=0, bottom=30)

    page.title = "🎯 ATS CV Matcher"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.padding = 30
    page.scroll = ft.ScrollMode.AUTO

    # Fungsi untuk snackbar
    def show_snack(e):
        page.snack_bar = ft.SnackBar(content=ft.Text("Mencari..."))
        page.update()

    # State CV count (slider + textfield sync)
    cv_count = ft.Ref[ft.Slider]()
    cv_input = ft.Ref[ft.TextField]()

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

    # Navbar
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
        border_radius=ft.BorderRadius(top_left=0, top_right=0, bottom_left=10, bottom_right=10)
    )

    # Welcome text
    welcome_text = ft.Text(
        "Welcome to the Smartest CV Finder in the Galaxy 🚀",
        size=20,
        weight=ft.FontWeight.W_600,
        text_align=ft.TextAlign.CENTER
    )

    # Keyword input
    keyword_input = ft.Container(
        content=ft.TextField(
            width=400,
            label="Masukkan Keyword",
            hint_text="Contoh: Python, SQL",
            border_radius=20,
            bgcolor="#F1C6E7",
            filled=True
        ),
        alignment=ft.alignment.center
    )

    # Dropdown + slider
    algorithm_selector = ft.Dropdown(
        label="Pilih Algoritma",
        options=[ft.dropdown.Option("KMP"), ft.dropdown.Option("BM")],
        bgcolor="#B7E5DD",
        border_radius=20,
        width=200
    )

    slider_row = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        # spacing=5,
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
        controls=[algorithm_selector, slider_row]
    )

    # Search button
    search_button = ft.ElevatedButton(
        text="🔍 Search",
        style=ft.ButtonStyle(bgcolor="#FDCEDF", shape=ft.RoundedRectangleBorder(radius=20)),
        on_click=show_snack
    )

    button_row = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        controls=[search_button]
    )

    layout = ft.Column([
        navbar,
        ft.Container(welcome_text, alignment=ft.alignment.center),
        keyword_input,
        control_row,
        button_row
    ], spacing=25)

    page.add(layout)
