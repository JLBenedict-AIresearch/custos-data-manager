# tests.unit.handlers.auditing

# run command: poetry run python -m pytest tests/unit/handlers/test_auditing_handlers.py

import pandas as pd

from src.pipeline.handlers.auditing import audit_csv, attempt_retry
from src.quarantine.domain import QuarantinedRow
from src.pipeline.events import PandasAuditFailed, SchemaDriftDetected
from src.pipeline.commands import ValidateDataCommand, AuditCSVCommand
from src.files.domain import File, FileStatus


from tests.fakes.fake_storage_manager import FakeFileStorageManager
from tests.fakes.fake_uow import FakeUnitOfWork


def test_audit_csv_reads_pandas(tmp_path, configured_registry):

    fake_csv = """SKU_Code,Product_Name,Category,Customer_ID,Region,Industry,Quantity,Revenue,Transaction_Date,Transaction_ID
    UGLY_TCHOTCHKE,Ugly Tchotchke,Decor,CUST-598741,Northwest,Home Goods,56,670.12,2023-10-24,TXN-001 
    SQUISHY_SOFA_BEIGE,Squishy Sofa (Beige),Furniture,CUST-639500,Southeast,Office,4,998.00,2025-03-29,TXN-002
    ERSATZ_ENDTABLE,Ersatz End Table,Furniture,CUST-913527,Northeast,Hospitality,40,1320,2024-02-06,TXN-003
    SAD_CLOWN_PTG,Sad Clown Painting,Decor,CUST-546358,Southwest,Public Sector,5,250,2024-07-31,TXN-004
    COL_RUG,Colorful Rug,Decor,CUST-726097,MidAtlantic,Hospitality,72,7272,2023-07-22,TXN-005"""

    fake_uow = FakeUnitOfWork()
    
    test_file = tmp_path / "creative_batch.csv"
    test_file.write_text(fake_csv)
    
    fake_storage = FakeFileStorageManager()
    fake_storage.known_files.add(test_file)
   
    with fake_uow as uow: 
        file = File(
        filename="creative_batch.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.AUDITING,

        )
        uow.files.add(file)
        uow.commit()

    command = AuditCSVCommand(
        file_id=1, 
        filepath=str(test_file), 
        filename=str("creative_batch.csv"),
        original_assumed_type="sales",
        assumed_type="sales",
        potential_types=["sales"],
        is_ambiguous=False,
        attempted_types=[]
)
    
    messages = audit_csv(command=command, uow_factory=lambda: fake_uow, registry=configured_registry )
    
    with fake_uow as uow: 
        file = uow.files.get(1)     
        quarantined = uow.quarantine.get(1)      
    
    assert isinstance(messages[0], ValidateDataCommand)
    assert file.quarantined_rows == 0
    assert file.total_processed_rows == 0
    assert not quarantined
    
    
