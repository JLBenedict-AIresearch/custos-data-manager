# tests.fakes.dummies

from datetime import datetime, timezone

from src.files.domain import File, FileStatus
from src.infrastructure.utils import calculate_email_row_hash
from src.leads.domain import Lead, AlertTeam
from src.leads.schemas import LeadData, LeadRowSchema
from src.leads.status_enum import LeadStatus
from src.quarantine.domain import QuarantinedRow
from src.sales.domain import FactSale, ProductDetails, CustomerDetails
from src.sales.schemas import SalesData, SalesRowSchema


from tests.fakes.fake_lead_dto import FakeLeadData
from tests.fakes.fake_sale_dto import FakeSalesData


def get_dummy_sales_file() -> File: 
    sales_file = File(
        filename="sales.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=[],
        status=FileStatus.PENDING,
        created_at=datetime(2026, 6, 9, 15, 55, tzinfo=timezone.utc),
        processing_begun=None
    )
    return sales_file

def get_dummy_leads_file() -> File: 
    leads_file =  File(
        filename="leads.csv", 
        hashed_file="8888899999", 
        assumed_type="leads", 
        is_ambiguous=False,
        potential_types=[],
        status=FileStatus.PENDING,
        created_at=datetime(2026, 6, 9, 15, 32, tzinfo=timezone.utc),
        processing_begun=None
   )
    return leads_file

def get_dummy_ambiguous_file() -> File: 
    questionable_file = File(
        filename="sales.csv", 
        hashed_file="789", 
        assumed_type="sales", 
        is_ambiguous=True,
        potential_types=["sales", "leads"],
        status=FileStatus.PENDING,
        created_at=datetime(2026, 6, 9, 15, 17, tzinfo=timezone.utc),
        processing_begun=None
    )
    return questionable_file

def get_dummy_interrupted_file() -> File: 
    interrupted_file = File(
        filename="leads.csv", 
        hashed_file="567", 
        assumed_type="leads", 
        is_ambiguous=False,
        potential_types=[],
        status=FileStatus.PROCESSING,
        created_at=datetime(2026, 6, 9, 15, 55, tzinfo=timezone.utc),
        processing_begun=datetime(2026, 8, 1, 3, 14, tzinfo=timezone.utc)
    )
    return interrupted_file


def get_sales_dicts() -> list[dict]:

    sales_row_dicts = [{'SKU_Code': 'UGLY_TCHOTCHKE', 'Product_Name': 'Ugly Tchotchke', 'Category': 'Decor', 'Customer_ID': 'CUST-598741', 'Region': 'Northwest', 'Industry': 'Home Goods', 'Quantity': 56, 'Revenue': 670.12, 'Transaction_Date': '2023-10-24', 'Transaction_ID': 'TXN-001 ', 'csv_line_number': 2}, {'SKU_Code': 'SQUISH_SOFA_BEIGE', 'Product_Name': 'Squishy Sofa (Beige)', 'Category': 'Furniture', 'Customer_ID': 'CUST-639500', 'Region': 'Southeast', 'Industry': 'Office', 'Quantity': 4, 'Revenue': 998.0, 'Transaction_Date': '2025-03-29', 'Transaction_ID': 'TXN-002', 'csv_line_number': 3}, {'SKU_Code': 'ERSATZ_ENDTABLE', 'Product_Name': 'Ersatz End Table', 'Category': 'Furniture', 'Customer_ID': 'CUST-913527', 'Region': 'Northeast', 'Industry': 'Hospitality', 'Quantity': 0, 'Revenue': 1320.0, 'Transaction_Date': '2024-02-06', 'Transaction_ID': 'TXN-003', 'csv_line_number': 4}, {'SKU_Code': 'sad_clown_ptg', 'Product_Name': 'Sad Clown Painting', 'Category': 'Decor', 'Customer_ID': 'CUST-546358', 'Region': 'Southwest', 'Industry': 'Public Sector', 'Quantity': 5, 'Revenue': 250.0, 'Transaction_Date': '2024-07-31', 'Transaction_ID': 'TXN-004', 'csv_line_number': 5}, {'SKU_Code': 'COL_RUG', 'Product_Name': 'Colorful Rug', 'Category': 'Decor', 'Customer_ID': '-726097', 'Region': 'MidAtlantic', 'Industry': 'Hospitality', 'Quantity': 72, 'Revenue': 7272.0, 'Transaction_Date': '2023-07-22', 'Transaction_ID': 'TXN-005', 'csv_line_number': 6}]

            
        # indices 0 and 1 are fine; 
        # index 2 should be quarantined (has a zero quantity)
        # index 3 has a SKU format that needs fixing
        # index 4 should be quarantined (missing customer ID in proper form)

    return sales_row_dicts


