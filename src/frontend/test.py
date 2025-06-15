from frontend.controller import get_controller

controller = get_controller()

profile = {
    "first_name": "Budi",
    "last_name": "Santoso",
    "date_of_birth": "1994-05-23",
    "address": "Jl. Mawar No. 10",
    "phone_number": "081234567890"
}

result = controller.extract_and_insert_cv("../data/ENGINEERING/10030015.pdf", profile, "Software Engineer")
print(result)
# from frontend.controller import get_controller

# controller = get_controller()
# result = controller.preload_and_extract_all_cvs()
# print(result)