# main flet app
import flet as ft
from frontend.views import home_view

def main(page: ft.Page):
    page.title = "ATS CV Finder"
    home_view(page)

if __name__ == "__main__":
    ft.app(target=main)