def get_leads_dicts() -> list[dict]:
    leads_row_dicts = [{'First_Name': 'John', 'Last_Name': 'Barker', 'Email_Address': 'jbark@example.com', 'Phone_Number': '800-555-6498', 'Company_Name': 'Super 9 Motels', 'Industry_Sector': 'Hospitality', 'Job_Title': 'Buyer', 'Lead_Status': 'MQL', 'Lead_Score': 63, 'Created_At': '2023-10-24T14:30:00Z', 'Modified_At': '2023-10-24T14:30:00Z', 'csv_line_number': 2, 'incoming_timestamp': '2023-10-24T14:30:00Z'}, {'First_Name': 'Lisa', 'Last_Name': 'Rodriguez', 'Email_Address': 'lisa_rodriguez@decor4u.com', 'Phone_Number': '800-555-9243', 'Company_Name': 'Decor For You', 'Industry_Sector': 'Home Goods', 'Job_Title': 'Buyer', 'Lead_Status': 'QUALIFIED', 'Lead_Score': 74, 'Created_At': '2025-01-17T09:58:00Z', 'Modified_At': '2025-11-14T11:32:00Z', 'csv_line_number': 3, 'incoming_timestamp': '2025-11-14T11:32:00Z'}, {'First_Name': 'Sandra', 'Last_Name': 'Washington', 'Email_Address': 's.washington@example.gov.us', 'Phone_Number': '(800) 555-6601', 'Company_Name': 'HUD', 'Industry_Sector': 'Public Sector', 'Job_Title': None, 'Lead_Status': 'NEW', 'Lead_Score': 22, 'Created_At': '2024-03-03T17:22:00Z', 'Modified_At': '2024-08-13T06:31:00Z', 'csv_line_number': 4, 'incoming_timestamp': '2024-08-13T06:31:00Z'}, {'First_Name': 'Lisa', 'Last_Name': 'Rodriguez', 'Email_Address': 'lisa_rodriguez@decor4u.com', 'Phone_Number': '00-555-9243', 'Company_Name': 'Decor For You', 'Industry_Sector': 'Home Goods', 'Job_Title': 'Buyer', 'Lead_Status': 'NEW', 'Lead_Score': 38, 'Created_At': '2025-12-24T13:06:00Z', 'Modified_At': '2025-12-24T13:06:00Z', 'csv_line_number': 5, 'incoming_timestamp': '2025-12-24T13:06:00Z'}, {'First_Name': 'Omar', 'Last_Name': 'Halb', 'Email_Address': 'omar.s.halb@toney.furniture.com', 'Phone_Number': '800-555-4059', 'Company_Name': 'Toney Furnishings Ltd.', 'Industry_Sector': 'Furniture', 'Job_Title': 'Chief Purchasing Officer', 'Lead_Status': 'REJECTED', 'Lead_Score': 14, 'Created_At': '2025-05-05T11:22:00Z', 'Modified_At': '2025-06-09T15:55:00Z', 'csv_line_number': 6, 'incoming_timestamp': '2025-06-09T15:55:00Z'}]

    # indices 0 and 1 should be fine
    # index 2 has a phone number that needs fixing; 
    # index 3 should be quarantined (missing phone number digits)
    
    return leads_row_dicts

