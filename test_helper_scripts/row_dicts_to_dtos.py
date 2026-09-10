# run command: poetry run python -m test_helper_scripts.row_dicts_to_dtos


from typing import Sequence, Callable
from pydantic import BaseModel, ValidationError

from src.files.domain import FileStatus
from src.leads.schemas import LeadRowSchema, LeadData
from src.leads.status_enum import LeadStatus

from src.sales.schemas import SalesData, SalesRowSchema

my_leads = [{'First_Name': 'John', 'Last_Name': 'Barker', 'Email_Address': 'jbark@example.com', 'Phone_Number': '800-555-6498', 'Company_Name': 'Super 9 Motels', 'Industry_Sector': 'Hospitality', 'Job_Title': 'Buyer', 'Lead_Status': 'MQL', 'Lead_Score': 63, 'Created_At': '2023-10-24T14:30:00Z', 'Modified_At': '2023-10-24T14:30:00Z', 'csv_line_number': 2, 'incoming_timestamp': '2023-10-24T14:30:00Z'}, 
                {'First_Name': 'Lisa', 'Last_Name': 'Rodriguez', 'Email_Address': 'lisa_rodriguez@decor4u.com', 'Phone_Number': '800-555-9243', 'Company_Name': 'Decor For You', 'Industry_Sector': 'Home Goods', 'Job_Title': 'Buyer', 'Lead_Status': 'QUALIFIED', 'Lead_Score': 74, 'Created_At': '2025-01-17T09:58:00Z', 'Modified_At': '2025-11-14T11:32:00Z', 'csv_line_number': 3, 'incoming_timestamp': '2025-11-14T11:32:00Z'}, 
                {'First_Name': 'Sandra', 'Last_Name': 'Washington', 'Email_Address': 's.washington@example.gov.us', 'Phone_Number': '(800) 555-6601', 'Company_Name': 'HUD', 'Industry_Sector': 'Public Sector', 'Job_Title': None, 'Lead_Status': 'NEW', 'Lead_Score': 22, 'Created_At': '2024-03-03T17:22:00Z', 'Modified_At': '2024-08-13T06:31:00Z', 'csv_line_number': 4, 'incoming_timestamp': '2024-08-13T06:31:00Z'}, 
                {'First_Name': 'Lisa', 'Last_Name': 'Rodriguez', 'Email_Address': 'lisa_rodriguqez@decor4u.com', 'Phone_Number': '800-555-9243', 'Company_Name': 'Decor For You', 'Industry_Sector': 'Home Goods', 'Job_Title': 'Buyer', 'Lead_Status': 'NEW', 'Lead_Score': 38, 'Created_At': '2025-12-24T13:06:00Z', 'Modified_At': '2025-12-24T13:06:00Z', 'csv_line_number': 5, 'incoming_timestamp': '2025-12-24T13:06:00Z'}, 
                {'First_Name': 'Omar', 'Last_Name': 'Halb', 'Email_Address': 'omar.s.halb@toney.furniture.com', 'Phone_Number': '800-555-4059', 'Company_Name': 'Toney Furnishings Ltd.', 'Industry_Sector': 'Furniture', 'Job_Title': 'Chief Purchasing Officer', 'Lead_Status': 'REJECTED', 'Lead_Score': 14, 'Created_At': '2025-05-05T11:22:00Z', 'Modified_At': '2025-06-09T15:55:00Z', 'csv_line_number': 6, 'incoming_timestamp': '2025-06-09T15:55:00Z'}]

my_sales = [{'SKU_Code': 'UGLY_TCHOTCHKE', 'Product_Name': 'Ugly Tchotchke', 'Category': 'Decor', 'Customer_ID': 'CUST-598741', 'Region': 'Northwest', 'Industry': 'Home Goods', 'Quantity': 56, 'Revenue': 670.12, 'Transaction_Date': '2023-10-24', 'Transaction_ID': 'TXN-001 ', 'csv_line_number': 2}, 
                {'SKU_Code': 'SQUISH_SOFA_BEIGE', 'Product_Name': 'Squishy Sofa (Beige)', 'Category': 'Furniture', 'Customer_ID': 'CUST-639500', 'Region': 'Southeast', 'Industry': 'Office', 'Quantity': 4, 'Revenue': 998.0, 'Transaction_Date': '2025-03-29', 'Transaction_ID': 'TXN-002', 'csv_line_number': 3}, 
                {'SKU_Code': 'ERSATZ_ENDTABLE', 'Product_Name': 'Ersatz End Table', 'Category': 'Furniture', 'Customer_ID': 'CUST-913527', 'Region': 'Northeast', 'Industry': 'Hospitality', 'Quantity': 40, 'Revenue': 1320.0, 'Transaction_Date': '2024-02-06', 'Transaction_ID': 'TXN-003', 'csv_line_number': 4}, 
                {'SKU_Code': 'sad_clown_ptg', 'Product_Name': 'Sad Clown Painting', 'Category': 'Decor', 'Customer_ID': 'CUST-546358', 'Region': 'Southwest', 'Industry': 'Public Sector', 'Quantity': 5, 'Revenue': 250.0, 'Transaction_Date': '2024-07-31', 'Transaction_ID': 'TXN-004', 'csv_line_number': 5}, 
                {'SKU_Code': 'ERSATZ_ENDTABLE', 'Product_Name': 'Ersatz End Table', 'Category': 'Furniture', 'Customer_ID': 'CUST-913527', 'Region': 'Northeast', 'Industry': 'Hospitality', 'Quantity': 40, 'Revenue': 1320.0, 'Transaction_Date': '2024-02-06', 'Transaction_ID': 'TXN-003', 'csv_line_number': 6}]


def row_dicts_to_dtos(leads_dict, sales_dict):

    
    valid_leads_dtos = []
    valid_sales_dtos = []
    
    for row_dict in leads_dict:
        line_num = row_dict.pop("csv_line_number", 0) 
        clean_data = LeadRowSchema(**row_dict)
        dto = LeadData(**clean_data.model_dump())
        valid_leads_dtos.append(dto)
    
    for row_dict in sales_dict: 
        line_num = row_dict.pop("csv_line_number", 0)
        clean_data = SalesRowSchema(**row_dict)
        dto = SalesData(**clean_data.model_dump())
        valid_sales_dtos.append(dto)
        
    return valid_leads_dtos, valid_sales_dtos

if __name__ == "__main__":
        
    results = row_dicts_to_dtos(my_leads, my_sales)
    
    print(results[0])
    print(results[1])