def test_audit_csv_creates_incoming_timestamp(tmp_path, configured_registry):
    
    fake_csv = """First_Name,Last_Name,Email_Address,Phone_Number,Company_Name,Industry_Sector,Job_Title,Lead_Status,Lead_Score,Created_At,Modified_At
    John,Barker,jbark@example.com,800-555-6498,Super 9 Motels,Hospitality,Buyer,MQL,63,,2023-10-24T14:30:00Z
    Lisa,Rodriguez,lisa_rodriguez@decor4u.com,800-555-9243,Decor For You,Home Goods,Buyer,QUALIFIED,74,2025-01-17T09:58:00Z,2025-11-14T11:32:00Z
    Sandra,Washington,s.washington@example.gov.us,800-555-6601,HUD,Public Sector,,NEW,22,2024-03-03T17:22:00Z,2024-08-13T06:31:00Z
    Lisa,Rodriguez,lisa_rodriguqez@decor4u.com,800-555-9243,Decor For You,Home Goods,Buyer,NEW,38,2025-12-24T13:06:00Z,
    Omar,Halb,omar.s.halb@toney.furniture.com,800-555-4059,Toney Furnishings Ltd.,Furniture,Chief Purchasing Officer,REJECTED,14,2025-05-05T11:22:00Z,2025-06-09T15:55:00Z"""

    fake_uow = FakeUnitOfWork()

    test_file = tmp_path / "fake_leads.csv"
    test_file.write_text(fake_csv)
    
    fake_storage = FakeFileStorageManager()
    fake_storage.known_files.add(test_file)
    

    command = AuditCSVCommand(
        file_id=1, 
        filepath=str(test_file), 
        filename=str("fake_leads.csv"),
        original_assumed_type="leads",
        assumed_type="leads",
        potential_types=["leads"],
        is_ambiguous=False,
        attempted_types=[]
)

    with fake_uow as uow: 
        file = File(
        filename=command.filename,
        hashed_file="123", 
        assumed_type=command.original_assumed_type, 
        is_ambiguous=command.is_ambiguous,
        potential_types=command.potential_types if command.potential_types else [command.original_assumed_type],
        status=FileStatus.AUDITING,
        )
        
        uow.files.add(file)
        uow.commit()
    

    messages = audit_csv(command=command, uow_factory=lambda: fake_uow, registry=configured_registry )
    
    with fake_uow as uow: 
        file = uow.files.get(1)     
        quarantined = uow.quarantine.get(1)      

    assert len(messages) > 0 
    all_row_dicts = []
    for msg in messages:
        all_row_dicts.extend(msg.payload)
        
    for row in all_row_dicts:
        assert "incoming_timestamp" in row, "Missing incoming_timestamp field"
        assert row["incoming_timestamp"] is not None


    assert pd.to_datetime(all_row_dicts[0]["incoming_timestamp"]) == pd.to_datetime("2023-10-24T14:30:00Z")
    assert pd.to_datetime(all_row_dicts[1]["incoming_timestamp"]) == pd.to_datetime("2025-11-14T11:32:00Z")
    assert pd.to_datetime(all_row_dicts[2]["incoming_timestamp"]) == pd.to_datetime("2024-08-13T06:31:00Z")
    assert pd.to_datetime(all_row_dicts[3]["incoming_timestamp"]) == pd.to_datetime("2025-12-24T13:06:00Z")
    assert pd.to_datetime(all_row_dicts[4]["incoming_timestamp"]) == pd.to_datetime("2025-06-09T15:55:00Z")

def test_audit_csv_rejects_extra_timestamp_columns(tmp_path, configured_registry):
    fake_csv = """First_Name,Last_Name,Email_Address,Phone_Number,Company_Name,Industry_Sector,Job_Title,Lead_Status,Lead_Score,Created_At,created_at,Modified_At
    John,Barker,jbark@example.com,800-555-6498,Super 9 Motels,Hospitality,Buyer,MQL,63,,2023-10-24T14:30:00Z,2023-10-24T14:30:00Z
    Lisa,Rodriguez,lisa_rodriguez@decor4u.com,800-555-9243,Decor For You,Home Goods,Buyer,QUALIFIED,74,2025-01-17T09:58:00Z,,2025-11-14T11:32:00Z
    Sandra,Washington,s.washington@example.gov.us,800-555-6601,HUD,Public Sector,NEW,22,,2024-03-03T17:22:00Z,2024-08-13T06:31:00Z
    Lisa,Rodriguez,lisa_rodriguqez@decor4u.com,800-555-9243,Decor For You,Home Goods,Buyer,NEW,38,2025-12-24T13:06:00Z,,
    Omar,Halb,omar.s.halb@toney.furniture.com,800-555-4059,Toney Furnishings Ltd.,Chief Purchasing Officer,REJECTED,14,2025-05-05T11:22:00Z,2025-06-09T15:55:00Z,"""

    fake_uow = FakeUnitOfWork()

    test_file = tmp_path / "fake_leads.csv"
    test_file.write_text(fake_csv)
    
    fake_storage = FakeFileStorageManager()
    fake_storage.known_files.add(test_file)
    
    command = AuditCSVCommand(
        file_id=1, 
        filepath=str(test_file), 
        filename=str("fake_leads.csv"),
        original_assumed_type="leads",
        assumed_type="leads",
        potential_types=["leads"],
        is_ambiguous=False,
        attempted_types=[]
)
    
    with fake_uow as uow: 
        file = File(
        filename=command.filename,
        hashed_file="123", 
        assumed_type=command.original_assumed_type, 
        is_ambiguous=command.is_ambiguous,
        potential_types=command.potential_types if command.potential_types else [command.original_assumed_type],
        status=FileStatus.AUDITING,
        )
        
        uow.files.add(file)
        uow.commit()

    messages = audit_csv(command=command, uow_factory=lambda: fake_uow, registry=configured_registry )
    
    with fake_uow as uow: 
        file = uow.files.get(1)     
        quarantined = uow.quarantine.get(1)      

    assert len(messages) == 1
    assert isinstance(messages[0], SchemaDriftDetected)
    assert not quarantined
    assert file.total_processed_rows == 0
    assert file.quarantined_rows == 0
    assert messages[0].reason == "Extra timestamp fields." 