def get_dummy_lead_quar(file_id) -> QuarantinedRow:
    lead_quar = QuarantinedRow(

    file_id=file_id,
    assumed_type="leads",
    raw_payload={'First_Name': 'Lisa', 'Last_Name': 'Rodriguez', 'Email_Address': "lisa", 'Phone_Number': '00-555-9243', 'Company_Name': 'Decor For You', 'Industry_Sector': 'Home Goods', 'Job_Title': 'Buyer', 'Lead_Status': 'NEW', 'Lead_Score': 38, 'Created_At': '2025-12-24T13:06:00Z', 'Modified_At': '2025-12-24T13:06:00Z', 'csv_line_number': 5, 'incoming_timestamp': '2025-12-24T13:06:00Z'}, 
    payload_hash="1234509876",
    error_reason="Email invalid",
    line_number=2,
    quarantined_at=datetime(2026, 8, 1, 3, 29, tzinfo=timezone.utc)
    )

    return lead_quar

def get_dummy_lead(file_id) -> Lead: 
    dummy_lead = Lead(
        source_file_id=file_id, 
        first_name="Lisa", 
        last_name="Rodriguez", 
        email="lisa_rodriguez@decor4u.com",
        email_hash=calculate_email_row_hash("lisa_rodriguez@decor4u.com"), 
        phone="8005559243", 
        status=LeadStatus.QUALIFIED,
        score=74,
        incoming_timestamp=datetime(2025, 11, 14, 11, 32, tzinfo=timezone.utc),
        company="Decor For You", 
        sector="Home Goods",
        position="Buyer",
        custos_timestamp=datetime(2026, 9, 2, 5, 5, tzinfo=timezone.utc)
    )
    
    return dummy_lead

def get_dummy_lead_udate(file_id) -> Lead:
    dummy_lead_update = Lead(
        source_file_id=file_id, 
        first_name="Lisa", 
        last_name="Rodriguez", 
        email="lisa_rodriguez@decor4u.com", 
        email_hash=calculate_email_row_hash("lisa_rodriguez@decor4u.com"),
        phone="8005559243", 
        status=LeadStatus.NEW,
        score=38,
        incoming_timestamp=datetime(2025, 12, 24, 13, 6, tzinfo=timezone.utc),
        company="Decor For You", 
        sector="Home Goods",
        position="Buyer",
        custos_timestamp=datetime(2026, 9, 2, 5, 5, tzinfo=timezone.utc)
    )

    return dummy_lead_update

def get_dummy_lead_dtos(case: str) -> list:
    
    
    results = []
    
    lead_dtos =     [
    LeadData(first_name='John', last_name='Barker', email='jbark@example.com', phone='8005556498', status=LeadStatus.MQL, score=63, incoming_timestamp=datetime(2023, 10, 24, 14, 30, tzinfo=timezone.utc), company='Super 9 Motels', sector='Hospitality', position='Buyer'),  
    LeadData(first_name='Lisa', last_name='Rodriguez', email='lisa_rodriguez@decor4u.com', phone='8005559243', status=LeadStatus.QUALIFIED, score=74, incoming_timestamp=datetime(2025, 11, 14, 11, 32, tzinfo=timezone.utc), company='Decor For You', sector='Home Goods', position='Buyer'), 
    LeadData(first_name='Sandra', last_name='Washington', email='s.washington@example.gov.us', phone='8005556601', status=LeadStatus.NEW, score=22, incoming_timestamp=datetime(2024, 8, 13, 6, 31, tzinfo=timezone.utc), company='HUD', sector='Public Sector', position=None), 
    LeadData(first_name='Lisa', last_name='Rodriguez', email='lisa_rodriguez@decor4u.com', phone='8005559243', status=LeadStatus.NEW, score=38, incoming_timestamp=datetime(2025, 12, 24, 13, 6, tzinfo=timezone.utc), company='Decor For You', sector='Home Goods', position='Buyer'), 
    LeadData(first_name='Omar', last_name='Halb', email='omar.s.halb@toney.furniture.com', phone='8005554059', status=LeadStatus.REJECTED, score=14, incoming_timestamp=datetime(2025, 6, 9, 15, 55, tzinfo=timezone.utc), company='Toney Furnishings Ltd.', sector='Furniture', position='Chief Purchasing Officer'),
    FakeLeadData(first_name='Lisa', last_name='Rodriguez', phone='8005559243', status=LeadStatus.NEW, score=38, incoming_timestamp=datetime(2025, 12, 24, 13, 6, tzinfo=timezone.utc), company='Decor For You', sector='Home Goods', position='Buyer')
    ]

    if case == "good": 
        results.append(lead_dtos[0])
        results.append(lead_dtos[1]) 

    if case == "update": 
        results.append(lead_dtos[1])
        results.append(lead_dtos[3])

    if case == "broken": 
        results.append(lead_dtos[5])

    return results

