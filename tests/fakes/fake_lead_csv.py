
from datetime import datetime, timedelta
from faker import Faker
import pandas as pd
import random

fake = Faker()

def generate_headers():
    headers = ["First_Name", "Last_Name", "Email_Address", "Phone_Number", "Lead_Status", "Lead_Score", "Company_Name", "Industry_Sector",   "Job_Title", "Created_At", "Modified_At"]
    return headers

def generate_missing_time_header(): 
    headers = ["First_Name", "Last_Name", "Email_Address", "Phone_Number", "Lead_Status", "Lead_Score", "Company_Name", "Industry_Sector",   "Job_Title", "Modified_At"]
    return headers

def generate_good_rows(n: int):
    rows = []
    for _ in range(n):
        created_at = fake.date_time_this_year()
        modified_at = created_at + timedelta(days=random.randint(1, 120))
        rows.append({
            "First_Name": fake.first_name(),
            "Last_Name": fake.last_name(),
            "Email_Address": fake.unique.email(),
            "Phone_Number": fake.phone_number(),
            "Lead_Status": random.choice (["NEW", "MQL", "QUALIFIED", "CONTACTED", "REJECTED"]),
            "Lead_Score": random.randint(0, 100),
            "Company_Name": fake.company(),
            "Industry_Sector": random.choice(["Public Sector", "Furniture", "Hospitality", "Home Goods", "Technology", "Education", "Food Service", None]),
            "Job_Title": fake.job(),
            "Created_At": created_at,
            "Modified_At": modified_at
        })
    return rows

def inject_missing_required_field(rows, n: int, field="First_Name"):
    """Corrupts n random rows by blanking a required field - should get quarantined."""
    clean_rows = [r for r in rows if not r.get("_is_dirty")]
    n = min(n, len(clean_rows))
    for row in random.sample(clean_rows, n):
        row[field] = None
        row["_is_dirty"] = True
    return rows

def inject_bad_phone_number(rows, n: int, field="Phone_Number"):
    """Messes up the phone number so that it fails Pydantic validation"""
    clean_rows = [r for r in rows if not r.get("_is_dirty")]
    n = min(n, len(clean_rows))
    for row in random.sample(clean_rows, n):
        row["Phone_Number"] = str(random.randint(100, 99999))  # 3-5 digits, should flag
        row["_is_dirty"] = True
    return rows

def generate_failing_lead_rows(n: int):    
    rows = []
    for _ in range(n):
        created_at = fake.date_time_this_year()
        modified_at = created_at + timedelta(days=random.randint(1, 120))
        rows.append({
            "First_Name": fake.first_name(),
            "Last_Name": fake.last_name(),
            "Email_Address": fake.unique.email(),
            "Phone_Number": fake.phone_number(),
            "Lead_Status": random.choice (["NEW", "MQL", "QUALIFIED", "CONTACTED", "REJECTED"]),
            "Lead_Score": random.randint(0, 100),
            "Company_Name": fake.company(),
            "Industry_Sector": random.choice(["Public Sector", "Furniture", "Hospitality", "Home Goods", "Technology", "Education", "Food Service", None]),
            "Job_Title": fake.job(),
            "Created_At": created_at,
            "Modified_At": modified_at
        })
    clean_rows = [r for r in rows if not r.get("_is_dirty")]
    for row in clean_rows:
        row["Phone_Number"] = str(random.randint(100, 99999))  # 3-5 digits, should flag
        row["_is_dirty"] = True

    return rows
    

def inject_duplicate_emails(rows, n: int):
    """Forces n rows to share an email with an earlier row - tests apply_update/rollback paths."""
    for _ in range(n):
        source = random.choice(rows)
        dupe = source.copy()
        dupe["Lead_Score"] = random.randint(0, 100) 
        rows.append(dupe)
    return rows

def strip_created_column(rows, keep="Modified_At"):
    """Simulates a file with only ONE timestamp field"""
    for row in rows:
        if keep == "Modified_At":
            row["Modified_At"] = row.pop("Created_At")
    return rows

def create_updates(
    rows,
    n: int = 3,  
    input_records: list[dict] | None = None
    ):
    """
    Takes n existing rows and creates a follow-up row for the same email,
    with changed values in a given field. Returns the extended rows list, 
    a list of the updated email addresses, and the full records that were updated.
    """
    updates = []
    updated_emails = [] 
    originals = []
    records_to_modify = input_records if input_records else random.sample(rows, n)

    for original_record in records_to_modify: 
        originals.append(original_record.copy()) 
        updated_emails.append(original_record["Email_Address"])
        
        updated = original_record.copy()
        
        base_time = updated.get("Modified_At", updated.get("Created_At"))
        if base_time:
            updated["Modified_At"] = base_time + timedelta(days=random.randint(1, 120))
        new_job = fake.job()
        while new_job == updated["Job_Title"]:
            new_job = fake.job()
        updated["Job_Title"] = new_job
        new_score = random.randint(0, 100)
        while new_score == updated["Lead_Score"]:
            new_score = random.randint(0, 100)
        updated["Lead_Score"] = new_score

            
        updates.append(updated)
        
    rows.extend(updates)
    
    return rows, updated_emails, originals
    