def test_audit_csv_rejects_missing_timestamps(tmp_path, configured_registry):
    fake_csv = """First_Name,Last_Name,Email_Address,Phone_Number,Company_Name,Industry_Sector,Job_Title,Lead_Status,Lead_Score
    John,Barker,jbark@example.com,800-555-6498,Super 9 Motels,Hospitality,Buyer,MQL,63
    Lisa,Rodriguez,lisa_rodriguez@decor4u.com,800-555-9243,Decor For You,Home Goods,Buyer,QUALIFIED,74
    Sandra,Washington,s.washington@example.gov.us,800-555-6601,HUD,Public Sector,NEW,22
    Lisa,Rodriguez,lisa_rodriguqez@decor4u.com,800-555-9243,Decor For You,Home Goods,Buyer,NEW,38
    Omar,Halb,omar.s.halb@toney.furniture.com,800-555-4059,Toney Furnishings Ltd.,Chief Purchasing Officer,REJECTED"""

    fake_uow = FakeUnitOfWork()

    test_file = tmp_path / "fake_leads.csv"
    test_file.write_text(fake_csv)
    
    fake_storage = FakeFileStorageManager()
    fake_storage.known_files.add(test_file)
    
    command = AuditCSVCommand(
        file_id=1, 
        filepath=str(test_file), 
        filename=str("fake_leads.csv"),
        original_assumed_type="leads",
        assumed_type="leads",
        potential_types=["leads"],
        is_ambiguous=False,
        attempted_types=[]
)

    with fake_uow as uow: 
        file = File(
        filename=command.filename,
        hashed_file="123", 
        assumed_type=command.original_assumed_type, 
        is_ambiguous=command.is_ambiguous,
        potential_types=command.potential_types if command.potential_types else [command.original_assumed_type],
        status=FileStatus.AUDITING,
        )
        
        uow.files.add(file)
        uow.commit()


    messages = audit_csv(command=command, uow_factory=lambda: fake_uow, registry=configured_registry )
    
    with fake_uow as uow: 
        file = uow.files.get(1)     
        quarantined = uow.quarantine.get(1)      
        
    assert len(messages) == 1
    assert isinstance(messages[0], SchemaDriftDetected)
    assert file.total_processed_rows == 0
    assert file.quarantined_rows == 0
    assert not quarantined
    assert messages[0].reason == "Missing required timestamp field(s) for file."
    