def get_dummy_sales_dtos(case: str) -> list:
    
    results = []

    sales_dtos = [
        SalesData(sku='UGLY_TCHOTCHKE', product_name='Ugly Tchotchke', category='Decor', customer_identifier='CUST-598741', region='Northwest', industry='Home Goods', quantity_sold=56, revenue_amount=670.12, sale_timestamp=datetime(2023, 12, 25, 0, 0), transaction_id='TXN-001'), 
        SalesData(sku='SQUISH_SOFA_BEIGE', product_name='Squishy Sofa (Beige)', category='Furniture', customer_identifier='CUST-639500', region='Southeast', industry='Office', quantity_sold=4, revenue_amount=998.0, sale_timestamp=datetime(2025, 3, 29, 0, 0), transaction_id='TXN-002'), 
        SalesData(sku='ERSATZ_ENDTABLE', product_name='Ersatz End Table', category='Furniture', customer_identifier='CUST-913527', region='Northeast', industry='Hospitality', quantity_sold=40, revenue_amount=1320.0, sale_timestamp=datetime(2024, 2, 6, 0, 0), transaction_id='TXN-003'), 
        SalesData(sku='SAD_CLOWN_PTG', product_name='Sad Clown Painting', category='Decor', customer_identifier='CUST-546358', region='Southwest', industry='Public Sector', quantity_sold=5, revenue_amount=250.0, sale_timestamp=datetime(2024, 7, 31, 0, 0), transaction_id='TXN-004'), 
        SalesData(sku='ERSATZ_ENDTABLE', product_name='Ersatz End Table', category='Furniture', customer_identifier='CUST-913527', region='Northeast', industry='Hospitality', quantity_sold=40, revenue_amount=1320.0, sale_timestamp=datetime(2024, 2, 6, 0, 0), transaction_id='TXN-003'),
        FakeSalesData(sku=None, product_name='Ugly Tchotchke', category='Decor', customer_identifier='CUST-598741', region='Northwest', industry='Home Goods', quantity_sold=56, revenue_amount=670.12, sale_timestamp=datetime(2023, 10, 24, 0, 0), transaction_id='TXN-001 ')
        ]

    if case == "good": 
        results.append(sales_dtos[0])
        results.append(sales_dtos[1])
    
    if case == "missing":
        results.append(sales_dtos[5])
        
    if case == "duplicate": 
        results.append(sales_dtos[2])
        results.append(sales_dtos[4])
        
    return results    

def get_quarantined_row_for_pydantic(case) -> list: 
    
    result = []
    
    lead_row =  {'First_Name': 'Omar', 'Last_Name': 'Halb', 'Email_Address': 'omar.s.halb', 'Phone_Number': '800-555-4059', 'Company_Name': 'Toney Furnishings Ltd.', 'Industry_Sector': 'Furniture', 'Job_Title': 'Chief Purchasing Officer', 'Lead_Status': 'REJECTED', 'Lead_Score': 14, 'Created_At': '2025-05-05T11:22:00Z', 'Modified_At': '2025-06-09T15:55:00Z', 'csv_line_number': 6, 'incoming_timestamp': '2025-06-09T15:55:00Z'}
    sales_row = {'SKU_Code': 'COL_RUG', 'Product_Name': 'Colorful Rug', 'Category': 'Decor', 'Customer_ID': '-726097', 'Region': 'MidAtlantic', 'Industry': 'Hospitality', 'Quantity': 72, 'Revenue': 7272.0, 'Transaction_Date': '2023-07-22', 'Transaction_ID': 'TXN-005', 'csv_line_number': 6}
    
    if case == "lead":
        result.append(lead_row)
    
    if case == "sales":
        result.append(sales_row)
        
    return result

