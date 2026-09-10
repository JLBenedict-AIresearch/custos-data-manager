
import pandas as pd
import os
import tempfile


def csv_to_row_dicts(csv_filepath: str, timestamp: bool):
    
    df = pd.read_csv(csv_filepath)
    df.columns = df.columns.astype(str)    
    df["csv_line_number"] = df.index + 2
    data_columns = [col for col in df.columns if col != "csv_line_number"]
    
    requires_timestamp = timestamp
    
    if requires_timestamp:
    
        created_at = {"created_at", "Created_at", "Created_At", "CreatedAt"}
        updated_at = {"modified_at", "Modified_At", "Modified_at", "ModifiedAt", "updated_at", "Updated_at", "Updated_At", "UpdatedAt"}
    
        created_fields = [col for col in df.columns if col in created_at]
        updated_fields = [col for col in df.columns if col in updated_at]
    

        if created_fields:
            created_str = str(created_fields[0])
            df["Created_At"] = pd.to_datetime(df[created_str], errors="coerce")  
        else: 
            updated_str = str(updated_fields[0])
            df["Created_At"].fillna(df[updated_str])
        if updated_fields: 
            updated_str = str(updated_fields[0])
            df["Modified_At"] = pd.to_datetime(df[updated_str], errors="coerce")
        else: 
            df["Modified_At"].fillna(df["Created_At"])
            
        df["incoming_timestamp"] = df["Modified_At"].fillna(df["Created_At"])

        datetime_columns = df.select_dtypes(include=['datetime64', 'datetimetz']).columns
        for col in datetime_columns:
            df[col] = df[col].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                
            clean_valid_df = df.astype(object).where(pd.notnull(df), None)


    valid_records = df.to_dict(orient="records")
    return valid_records
    

if __name__ == "__main__":
    
    sales_input_csv  = """SKU_Code,Product_Name,Category,Customer_ID,Region,Industry,Quantity,Revenue,Transaction_Date,Transaction_ID
    UGLY_TCHOTCHKE,Ugly Tchotchke,Decor,CUST-598741,Northwest,Home Goods,56,670.12,2023-10-24,TXN-001 
    SQUISHY_SOFA_BEIGE,Squishy Sofa (Beige),Furniture,CUST-639500,Southeast,Office,4,998.00,2025-03-29,TXN-002
    ERSATZ_ENDTABLE,Ersatz End Table,Furniture,CUST-913527,Northeast,Hospitality,40,1320,2024-02-06,TXN-003
    SAD_CLOWN_PTG,Sad Clown Painting,Decor,CUST-546358,Southwest,Public Sector,5,250,2024-07-31,TXN-004
    COL_RUG,Colorful Rug,Decor,CUST-726097,MidAtlantic,Hospitality,72,7272,2023-07-22,TXN-005"""
    
    leads_input_csv = """First_Name,Last_Name,Email_Address,Phone_Number,Company_Name,Industry_Sector,Job_Title,Lead_Status,Lead_Score,Created_At,Modified_At
    John,Barker,jbark@example.com,800-555-6498,Super 9 Motels,Hospitality,Buyer,MQL,63,,2023-10-24T14:30:00Z
    Lisa,Rodriguez,lisa_rodriguez@decor4u.com,800-555-9243,Decor For You,Home Goods,Buyer,QUALIFIED,74,2025-01-17T09:58:00Z,2025-11-14T11:32:00Z
    Sandra,Washington,s.washington@example.gov.us,800-555-6601,HUD,Public Sector,,NEW,22,2024-03-03T17:22:00Z,2024-08-13T06:31:00Z
    Lisa,Rodriguez,lisa_rodriguqez@decor4u.com,800-555-9243,Decor For You,Home Goods,Buyer,NEW,38,2025-12-24T13:06:00Z,
    Omar,Halb,omar.s.halb@toney.furniture.com,800-555-4059,Toney Furnishings Ltd.,Furniture,Chief Purchasing Officer,REJECTED,14,2025-05-05T11:22:00Z,2025-06-09T15:55:00Z"""
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", prefix="leads_", delete=False) as leads_tmp:
        leads_tmp.write(leads_input_csv)
        leads_filepath = leads_tmp.name  # e.g., /tmp/leads_a8b9c.csv


    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", prefix="sales_", delete=False) as sales_tmp:
        sales_tmp.write(sales_input_csv)
        sales_filepath = sales_tmp.name
        
    try:
    
        leads_dict = csv_to_row_dicts(leads_filepath, True)
        sales_dict = csv_to_row_dicts(sales_filepath, False)
        
        print(leads_dict)
        print(sales_dict)
        
    finally:
        os.remove(leads_filepath)
        os.remove(sales_filepath)