def test_audit_csv_quarantined_missing_timestamp_fields(tmp_path, configured_registry):
    fake_csv = """First_Name,Last_Name,Email_Address,Phone_Number,Company_Name,Industry_Sector,Job_Title,Lead_Status,Lead_Score,Created_At,Modified_At
    John,Barker,jbark@example.com,800-555-6498,Super 9 Motels,Hospitality,Buyer,MQL,63,,
    Lisa,Rodriguez,lisa_rodriguez@decor4u.com,800-555-9243,Decor For You,Home Goods,Buyer,QUALIFIED,74,2025-01-17T09:58:00Z,2025-11-14T11:32:00Z
    Sandra,Washington,s.washington@example.gov.us,800-555-6601,HUD,Public Sector,,NEW,22,2024-03-03T17:22:00Z,2024-08-13T06:31:00Z
    Lisa,Rodriguez,lisa_rodriguqez@decor4u.com,800-555-9243,Decor For You,Home Goods,Buyer,NEW,38,2025-12-24T13:06:00Z,
    Omar,Halb,omar.s.halb@toney.furniture.com,800-555-4059,Toney Furnishings Ltd.,Furniture,Chief Purchasing Officer,REJECTED,14,2025-05-05T11:22:00Z,2025-06-09T15:55:00Z"""

    # line 1 (no timestamp fields) should be quarantined
   
    fake_uow = FakeUnitOfWork()
    test_file = tmp_path / "fake_leads.csv"
    test_file.write_text(fake_csv)
    
    fake_storage = FakeFileStorageManager()
    fake_storage.known_files.add(test_file)
    
    command = AuditCSVCommand(
        file_id=1, 
        filepath=str(test_file), 
        filename=str("fake_leads.csv"),
        original_assumed_type="leads",
        assumed_type="leads",
        potential_types=["leads"],
        is_ambiguous=False,
        attempted_types=[]
)
    
    with fake_uow as uow: 
        file = File(
        filename=command.filename,
        hashed_file="123", 
        assumed_type=command.original_assumed_type, 
        is_ambiguous=command.is_ambiguous,
        potential_types=command.potential_types if command.potential_types else [command.original_assumed_type],
        status=FileStatus.AUDITING,
        )
        
        uow.files.add(file)
        uow.commit()

    messages = audit_csv(command=command, uow_factory=lambda: fake_uow, registry=configured_registry )
    
    with fake_uow as uow: 
        file = uow.files.get(1)     
        quarantined = uow.quarantine.get(1)  
        payload = quarantined[0]

    assert len(messages) == 2
    assert isinstance(messages[0], ValidateDataCommand)
    assert isinstance(messages[1], ValidateDataCommand)
    assert len(quarantined) == 1
    assert file.total_processed_rows == 1
    assert file.quarantined_rows == 1
    assert payload.line_number == 2

    
    

def test_audit_csv_quarantined_reversed_timestamps(tmp_path, configured_registry):
    fake_csv = """First_Name,Last_Name,Email_Address,Phone_Number,Company_Name,Industry_Sector,Job_Title,Lead_Status,Lead_Score,Created_At,Modified_At
    John,Barker,jbark@example.com,800-555-6498,Super 9 Motels,Hospitality,Buyer,MQL,63,,2023-10-24T14:30:00Z
    Lisa,Rodriguez,lisa_rodriguez@decor4u.com,800-555-9243,Decor For You,Home Goods,Buyer,QUALIFIED,74,2025-01-17T09:58:00Z,2025-11-14T11:32:00Z
    Sandra,Washington,s.washington@example.gov.us,800-555-6601,HUD,Public Sector,,NEW,22,2024-08-13T06:31:00Z,2024-03-03T17:22:00Z
    Lisa,Rodriguez,lisa_rodriguqez@decor4u.com,800-555-9243,Decor For You,Home Goods,Buyer,NEW,38,2025-12-24T13:06:00Z,
    Omar,Halb,omar.s.halb@toney.furniture.com,800-555-4059,Toney Furnishings Ltd.,Furniture,Chief Purchasing Officer,REJECTED,14,2025-05-05T11:22:00Z,2025-06-09T15:55:00Z"""

    # line 1 (no timestamp fields) should be quarantined
   
    fake_uow = FakeUnitOfWork()
    test_file = tmp_path / "fake_leads.csv"
    test_file.write_text(fake_csv)
    
    fake_storage = FakeFileStorageManager()
    fake_storage.known_files.add(test_file)
    
    command = AuditCSVCommand(
        file_id=1, 
        filepath=str(test_file), 
        filename=str("fake_leads.csv"),
        original_assumed_type="leads",
        assumed_type="leads",
        potential_types=["leads"],
        is_ambiguous=False,
        attempted_types=[]
)
    
    with fake_uow as uow: 
        file = File(
        filename=command.filename,
        hashed_file="123", 
        assumed_type=command.original_assumed_type, 
        is_ambiguous=command.is_ambiguous,
        potential_types=command.potential_types if command.potential_types else [command.original_assumed_type],
        status=FileStatus.AUDITING,
        )
        
        uow.files.add(file)
        uow.commit()

    messages = audit_csv(command=command, uow_factory=lambda: fake_uow, registry=configured_registry )
    
    with fake_uow as uow: 
        file = uow.files.get(1)     
        quarantined = uow.quarantine.get(1)      
        payload = quarantined[0]

    assert len(messages) == 2
    assert isinstance(messages[0], ValidateDataCommand)
    assert isinstance(messages[1], ValidateDataCommand)
    assert len(quarantined) == 1
    assert file.total_processed_rows == 1
    assert file.quarantined_rows == 1
    assert payload.line_number == 4
  


