#!/usr/bin/python3

import mariadb
import requests
import sys
import argparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DB Sync local and remote via HTTP")

# Setup argument parser
parser = argparse.ArgumentParser(description='Synchronize local MariaDB data to a remote MySQL database.')
parser.add_argument('--reset', action='store_true', help='Reset the remote database tables before syncing.')
parser.add_argument("-v", "--verbosity", help="increase output verbosity", default=0, action="count")
args = parser.parse_args()

logger.setLevel(logging.WARNING-(args.verbosity * 10 if args.verbosity <= 2 else 20))

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


def fetch_data(query):
    global column_names
    """Fetches data from the local database based on the provided SQL query."""
    data = []

    # Connect to MariaDB
    conn = mariadb.connect(**config)
    cur = conn.cursor()
    cur.execute(query)
    
    # Append all rows to a list
    data = [row for row in cur]

    column_names = next(zip(*cur.description))
    logger.debug(f"{column_names=}")
    cur.close()
    conn.close()
    return data.copy(), column_names

def send_data(row, table_name, column_names):
    """Sends data to the remote API."""
    payload = {f"{col_name}": value for col_name, value in zip(column_names, row)}
    payload['table'] = table_name  # This helps the PHP script to handle different tables appropriately
    payload['secret_key'] = secret_key  # Add the secret key to the payload for security
    logger.debug(f"Data will be send with payload: {payload}")
    response = requests.post(api_url, data=payload)
    logger.debug(f"HTTP Response Code: {response.status_code}  Data sent to {api_url}: {response.text}")

    return response.status_code

def reset_tables():
    """Sends a command to the remote API to reset the tables."""
    response = requests.post(api_url, data={"reset": "true", "secret_key": secret_key})
    logger.info(f"Tables reset command sent: {response.text}")
    return response.status_code

def main():
    if args.reset:
        r=reset_tables()
        logger.debug(f"  HTTP Return code: {r}")
        if r == 200:
            logger.info("Reset sync bit on all invoices.")
            query = f"UPDATE `Invoices` SET `synced`=0 "
            logger.debug(query)
            conn = mariadb.connect(**config)
            cur = conn.cursor()
            cur.execute(query)
            conn.commit()
            cur.close()
            conn.close()
            logger.info("Reset sync bit on all invoices: done.")

    logger.debug("Connected to DB okay.")

    invoices_query = "SELECT * FROM Invoices WHERE synced=0; "
    invoice_data, column_names = fetch_data(invoices_query)
    invoice_data = invoice_data[:10] #limit to 10 due to limits of the HTTP Server and DB provider
    logger.debug(f"{invoice_data=}")

    for row in invoice_data:
        logger.debug(f"Submit now invoice id {row[0]}")
        r = send_data(row, "Invoices", column_names)
        logger.debug(f" --> Invoice successfully synced with HTTP status code {r}. Now update DB with sync bit.")
        if r == 200: #submitted okay
            logger.info(f"successfully synced InvoiceID {row[0]}")
            query = f"UPDATE `Invoices` SET `synced`=1 WHERE `InvoiceID`={row[0]}; "
            logger.debug(query)
            conn = mariadb.connect(**config)
            cur = conn.cursor()
            cur.execute(query)
            conn.commit()
            cur.close()
            conn.close()


            logger.debug("Submitting products now, too.")
            invoice_products_query = f"SELECT * FROM InvoiceProducts WHERE InvoiceID={row[0]}"
            logger.debug(invoice_products_query)
            invoice_products_data, column_names2 = fetch_data(invoice_products_query)
            logger.debug(f"invoice_products_data (len: {len(invoice_products_data)}): {invoice_products_data}")
            for row2 in invoice_products_data:
                send_data(row2, "InvoiceProducts", column_names2)
            logger.debug("     Done with submitting products")


if __name__ == "__main__":
    main()