def get_quarantined_row_for_pandas(case) -> list: 
    
    result = []
    
    lead_row_csv = ("First_Name,Last_Name,Email_Address,Phone_Number,Company_Name,Industry_Sector,Job_Title,Lead_Status,Lead_Score,Created_At,Modified_At\n"
    "John,Barker,jbark@example.com,800-555-6498,Super 9 Motels,Hospitality,Buyer,MQL,63,,\n"
    "Lisa,Rodriguez,lisa_rodriguez@decor4u.com,800-555-9243,Decor For You,Home Goods,Buyer,QUALIFIED,74,2025-01-17T09:58:00Z,2025-11-14T11:32:00Z\n"
    "Sandra,Washington,s.washington@example.gov.us,800-555-6601,HUD,Public Sector,,NEW,22,2024-03-03T17:22:00Z,2024-08-13T06:31:00Z\n"
    "Lisa,Rodriguez,lisa_rodriguqez@decor4u.com,800-555-9243,Decor For You,Home Goods,Buyer,NEW,38,2025-12-24T13:06:00Z,\n"
    "Omar,Halb,omar.s.halb@toney.furniture.com,800-555-4059,Toney Furnishings Ltd.,Furniture,Chief Purchasing Officer,REJECTED,14,2025-05-05T11:22:00Z,2025-06-09T15:55:00Z")
    sales_row_csv = """SKU_Code,Product_Name,Category,Customer_ID,Region,Industry,Quantity,Revenue,Transaction_Date,Transaction_ID
    UGLY_TCHOTCHKE,Ugly Tchotchke,Decor,-598741,Northwest,Home Goods,56,670.12,2023-10-24,TXN-001"""
    
    if case == "lead":
        result.append(lead_row_csv)
    if case == "sales": 
        result.append(sales_row_csv)
    
    return result

def get_three_lead_files() -> list[File]:

    leads_file1 =  File(
        filename="leads1.csv", 
        hashed_file="444880", 
        assumed_type="leads", 
        is_ambiguous=False,
        potential_types=[],
        status=FileStatus.VALIDATING,
        created_at=datetime(2026, 6, 9, 15, 32, tzinfo=timezone.utc),
        processing_begun=None
   )

    leads_file2 =  File(
        filename="leads2.csv", 
        hashed_file="13579", 
        assumed_type="leads", 
        is_ambiguous=False,
        potential_types=[],
        status=FileStatus.VALIDATING,
        created_at=datetime(2026, 6, 9, 15, 32, tzinfo=timezone.utc),
        processing_begun=None
   )

    leads_file3 =  File(
        filename="leads3.csv", 
        hashed_file="746902", 
        assumed_type="leads", 
        is_ambiguous=False,
        potential_types=[],
        status=FileStatus.VALIDATING,
        created_at=datetime(2026, 6, 9, 15, 32, tzinfo=timezone.utc),
        processing_begun=None
   )
    
    return [leads_file1, leads_file2, leads_file3]

def get_base_and_updates() -> list[LeadData]:
    
    base_lead = LeadData(
        first_name="Hannibal",
        last_name="Lecter",
        email="hannibalcannibal@chomp.com",
        phone="800-555-4039",
        status=LeadStatus.NEW,
        score=26,
        incoming_timestamp=datetime(2025, 11, 14, 11, 32, tzinfo=timezone.utc),
        company="Lector Therapy",
        sector="Psychology/Fine Dining",
        position="Therapist"            
        )

    incoming1 = LeadData(
        first_name="Hannibal",
        last_name="Lecter",
        email="hannibalcannibal@chomp.com",
        phone="800-555-4039",
        status=LeadStatus.CONTACTED,
        score=67,
        incoming_timestamp=datetime(2025, 11, 18, 17, 4, tzinfo=timezone.utc),
        company="Carthage Therapy",
        sector="Psychology/Fine Dining",
        position="Therapist"
        )
    
    incoming2 = LeadData(
        first_name="Hannibal",
        last_name="Lecter",
        email="hannibalcannibal@chomp.com",
        phone="800-555-4039",
        status=LeadStatus.REJECTED,
        score=2,
        incoming_timestamp=datetime(2025, 11, 18, 21, 45, tzinfo=timezone.utc),
        company="Federal Prison",
        sector="Solitary",
        position="High-Risk Prisoner"
        )
    
    return [base_lead, incoming1, incoming2]