def test_audit_csv_checks_quarantine_threshold_passed(tmp_path, configured_registry):
    
    fake_csv = """SKU_Code,Product_Name,Category,Customer_ID,Region,Industry,Quantity,Revenue,Transaction_Date,Transaction_ID
    UGLY_TCHOTCHKE,Ugly Tchotchke,,CUST-598741,Northwest,Home Goods,56,670.12,2023-10-24,TXN-001 
    SQUISHY_SOFA_BEIGE,Squishy Sofa (Beige),Furniture,,Southeast,Office,,998.00,2025-03-29,TXN-002
    ERSATZ_ENDTABLE,Ersatz End Table,Furniture,CUST-913527,Northeast,Hospitality,40,1320,2024-02-06,TXN-003
    SAD_CLOWN_PTG,Sad Clown Painting,Decor,CUST-546358,Southwest,Public Sector,5,250,2024-07-31,TXN-004
    COL_RUG,Colorful Rug,Decor,CUST-726097,MidAtlantic,Hospitality,72,7272,2023-07-22,TXN-005"""

    # lines 1, 2, and 3 are missing values -- 3 of 5 lines should pass threshold and fail

    fake_uow = FakeUnitOfWork()

    test_file = tmp_path / "creative_batch.csv"
    test_file.write_text(fake_csv)
    
    fake_storage = FakeFileStorageManager()
    fake_storage.known_files.add(test_file)
    

    command = AuditCSVCommand(
        file_id=1, 
        filepath=str(test_file), 
        filename=str("creative_batch.csv"),
        original_assumed_type="sales",
        assumed_type="sales",
        potential_types=["sales"],
        is_ambiguous=False,
        attempted_types=[]
)

    with fake_uow as uow: 
        file = File(
        filename=command.filename,
        hashed_file="123", 
        assumed_type=command.original_assumed_type, 
        is_ambiguous=command.is_ambiguous,
        potential_types=command.potential_types if command.potential_types else [command.original_assumed_type],
        status=FileStatus.AUDITING,
        )
        
        uow.files.add(file)
        uow.commit()

    messages = audit_csv(command=command, uow_factory=lambda: fake_uow, registry=configured_registry)
    
    with fake_uow as uow: 
        file = uow.files.get(1)     
        quarantined = uow.quarantine.get(1)      
        
    assert isinstance(messages[0], PandasAuditFailed)
    assert file.quarantined_rows == 0   # initial check creates no quarantined rows (i.e., no rows processed into ORM objs)
    assert file.total_processed_rows == 0  # ditto
    assert file.status == FileStatus.AUDITING   # not updated by domain entity because no rows processed

    

