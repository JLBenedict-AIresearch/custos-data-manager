# src.infrastructure.handlers.alerts

from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
import json
from pathlib import Path
from typing import Callable

from src.bootstrap.dependencies import get_uow
from src.infrastructure.directory import CustosDirectoryManager 
from src.infrastructure.logging import logger
from src.infrastructure.wrappers.safety_wrappers import with_infrastructure_safety, with_logging_context
from src.leads.domain import Lead, MQLAlert, AlertTeam
from src.leads.status_enum import LeadStatus
from src.leads.schemas import LeadContact
from src.pipeline.events import SystemFaultEvent
from src.shared.interfaces.file_storage_interface import AbstractFileStorageManager


def handle_mql_alerts(directory: CustosDirectoryManager, uow_factory: Callable, storage: AbstractFileStorageManager):
    """Finds un-alerted MQLs, generates mock emails, and updates the alert tracker."""
    
    alert_dict = defaultdict(list)
    own_dict = {}
    lead_map = defaultdict(list)
    
    with uow_factory() as uow: 
        members = uow.leads.get_alert_team_all()
        mql_leads = uow.leads.get_mql_leads()

        if not mql_leads or not members: 
            return
        
        for member in members:
            if not member.sectors: 
                continue
            for sector in member.sectors: 
                own_dict[sector] = member.email

 
        for lead in mql_leads: 
            if not lead.sector or lead.sector not in own_dict: 
                team_email = own_dict.get("Other") 
            else:
                team_email = own_dict.get(lead.sector)                 
            
            if team_email:               
                lead_contact = make_contact(lead)
                alert_dict[team_email].append(lead_contact)
                lead_map[team_email].append(lead)
            
        for member in members: 
            mql_list = alert_dict.get(member.email)
            if not mql_list: 
                continue
            email = create_email_body(member, mql_list)
            try: 
                send_email(member.email, email, directory, storage)
                successful_leads = lead_map.get(member.email, [])
                for lead in successful_leads:
                    uow.leads.add_mql_alert(lead.id)
                
            except Exception as e: 
                logger.error("alert_email_failed", email=member.email, error=str(e))
            
        uow.commit()


     
def send_email(address: str, body: str, directory: CustosDirectoryManager, storage: AbstractFileStorageManager):
    """Mocks sending an email by writing a text file to the outgoing_alerts directory."""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_address = address.replace("@", "_at_")
    filename = f"mql_alert_{safe_address}_{timestamp}.txt"
    
    filepath = directory.get_outgoing_alerts_path(filename)
    
    filepath.write_text(body, encoding="utf-8")
    
    
    
def create_email_body(member, mql_list) -> str: 
    
    info_dump = []
    for mql in mql_list: 
        contact = json.dumps(asdict(mql), indent=4) 
        info_dump.append(contact)
    
    
    formatted_leads = "\n\n".join(info_dump)
    
    email = f"""Hi, {member.first_name}!
Here are some new MQL Leads for you to reach out to: 

{formatted_leads}

Have fun with that!
Sincerely,
The Management"""

    return email

    
              
def make_contact(lead: Lead) -> LeadContact:
    lead_contact = LeadContact(
        first_name=lead.first_name,
        last_name=lead.last_name,
        email=lead.email,
        phone=lead.phone,
        score=lead.score,
        company=lead.company,
        sector=lead.sector,
        position=lead.position
    )        
                
    return lead_contact


def send_system_failure_alert(
    event: SystemFaultEvent,
    directory: CustosDirectoryManager,
    storage: AbstractFileStorageManager
):
    """Sends an alert email to the sytem engineering team about a System Fault Event"""


    error_details = getattr(event, 'message', 'Unknown critical error')
        
    email_body = f"""URGENT: SYSTEM HALT DETECTED

The Custos ETL Pipeline has automatically halted to prevent data corruption.

Failure Details:
{error_details}

Please check the system_failure directory and application logs immediately.
"""

    try:
        send_email(
            address="engineering_oncall@custos-sales.local", 
            body=email_body, 
            directory=directory, 
            storage=storage
        )
    except Exception:
        # If the system has already failed, there's not much we can do about it if the email fails to send.
        pass