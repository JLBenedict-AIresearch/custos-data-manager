# tests.conftest.fake_lead_repository

from datetime import datetime
from src.infrastructure.utils import calculate_email_row_hash
from src.leads.domain import Lead, LeadSnapshot, LeadStatus, AlertTeam, MQLAlert
from src.leads.repo_interface import AbstractLeadRepository

class FakeLeadRepository(AbstractLeadRepository):
    def __init__(self): 
        self._leads: set[Lead] = set()
        self._alert_team: set[AlertTeam] = set()
        self._alerts: set[int] = set()

    def add(self, entity: Lead) -> None:
        if not self.check_exists(entity.email):
            ids = [lead.id for lead in self._leads if lead.id is not None]
            entity.id = max(ids, default=0) + 1
            entity.marketing_qualify()
            self._leads.add(entity)
        else: 
            self.update(entity)
    
    def check_exists(self, identifier) -> bool: 
        identifier = str(identifier)
        existing_lead = next((lead for lead in self._leads if lead.email == identifier), None) 
        return True if existing_lead else False

    def delete(self, identifier):
        to_delete = next((lead for lead in self._leads if lead.email == identifier), None)
        if to_delete: 
            self._leads.remove(to_delete)
        
    def get(self, identifier) -> Lead | None:
        """Looks up a lead by email (the natural business key)."""
        return next((lead for lead in self._leads if lead.email == identifier), None) 
    
    def update(self, entity: Lead):
        lead_to_update = next((lead for lead in self._leads if lead.email == entity.email), None)
        entity.marketing_qualify()
        if lead_to_update:
            entity.id = lead_to_update.id
            self._leads.remove(lead_to_update)
            self._leads.add(entity)
        else:
            self.add(entity)

    def get_by_source_file(self, file_id: int) -> list[Lead]:
        """
        Mimics the OUTER JOIN by checking both the parent entity and its updates history.
        """
        affected_leads = []
        for lead in self._leads:
            if lead.source_file_id == file_id:
                affected_leads.append(lead)
                continue
            
            if hasattr(lead, "updates") and any(u.source_file_id == file_id for u in lead.updates):
                affected_leads.append(lead)
                
        return affected_leads
    
    def delete_by_source_file(self, file_id: int): 
        """
        Exactly mirrors the SQLAlchemy implementation, calling the domain entity's
        rollback logic and applying the results.
        """
        affected_leads = self.get_by_source_file(file_id)
        
        if not affected_leads:
            return
            
        for lead in affected_leads:
            survives = lead.rollback(file_id)
            
            if not survives:
                self.delete(lead.email)
            else:
                self.update(lead)


    def get_mql_leads(self) -> list[Lead] | None:
        """Gets leads with status NEW for which alerts have NOT been sent."""
        mql_leads = [lead for lead in self._leads if lead.status == LeadStatus.MQL]        
       
        return [lead for lead in self._leads if lead.id not in self._alerts]
        

    def add_mql_alert(self, lead_id: int):
        self._alerts.add(lead_id)
    
    def check_mql_alert_exists(self, lead_id: int) -> bool:
        check = next(alert for alert in self._alerts if alert == lead_id)
        return True if check is not None else False
    
    def check_team_member_exists(self, email: str) -> bool:
        normalized_email = email.strip().lower()
        return any(member.email == normalized_email for member in self._alert_team)
    
    def add_or_update_alert_team_member(self, member: AlertTeam):
        normalized_email = member.email.strip().lower()
        hashed = calculate_email_row_hash(normalized_email)
        result = next((member for member in self._alert_team if member.email_hash == hashed), None)
        ids = [member.id for member in self._alert_team if member.id is not None]
        
        if not result: 
            member.id = max(ids, default=0) + 1
            member.email = normalized_email
            member.email_hash = hashed
            self._alert_team.add(member)
        else: 
            result.first_name = member.first_name
            result.last_name = member.last_name
            result.sectors = member.sectors
    
    def get_alert_team_member(self, email: str) -> AlertTeam | None:
        normalized_email = email.strip().lower()
        hashed = calculate_email_row_hash(normalized_email)
        return next((member for member in self._alert_team if member.email_hash == hashed), None)
         

    def get_alert_team_all(self) -> list[AlertTeam]: 
        
        return list(self._alert_team)

    
    def update_alert_team_member(self, member: AlertTeam):
        normalized_email = member.email.strip().lower()
        hashed = calculate_email_row_hash(normalized_email)
        result = next((member for member in self._alert_team if member.email_hash == hashed), None)

        if result:

            result.first_name = member.first_name
            result.last_name = member.last_name
            result.sectors = member.sectors