def test_audit_csv_creates_quarantined_rows(tmp_path, configured_registry):
    fake_csv = """SKU_Code,Product_Name,Category,Customer_ID,Region,Industry,Quantity,Revenue,Transaction_Date,Transaction_ID
    UGLY_TCHOTCHKE,Ugly Tchotchke,Decor,CUST-598741,Northwest,Home Goods,56,670.12,2023-10-24,TXN-001 
    SQUISHY_SOFA_BEIGE,,Furniture,CUST-639500,Southeast,Office,4,998.00,2025-03-29,TXN-002
    ERSATZ_ENDTABLE,Ersatz End Table,Furniture,CUST-913527,Northeast,Hospitality,40,1320,2024-02-06,TXN-003
    SAD_CLOWN_PTG,Sad Clown Painting,Decor,CUST-546358,Southwest,Public Sector,5,250,2024-07-31,TXN-004
    COL_RUG,Colorful Rug,Decor,CUST-726097,MidAtlantic,Hospitality,72,7272,2023-07-22,TXN-005"""
    # line 2 is missing data; this is right AT the 20% threshold and should pass; just row 2 should be quarantined.

    fake_uow = FakeUnitOfWork()

    test_file = tmp_path / "creative_batch.csv"
    test_file.write_text(fake_csv)
    
    fake_storage = FakeFileStorageManager()
    fake_storage.known_files.add(test_file)
    

    command = AuditCSVCommand(
        file_id=1, 
        filepath=str(test_file), 
        filename=str("creative_batch.csv"),
        original_assumed_type="sales",
        assumed_type="sales",
        potential_types=["sales"],
        is_ambiguous=False,
        attempted_types=[]
)
    
    
    with fake_uow as uow: 
        file = File(
        filename=command.filename,
        hashed_file="123", 
        assumed_type=command.original_assumed_type, 
        is_ambiguous=command.is_ambiguous,
        potential_types=command.potential_types if command.potential_types else [command.original_assumed_type],
        status=FileStatus.AUDITING,
        )
        
        uow.files.add(file)
        uow.commit()
    
    messages = audit_csv(command=command, uow_factory=lambda: fake_uow, registry=configured_registry)
    
    with fake_uow as uow: 
        file = uow.files.get(1)     
        quarantined = uow.quarantine.get(1)      
        
    
    assert isinstance(messages[0], ValidateDataCommand)
    assert file.quarantined_rows == 1
    assert file.total_processed_rows == 1
    assert quarantined[0].line_number == 3

    
    
