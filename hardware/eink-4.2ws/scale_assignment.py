import os
import network
import ujson

file_path = 'myconfig_assigned_scale.txt'
assigned_scale = ""
assigned_productid = None
product_hash = None


def read_file():
    global assigned_scale, assigned_productid, product_hash
    try:
        data = {}
        with open(file_path, 'r') as file:
            data = ujson.loads(file.readline())            
            assigned_scale = data['scaleid']
            assigned_productid = data['productid']
            product_hash = data['hash']
    except OSError:
        print(f"File {file_path} does not exist or has errors. Using default.")
        assigned_scale = None
        assigned_productid = None
        product_hash = None


    print(f"Data from file {file_path}:")
    print(f"  - scaleid:     {assigned_scale}")
    print(f"  - productid:   {assigned_productid}")
    print(f"  - producthash: {product_hash}")

def write_file(scaleid=None, productid=None, myhash=None):
    global assigned_scale, assigned_productid, product_hash
    with open(file_path, 'w') as file:
        data = {'scaleid': scaleid, 'productid': productid, 'hash': myhash}
        s = ujson.dumps(data)
        file.write(s)
        print(f"data {s} written to file {file_path}")
    assigned_scale = scaleid
    assigned_productid = productid
    product_hash = myhash

def print_status():
    print(f"Read from config file: {file_path}")
    print(f"  {assigned_scale=} {assigned_productid=} {product_hash=}")