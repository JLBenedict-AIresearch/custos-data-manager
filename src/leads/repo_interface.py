# src.leads.repo_interface.py

from abc import abstractmethod
from datetime import datetime

from src.leads.domain import Lead, AlertTeam, MQLAlert
from src.shared.interfaces.repository_interface import AbstractUpdatableDomainRepository


class AbstractLeadRepository(AbstractUpdatableDomainRepository):
    
    @abstractmethod
    def get_mql_leads(self) -> list[Lead] | None:
        raise NotImplementedError

    @abstractmethod
    def add_mql_alert(self, lead_id: int):
        raise NotImplementedError
    
    @abstractmethod
    def check_mql_alert_exists(self, lead_id: int) -> bool:
        raise NotImplementedError
        
    @abstractmethod
    def check_team_member_exists(self, email: str) -> bool:
        raise NotImplementedError
    
    @abstractmethod
    def add_or_update_alert_team_member(self, member: AlertTeam):
        raise NotImplementedError
    
    @abstractmethod
    def get_alert_team_member(self, email: str) -> AlertTeam | None:
        raise NotImplementedError\
            
    @abstractmethod
    def get_alert_team_all(self) -> list[AlertTeam]: 
        raise NotImplementedError
    
    @abstractmethod
    def update_alert_team_member(self, member: AlertTeam):
        raise NotImplementedError