def test_audit_csv_creates_correct_batches(tmp_path, configured_registry):
    # Here we're just looking to see if the script is following instructions for batch/chunk size 
    # given in the config for different types and does NOT just use its defaults

    fake_csv1 = """SKU_Code,Product_Name,Category,Customer_ID,Region,Industry,Quantity,Revenue,Transaction_Date,Transaction_ID
    UGLY_TCHOTCHKE,Ugly Tchotchke,Decor,CUST-598741,Northwest,Home Goods,56,670.12,2023-10-24,TXN-001 
    SQUISHY_SOFA_BEIGE,Squishy Sofa (Beige),Furniture,CUST-639500,Southeast,Office,4,998.00,2025-03-29,TXN-002
    ERSATZ_ENDTABLE,Ersatz End Table,Furniture,CUST-913527,Northeast,Hospitality,40,1320,2024-02-06,TXN-003
    SAD_CLOWN_PTG,Sad Clown Painting,Decor,CUST-546358,Southwest,Public Sector,5,250,2024-07-31,TXN-004
    COL_RUG,Colorful Rug,Decor,CUST-726097,MidAtlantic,Hospitality,72,7272,2023-07-22,TXN-005"""
    
    fake_uow = FakeUnitOfWork()

    test_file1 = tmp_path / "creative_batch.csv"
    test_file1.write_text(fake_csv1)
    
    fake_storage = FakeFileStorageManager()
    fake_storage.known_files.add(test_file1)
   

    command1 = AuditCSVCommand(
        file_id=1, 
        filepath=str(test_file1), 
        filename=str("creative_batch.csv"),
        original_assumed_type="sales",
        assumed_type="sales",
        potential_types=["sales"],
        is_ambiguous=False,
        attempted_types=[]
)
    
    with fake_uow as uow: 
        file = File(
        filename=command1.filename,
        hashed_file="123", 
        assumed_type=command1.original_assumed_type, 
        is_ambiguous=command1.is_ambiguous,
        potential_types=command1.potential_types if command1.potential_types else [command1.original_assumed_type],
        status=FileStatus.AUDITING,
        )
        
        uow.files.add(file)
        uow.commit()
    
    messages1 = audit_csv(command=command1, uow_factory=lambda: fake_uow, registry=configured_registry )
    
    
    fake_csv2 = """First_Name,Last_Name,Email_Address,Phone_Number,Company_Name,Industry_Sector,Job_Title,Lead_Status,Lead_Score,Created_At,Modified_At
    John,Barker,jbark@example.com,800-555-6498,Super 9 Motels,Hospitality,Buyer,MQL,63,2023-10-24T14:30:00Z,2023-10-24T14:30:00Z
    Lisa,Rodriguez,lisa_rodriguez@decor4u.com,800-555-9243,Decor For You,Home Goods,Buyer,QUALIFIED,74,2025-01-17T09:58:00Z,2025-11-14T11:32:00Z
    Sandra,Washington,s.washington@example.gov.us,800-555-6601,HUD,Public Sector,,NEW,22,2024-03-03T17:22:00Z,2024-08-13T06:31:00Z
    Lisa,Rodriguez,lisa_rodriguqez@decor4u.com,800-555-9243,Decor For You,Home Goods,Buyer,NEW,38,2025-12-24T13:06:00Z,
    Omar,Halb,omar.s.halb@toney.furniture.com,800-555-4059,Toney Furnishings Ltd.,Furniture,Chief Purchasing Officer,REJECTED,14,2025-05-05T11:22:00Z, 2025-06-09T15:55:00Z"""

    test_file2 = tmp_path / "fake_leads.csv"
    test_file2.write_text(fake_csv2)
    
    fake_storage = FakeFileStorageManager()
    fake_storage.known_files.add(test_file2)
    
    command2 = AuditCSVCommand(
        file_id=2, 
        filepath=str(test_file2), 
        filename=str("fake_leads.csv"),
        original_assumed_type="leads",
        assumed_type="leads",
        potential_types=["leads"],
        is_ambiguous=False,
        attempted_types=[]
)

    with fake_uow as uow: 
        file = File(
        filename=command2.filename,
        hashed_file="456", 
        assumed_type=command2.original_assumed_type, 
        is_ambiguous=command2.is_ambiguous,
        potential_types=command2.potential_types if command2.potential_types else [command2.original_assumed_type],
        status=FileStatus.AUDITING,
        )
        
        uow.files.add(file)
        uow.commit()

    messages2 = audit_csv(command=command2, uow_factory=lambda: fake_uow, registry=configured_registry )

    # The sales batch size is 3; the leads batch size is 2. There should be two batches for sales and 3 for leads.

    with fake_uow as uow: 
        file1 = uow.files.get(1)
        file2 = uow.files.get(2)

    
    assert len(messages1) == 2
    assert isinstance(messages1[0], ValidateDataCommand)
    assert isinstance(messages1[1], ValidateDataCommand)
    assert len(file1.expected_batches) == 2
    assert len(messages2) == 3
    assert isinstance(messages2[0], ValidateDataCommand)
    assert isinstance(messages2[1], ValidateDataCommand)
    assert isinstance(messages2[2], ValidateDataCommand)
    assert len(file2.expected_batches) == 3

def test_attempt_retry_attempts_retry(tmp_path, configured_registry):
    
    fake_csv = """SKU_Code,Product_Name,Category,Customer_ID,Region,Industry,Quantity,Revenue,Transaction_Date,Transaction_ID, Lead_Score,Created_At,Modified_At
    UGLY_TCHOTCHKE,Ugly Tchotchke,Decor,CUST-598741,Northwest,Home Goods,56,670.12,2023-10-24,TXN-001,6,2023-10-24T14:30:00Z, 2023-10-24T14:30:00Z
    SQUISHY_SOFA_BEIGE,Squishy Sofa (Beige),Furniture,CUST-639500,Southeast,Office,4,998.00,2025-03-29,TXN-002,4,2025-01-17T09:58:00Z,2025-11-14T11:32:00Z
    ERSATZ_ENDTABLE,Ersatz End Table,Furniture,CUST-913527,Northeast,Hospitality,40,1320,2024-02-06,TXN-003,333
    SAD_CLOWN_PTG,Sad Clown Painting,Decor,CUST-546358,Southwest,Public Sector,5,250,2024-07-31,TXN-004,92
    COL_RUG,Colorful Rug,Decor,CUST-726097,MidAtlantic,Hospitality,72,7272,2023-07-22,TXN-005,57"""

    # This is our super wacky batch that has the key fields for both leads (Lead_Score) AND sales (Transaction_ID and SKU_Code)
    # we're assuming it has now failed audit_csv once for its original assumed type ("leads")
    # attempt_retry should create an AuditCSVCommand to try it as a "sale" now.
    
    fake_uow = FakeUnitOfWork()

    test_file = tmp_path / "creative_batch.csv"
    test_file.write_text(fake_csv)
    
    fake_storage = FakeFileStorageManager()
    fake_storage.known_files.add(test_file)
    
    event = PandasAuditFailed(
        file_id=1, 
        filepath=str(test_file), 
        filename=str("creative_batch.csv"),
        original_assumed_type="leads",
        assumed_type="leads",
        potential_types=["leads", "sales"],
        is_ambiguous=True,
        attempted_types=[]
)
    
    with fake_uow as uow: 
        file = File(
        filename=event.filename,
        hashed_file="123", 
        assumed_type=event.original_assumed_type, 
        is_ambiguous=event.is_ambiguous,
        potential_types=event.potential_types if event.potential_types else [event.original_assumed_type],
        status=FileStatus.AUDITING,
        )
        
        uow.files.add(file)
        uow.commit()

    messages = attempt_retry(event=event, uow_factory=lambda: fake_uow)
    new_command = messages[0] 
    
    assert len(messages) == 1
    assert isinstance(messages[0], AuditCSVCommand)
    assert new_command.attempted_types == ["leads"]
    assert new_command.assumed_type == "sales"
    assert new_command.original_assumed_type == "leads"
    
