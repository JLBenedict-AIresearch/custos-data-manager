# tests.integration.test_alerts

# run command: poetry run python -m pytest tests/integration/test_alerts.py

from datetime import datetime, timezone
from pathlib import Path

from src.infrastructure.adapters.file_storage_manager import CustosFileStorageManager
from src.infrastructure.directory import CustosDirectoryManager
from src.infrastructure.handlers.alerts import handle_mql_alerts, send_system_failure_alert
from src.pipeline.events import SystemFaultEvent

from tests.fakes import dummies


def test_mql_alerts_creates_emails(tmp_path, real_uow):
    storage = CustosFileStorageManager()
    directory =CustosDirectoryManager(base_dir=tmp_path)
    directory.setup_directories()
    leads = dummies.get_mql_lead_data()
    team = dummies.get_fake_alert_team()
    file = dummies.get_dummy_leads_file()
    with real_uow as uow: 
        uow.files.add(file)
        for lead in leads: 
            uow.leads.add(lead)
        barker = uow.leads.get("jbark@example.com")
        uow.leads.add_mql_alert(barker.id)
        # this guy should flag as already alerted now and NOT get an email
        
        for t in team: 
            uow.leads.add_or_update_alert_team_member(t)
    
        uow.commit()
            
    handle_mql_alerts(directory=directory, uow_factory=lambda: real_uow, storage=storage)
    
    alerts_dir = directory.outgoing_alerts      
    email_files = list(alerts_dir.glob("*.txt"))
    
    assert len(email_files) == 3
    diego_email = next((f for f in email_files if "diego" in f.name), None)
    lucia_email = next((f for f in email_files if "vanitelli" in f.name), None)
    tony_email = next((f for f in email_files if "nguyen" in f.name), None)
    assert diego_email is not None
    assert lucia_email is not None
    assert tony_email is not None
    diego_content = diego_email.read_text()
    lucia_content = lucia_email.read_text()
    tony_content = tony_email.read_text()
    
    assert "Lisa" in diego_content
    assert "s.washington@example.gov.us" in lucia_content
    assert "Halb" in tony_content
    

def test_send_system_alerts(tmp_path):
    storage = CustosFileStorageManager()
    directory =CustosDirectoryManager(base_dir=tmp_path)
    directory.setup_directories()
    filename="data.csv"
    
    event = SystemFaultEvent(
        timestamp=datetime.now(timezone.utc),
        file_id=1,
        filename=filename,
        filepath=str(directory.get_processing_path(filename)),
        error_type="SystemFault",
        message="Everything just broke."
    )
    
    send_system_failure_alert(event=event, directory=directory, storage=storage)
    
    alerts_dir = directory.outgoing_alerts      
    email_files = list(alerts_dir.glob("*.txt"))
    
    assert len(email_files) == 1
    content = email_files[0].read_text()
    assert "engineering_oncall" in email_files[0].name
    assert "URGENT" in content
    assert "Everything just broke" in content 