#!/usr/bin/python3

import mariadb
import requests
import sys
import argparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration for local MariaDB
config = {
    'host': '192.168.10.10',
    'user': 'user_shop_control',
    'password': 'wlLvMOR4FStMEzzN',
    'database': 'zeitlos'
}

# API URL and Secret Key
api_url = "https://www.hemmes24.de/code/insert_invoices.php"
secret_key = "your_secret_key"  # This should be the same as configured in your PHP script for authentication
column_names = ""

def fetch_data(query):
    global column_names
    """Fetches data from the local database based on the provided SQL query."""
    data = []
    try:
        # Connect to MariaDB
        conn = mariadb.connect(**config)
        cur = conn.cursor()
        cur.execute(query)
        
        # Append all rows to a list
        data = [row for row in cur]

        column_names = next(zip(*cur.description))
        logging.info(f"{column_names=}")
        cur.close()
        conn.close()
        return data
    except mariadb.Error as e:
        logging.error(f"Error connecting to MariaDB: {e}")
        sys.exit(1)

def send_data(data, table_name):
    """Sends data to the remote API."""
    for row in data:
        payload = {f"{col_name}": value for col_name, value in zip(column_names, row)}
        payload['table'] = table_name  # This helps the PHP script to handle different tables appropriately
        payload['secret_key'] = secret_key  # Add the secret key to the payload for security
        logging.debug(f"Data will be send with payload: {payload}")
        response = requests.post(api_url, data=payload)
        logging.info(f"Data sent to {api_url}: {response.text}")

def reset_tables():
    """Sends a command to the remote API to reset the tables."""
    response = requests.post(api_url, data={"reset": "true", "secret_key": secret_key})
    logging.info(f"Tables reset command sent: {response.text}")

def main():
    # Setup argument parser
    parser = argparse.ArgumentParser(description='Synchronize local MariaDB data to a remote MySQL database.')
    parser.add_argument('--reset', action='store_true', help='Reset the remote database tables before syncing.')
    args = parser.parse_args()

    if args.reset:
        reset_tables()

    # Define your SQL queries here
    invoices_query = "SELECT * FROM Invoices"# WHERE synced=0"
    # Fetch and send data
    invoice_data = fetch_data(invoices_query)
    send_data(invoice_data, "Invoices")

    invoice_products_query = "SELECT * FROM InvoiceProducts"# WHERE synced=0"
    invoice_products_data = fetch_data(invoice_products_query)
    send_data(invoice_products_data, "InvoiceProducts")

if __name__ == "__main__":
    main()