def test_attempt_retry_stops_if_maxxed_out(tmp_path, configured_registry):

    fake_csv = """SKU_Code,Product_Name,Category,Customer_ID,Region,Industry,Quantity,Revenue,Transaction_Date,Transaction_ID, Lead_Score
    UGLY_TCHOTCHKE,Ugly Tchotchke,Decor,,Northwest,Home Goods,56,670.12,2023-10-24,TXN-001,6
    SQUISHY_SOFA_BEIGE,Squishy Sofa (Beige),Furniture,CUST-639500,Southeast,Office,,998.00,2025-03-29,TXN-002,4
    ERSATZ_ENDTABLE,,Furniture,CUST-913527,Northeast,Hospitality,40,1320,2024-02-06,TXN-003,333
    SAD_CLOWN_PTG,Sad Clown Painting,Decor,CUST-546358,Southwest,Public Sector,5,250,2024-07-31,TXN-004,92
    COL_RUG,Colorful Rug,Decor,CUST-726097,MidAtlantic,Hospitality,72,7272,2023-07-22,TXN-005,57"""

    # It's the wacky batch once more, only tweaked so that it is ALSO doesn't pass the quarantine threshold test for "sales."
    # Here we assume it's been tested as its original assumed type (leads) and failed there; then it was tested again for 
    # its other potential type (sales) and has failed (3 incorrect lines = more than 20% of rows need quarantine.)
    # The retry attempts are maxxed out and it should return a SchemaDriftDetetected event.
    
    fake_uow = FakeUnitOfWork()

    test_file = tmp_path / "creative_batch.csv"
    test_file.write_text(fake_csv)
    
    fake_storage = FakeFileStorageManager()
    fake_storage.known_files.add(test_file)
    
    event = PandasAuditFailed(
        file_id=1, 
        filepath=str(test_file), 
        filename=str("creative_batch.csv"),
        original_assumed_type="leads",
        assumed_type="sales",
        potential_types=["leads", "sales"],
        is_ambiguous=True,
        attempted_types=["leads", "sales"]
)
    
    with fake_uow as uow: 
        file = File(
        filename=event.filename,
        hashed_file="123", 
        assumed_type=event.original_assumed_type, 
        is_ambiguous=event.is_ambiguous,
        potential_types=event.potential_types if event.potential_types else [event.original_assumed_type],
        status=FileStatus.AUDITING,
        )
        uow.files.add(file)
        uow.commit()
    
    messages = attempt_retry(event=event, uow_factory=lambda: fake_uow)
    
    new_message = messages[0]
    
    assert len(messages) == 1
    assert isinstance(new_message, SchemaDriftDetected)
    assert new_message.assumed_type == "leads"
    assert new_message.reason == "Ambiguously typed data failed Pandas audit for all potential types."     