import os
import network

file_path = 'myconfig_assigned_scale.txt'
assigned_scale = ""
assigned_productid = None
product_hash = None


def read_file():
    global assigned_scale
    try:
        with open(file_path, 'r') as file:
            assigned_scale = file.readline().strip()  # Read the first line and strip any extra whitespace
            assigned_productid = file.readline().strip()  # Read the first line and strip any extra whitespace
            product_hash = file.readline().strip()  # Read the first line and strip any extra whitespace
    except OSError:
        print("File myconfig_assigned_scale.txt does not exist or has errors. Using default.")
        assigned_scale = " "
        assigned_productid = None
        product_hash = None


    print(f"Data from file {file_path}:")
    print(f"  - scaleid:     {assigned_scale}")
    print(f"  - productid:   {assigned_productid}")
    print(f"  - producthash: {product_hash}")
