# tests.fakes.fake_sales_csv

import csv
from faker import Faker
import pandas as pd
import random
import uuid

fake = Faker()

def generate_product_name():
    adjectives = ["Ugly", "Comfortable", "Sad", "Elegant", "Heavy-Duty", "Premium", "Compact"]
    nouns = ["Lamp", "Table", "Sofa", "Lamp", "Rug", "Chair", "Desk", "Bed"]
    return f"{random.choice(adjectives)} {random.choice(nouns)}"

def generate_sku(product_name: str):
    parts = product_name.split()
    part_1 = parts[0].upper()
    part_2 = parts[1].upper()
    return f"{part_1}_{part_2}"

def generate_headers():
    headers = ["SKU_Code", "Product_Name", "Category", "Customer_ID", "Region", "Industry", "Quantity", "Revenue",           "Transaction_Date", "Transaction_ID"]
    return headers

def generate_missing_headers(): 
    headers = ["SKU_Code", "Product_Name", "Category", "Customer_ID", "Industry", "Quantity", "Revenue", "Transaction_Date", "Transaction_ID"]

def generate_good_rows(n: int):
    rows = []
    for _ in range(n):
        product_name = generate_product_name()
        rows.append({
            "SKU_Code": generate_sku(product_name),
            "Product_Name": product_name,
            "Category": random.choice(["Furniture", "Decor", "Rugs", "Other"]),
            "Customer_ID": f"CUST-{fake.unique.random_number(digits=6)}",
            "Region": random.choice(["Northwest", "Northeast", "Midwest", "MidAtlantic", "Southeast", "Southwest"]),
            "Industry": random.choice(["Public Sector", "Education", "Hospitality", "Home Goods", "Food Services", "Furniture"]),
            "Quantity": random.randint(1,1000),
            "Revenue": round(random.uniform(10, 5000), 2),
            "Transaction_Date": fake.date_time_this_year(),
            "Transaction_ID": fake.unique.uuid4()
        })
    return rows

def missing_headers_rows(n: int):
    rows = []
    for _ in range(n):
        product_name = generate_product_name()
        rows.append({
            "SKU_Code": generate_sku(product_name),
            "Product_Name": product_name,
            "Category": random.choice(["Furniture", "Decor", "Rugs", "Other"]),
            "Customer_ID": f"CUST-{fake.unique.random_number(digits=6)}",
            "Industry": random.choice(["Public Sector", "Education", "Hospitality", "Home Goods", "Food Services", "Furniture"]),
            "Quantity": random.randint(1,1000),
            "Revenue": round(random.uniform(10, 5000), 2),
            "Transaction_Date": fake.date_time_this_year(),
            "Transaction_ID": fake.unique.uuid4()
        })
    return rows

def inject_bad_customer_identifiers(rows, n: int):
    """Corrupts n rows so customer_identifier lacks the required 'CUST-' prefix."""
    clean_rows = [r for r in rows if not r.get("_is_dirty")]
    n = min(n, len(clean_rows))
    
    for row in random.sample(clean_rows, n):
        row["Customer_ID"] = str(fake.unique.random_number(digits=6))
        row["_is_dirty"] = True  # Tag it so other functions leave it alone
        
    return rows


def inject_bad_quantity(rows, n: int):
    """Corrupts quantity row -- makes it 0 or negative"""
    clean_rows = [r for r in rows if not r.get("_is_dirty")]
    n = min(n, len(clean_rows))
    
    for row in random.sample(clean_rows, n):
        row["Quantity"] = random.randint(-10, 0)
        row["_is_dirty"] = True 
        
    return rows

def inject_bad_revenue(rows, n: int):
    """Corrupts revenue rows -- makes them 0 or negative (float, matching real schema)"""
    clean_rows = [r for r in rows if not r.get("_is_dirty")]
    n = min(n, len(clean_rows))
    
    for row in random.sample(rows, n):
        row["Revenue"] = round(random.uniform(-1000, 0), 2)
        row["_is_dirty"] = True
    return rows

def inject_exact_duplicates(rows, n: int = 3):
    """Appends n exact copies of existing rows - tests idempotency within a single file."""
    dupes = [row.copy() for row in random.sample(rows, n) if not row.get("_is_dirty")]
    rows.extend(dupes)
    return rows

def inject_missing_required_values(rows, n: int):
    """Makes a required field None; row will fail validation and be quarantined"""
    clean_rows = [r for r in rows if not r.get("_is_dirty")]
    n = min(n, len(clean_rows))
    
    for row in random.sample(clean_rows, n):
        case = random.randint(1, 2)
        if case == 1:
            row["Transaction_ID"] = None
        elif case == 2:
            row["SKU_Code"] = None
            
        row["_is_dirty"] = True
        
    return rows


    