def get_fake_alert_team(): 
    raw_team_data = [
    {
        "first_name": "Diego",
        "last_name": "Garcia",
        "email": "diego.garcia@custos-sales.local",
        "sectors": ["Home Goods", "Furniture", "Decor"]
    },
    {
        "first_name": "Lucia",
        "last_name": "Vanitelli",
        "email": "l.vanitelli@custos-sales.local",
        "sectors": ["Public Sector", "Education"]
    },
    {
        "first_name": "Amelia",
        "last_name": "Gehrhardt",
        "email": "amelia.gehrhardt@custos-sales.local",
        "sectors": ["Hospitality", "Food Service"]
    },
    {
        "first_name": "Tony",
        "last_name": "Nguyen",
        "email": "t.nguyen@custos-sales.local",
        "sectors": ["Retail", "Technology", "Other"]
    }
]

    team_members = []
    
    for data in raw_team_data:
        normalized_email = data["email"].strip().lower()
        
        member = AlertTeam(
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            email_hash=calculate_email_row_hash(normalized_email), 
            sectors=data["sectors"]
        )
        team_members.append(member)
    return team_members

def get_mql_lead_data():
    leads= [Lead(source_file_id=1, first_name='John', last_name='Barker', email='jbark@example.com', email_hash=calculate_email_row_hash('jbark@example.com'), phone='8005556498', status=LeadStatus.MQL, score=63, incoming_timestamp=datetime(2023, 10, 24, 14, 30, tzinfo=timezone.utc), company='Super 9 Motels', sector='Hospitality', position='Buyer', custos_timestamp=datetime(2026, 9, 2, 5, 5, tzinfo=timezone.utc)),  
    Lead(source_file_id=1, first_name='Lisa', last_name='Rodriguez', email='lisa_rodriguez@decor4u.com', email_hash=calculate_email_row_hash('lisa_rodriguez@decor4u.com'), phone='8005559243', status=LeadStatus.MQL, score=74, incoming_timestamp=datetime(2025, 11, 14, 11, 32, tzinfo=timezone.utc), company='Decor For You', sector='Home Goods', position='Buyer', custos_timestamp=datetime(2026, 9, 2, 5, 5, tzinfo=timezone.utc)), 
    Lead(source_file_id=1, first_name='Sandra', last_name='Washington', email='s.washington@example.gov.us', email_hash=calculate_email_row_hash('s.washington@example.gov.us'), phone='8005556601', status=LeadStatus.NEW, score=52, incoming_timestamp=datetime(2024, 8, 13, 6, 31, tzinfo=timezone.utc), company='HUD', sector='Public Sector', position=None, custos_timestamp=datetime(2026, 9, 2, 5, 5, tzinfo=timezone.utc)), 
    Lead(source_file_id=1, first_name='Omar', last_name='Halb', email='omar.s.halb@toney.furniture.com', email_hash=calculate_email_row_hash('omar.s.halb@toney.furniture.com'), phone='8005554059', status=LeadStatus.NEW, score=64, incoming_timestamp=datetime(2025, 6, 9, 15, 55, tzinfo=timezone.utc), company='Toney Furnishings Ltd.', sector=None, position='Chief Purchasing Officer', custos_timestamp=datetime(2026, 9, 2, 5, 5, tzinfo=timezone.utc))]
    return leads

def lead_to_dto(lead: Lead) -> LeadData:
    dto = LeadData(
        first_name=lead.first_name,
        last_name=lead.last_name,
        email=lead.email,
        phone=lead.phone,
        status=lead.status,
        score=lead.score,
        company=lead.company,
        sector=lead.sector,
        position=lead.position,
        incoming_timestamp=lead.incoming_timestamp
    )
    return dto