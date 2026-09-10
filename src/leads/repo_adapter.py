# src.leads.repo_adapter

from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from src.infrastructure.utils import calculate_email_row_hash
from src.leads.domain import AlertTeam, Lead, LeadStatus, LeadSnapshot, MQLAlert
from src.leads.orm import AlertTeamORM, LeadAlertORM, LeadORM, LeadSnapshotORM
from src.leads.repo_interface import AbstractLeadRepository
from src.leads.schemas import LeadData
from src.shared.errors import WrongTypeError


class SQLAlchemyLeadsRepository(AbstractLeadRepository):
    def __init__(self, session: Session):
        self.session = session
        self.seen: set[Lead] = set()
        self._identity_map: dict[str, tuple[LeadORM, Lead]] = {}

# Internal helper methods

    def _to_domain(self, orm_lead: LeadORM) -> Lead:
        """Rebuilds the pure Domain Lead from the database state."""
        lead = Lead(
            source_file_id=orm_lead.source_file_id,
            custos_timestamp=orm_lead.custos_timestamp,
            first_name=orm_lead.first_name,
            last_name=orm_lead.last_name,
            email=orm_lead.email,
            phone=orm_lead.phone,
            status=LeadStatus(orm_lead.status),
            score=orm_lead.score,
            incoming_timestamp=orm_lead.incoming_timestamp,
            company=orm_lead.company,
            sector=orm_lead.sector,
            position=orm_lead.position, 
            email_hash=orm_lead.email_hash,
            id=orm_lead.id

        )
        
        for orm_update in orm_lead.update_history:
            lead.updates.append(
                LeadSnapshot(
                    id=orm_update.id,
                    source_file_id=orm_update.source_file_id,
                    incoming_timestamp=orm_update.incoming_timestamp,
                    custos_timestamp=orm_update.custos_timestamp,
                    data=LeadData(
                        first_name=orm_update.first_name, 
                        last_name=orm_update.last_name, 
                        email=orm_update.email,
                        phone=orm_update.phone,
                        status=LeadStatus(orm_update.status),
                        score=orm_update.score,
                        company=orm_update.company,
                        sector=orm_update.sector,
                        position=orm_update.position,
                        incoming_timestamp=orm_update.incoming_timestamp
                    ),
                    email_hash=orm_update.email_hash
                )
            )
        return lead

    def _to_orm(self, lead: Lead) -> LeadORM:
        """
        Translates the domain entity to ORM. 
        Updates existing ORM objects if they were previously loaded.
        """
        normalized_email = lead.email.strip().lower()
        mapped = self._identity_map.get(normalized_email)
        orm_lead = mapped[0] if mapped else None

        if not orm_lead:
            orm_lead = LeadORM(email=lead.email)
            self._identity_map[normalized_email] = (orm_lead, lead)
            
        if lead.id is not None: 
            orm_lead.id = lead.id       

        orm_lead.source_file_id = lead.source_file_id
        orm_lead.first_name = lead.first_name
        orm_lead.last_name = lead.last_name
        orm_lead.phone = lead.phone
        orm_lead.company = lead.company
        orm_lead.sector = lead.sector
        orm_lead.position = lead.position
        orm_lead.status = lead.status.value if hasattr(lead.status, "value") else lead.status
        orm_lead.score = lead.score
        orm_lead.incoming_timestamp = lead.incoming_timestamp
        orm_lead.email_hash = lead.email_hash
        orm_lead.custos_timestamp = lead.custos_timestamp

        current_orm_updates = len(orm_lead.update_history)
        for new_update in lead.updates[current_orm_updates:]:
            orm_lead.update_history.append(
                LeadSnapshotORM(
                    id=new_update.id,
                    source_file_id=new_update.source_file_id,
                    incoming_timestamp=new_update.incoming_timestamp,
                    custos_timestamp=new_update.custos_timestamp,
                    first_name=new_update.data.first_name, 
                    last_name=new_update.data.last_name, 
                    email=new_update.data.email,
                    phone=new_update.data.phone,
                    status=new_update.data.status,
                    score=new_update.data.score,
                    company=new_update.data.company,
                    sector=new_update.data.sector,
                    position=new_update.data.position,
                    email_hash=new_update.email_hash
                )
            )

        return orm_lead

# Parent class methods

    def add(self, entity: Lead) -> None:
        """Adds a completely new Lead to the database."""
        normalized_email = entity.email.strip().lower()
        if self.check_exists(normalized_email):
            self.update(entity)
            existing_orm = self._identity_map[normalized_email][0]
            entity.id = existing_orm.id
            self.seen.add(entity)
            return
        
        entity.marketing_qualify()
        orm_lead = self._to_orm(entity)
        self.session.add(orm_lead)
        self.session.flush()
        entity.id = orm_lead.id

        self._identity_map[normalized_email] = (orm_lead, entity)
        self.seen.add(entity)

    def check_exists(self, identifier) -> bool: 
        """Checks if the entity exists by its EMAIL (str)"""
        if not isinstance(identifier, str):
            raise WrongTypeError(f"Lead requires a string identifier but received a {type(identifier).__name__}")
            
        normalized_identifier = identifier.strip().lower()
        hashed_identifier = calculate_email_row_hash(normalized_identifier)
        
        if normalized_identifier in self._identity_map:
            return True
            
        for domain_lead in self.seen:
            if domain_lead.email.strip().lower() == normalized_identifier:
                return True
            
        stmt = select(LeadORM.id).where(LeadORM.email_hash == hashed_identifier)
        return self.session.execute(stmt).scalar_one_or_none() is not None

    def get(self, identifier) -> Lead | None:
        """Retrieves a Lead by EMAIL (identifier: str) and tracks it for future updates."""
        if not isinstance(identifier, str):
            raise WrongTypeError(f"Lead requires a string identifier but received a {type(identifier).__name__}")
        
        normalized_identifier = identifier.strip().lower()
        
        if normalized_identifier in self._identity_map:
            domain_lead = self._identity_map[normalized_identifier][1]
            self.seen.add(domain_lead)
            return domain_lead
        
        hashed_identifier: str = calculate_email_row_hash(normalized_identifier)
        
        stmt = select(LeadORM).options(selectinload(LeadORM.update_history)).where(LeadORM.email_hash == hashed_identifier)
        orm_lead = self.session.execute(stmt).scalar_one_or_none()
        
        if orm_lead:
            domain_lead = self._to_domain(orm_lead)
            self._identity_map[normalized_identifier] = (orm_lead, domain_lead)
            self.seen.add(domain_lead)
            return domain_lead
            
        return None


    def _get_lookup_hash(self, identifier: str) -> str:
        """Returns the identifier directly if it's already a hash, otherwise hashes it."""
        normalized = identifier.strip().lower()
        if len(normalized) == 64 and all(c in '0123456789abcdef' for c in normalized):
            return normalized
        return calculate_email_row_hash(normalized)

    def delete(self, identifier) -> None:
        
        if not isinstance(identifier, str):
            raise WrongTypeError(f"Lead requires a string identifier but received a {type(identifier).__name__}")
        
        hashed_identifier = self._get_lookup_hash(identifier)
        
        stmt = select(LeadORM).where(LeadORM.email_hash == hashed_identifier)
        result = self.session.execute(stmt).scalar_one_or_none()
        
        if result: 
            self.session.delete(result)
            # Cleanup memory map to prevent ghost records
            keys_to_delete = [k for k, v in self._identity_map.items() if v[0].email_hash == hashed_identifier]
            for k in keys_to_delete:
                del self._identity_map[k]

           
    def update(self, lead: Lead) -> None:
        normalized_email = lead.email.strip().lower()
        lead.marketing_qualify()
        
        mapped = self._identity_map.get(normalized_email)
        orm_lead = mapped[0] if mapped else None
        
        if not orm_lead:
            stmt = select(LeadORM).options(selectinload(LeadORM.update_history)).where(LeadORM.email_hash == lead.email_hash)
            orm_lead = self.session.execute(stmt).scalar_one_or_none()
            
        if not orm_lead:
            raise ValueError(f"Cannot update lead {lead.email}; not found in database.")
            
        self._identity_map[normalized_email] = (orm_lead, lead)
        
        self.seen.add(lead)
        
        orm_lead.source_file_id = lead.source_file_id
        orm_lead.first_name = lead.first_name
        orm_lead.last_name = lead.last_name
        orm_lead.phone = lead.phone
        orm_lead.company = lead.company
        orm_lead.sector = lead.sector
        orm_lead.position = lead.position
        orm_lead.status = lead.status.value if hasattr(lead.status, "value") else lead.status
        orm_lead.score = lead.score
        orm_lead.incoming_timestamp = lead.incoming_timestamp
        orm_lead.email_hash = lead.email_hash
        
        existing_updates_dict = {
            (orm_update.source_file_id, orm_update.incoming_timestamp): orm_update 
            for orm_update in orm_lead.update_history
        }

        for domain_update in lead.updates:
            update_key = (domain_update.source_file_id, domain_update.incoming_timestamp)
            
            if update_key not in existing_updates_dict:
                new_orm_update = LeadSnapshotORM(
                    source_file_id=domain_update.source_file_id,
                    lead_id=orm_lead.id,
                    custos_timestamp=domain_update.custos_timestamp,
                    incoming_timestamp=domain_update.incoming_timestamp,
                    first_name=domain_update.data.first_name, 
                    last_name=domain_update.data.last_name, 
                    email=domain_update.data.email,
                    phone=domain_update.data.phone,
                    status=domain_update.data.status,
                    score=domain_update.data.score,
                    company=domain_update.data.company,
                    sector=domain_update.data.sector,
                    position=domain_update.data.position,
                    email_hash=domain_update.email_hash
                )
                orm_lead.update_history.append(new_orm_update)
                existing_updates_dict[update_key] = new_orm_update

                        

    def get_by_source_file(self, file_id: int) -> list[Lead] | None: 
        stmt = (
            select(LeadORM)
            .options(selectinload(LeadORM.update_history)) # CRITICAL: Prevents lazy-load crashes during rollback
            .outerjoin(LeadSnapshotORM, LeadORM.id == LeadSnapshotORM.lead_id) 
            .where(
                or_(
                    LeadORM.source_file_id == file_id,
                    LeadSnapshotORM.source_file_id == file_id
                )
            )
            .distinct()  
        )
        orm_records = self.session.execute(stmt).scalars().all()
        
        domain_leads = []
        for record in orm_records:
            normalized_email = record.email.strip().lower()
            
            # Use the cached domain object if we already have it
            if normalized_email in self._identity_map:
                domain_leads.append(self._identity_map[normalized_email][1])
            else:
                domain_lead = self._to_domain(record)
                self._identity_map[normalized_email] = (record, domain_lead)
                domain_leads.append(domain_lead)
                
        return domain_leads
            

    def delete_by_source_file(self, file_id: int):
        
        affected_leads = self.get_by_source_file(file_id)
        if not affected_leads:
            return
            
        for lead in affected_leads:
            survives = lead.rollback(file_id)
            
            if not survives:
                self.delete(lead.email_hash)
            else:
                self.update(lead)
                    
                # Clean up memory state to stop SQLAlchemy from resurrecting children!!
                orm_lead = next((orm for orm, _ in self._identity_map.values() if orm.email_hash == lead.email_hash), None)
                if orm_lead:
                    orm_lead.update_history = [u for u in orm_lead.update_history if u.source_file_id != file_id]
  
# Distinctive methods for Leads and Lead-related Alerts speciifically

    def _alert_to_domain(self, alert_orm: LeadAlertORM) -> MQLAlert: 
        alert = MQLAlert(
            id=alert_orm.id,
            lead_id=alert_orm.lead_id,
            alert_timestamp=alert_orm.alert_timestamp
        )
        return alert

    def get_mql_leads(self) -> list[Lead] | None:
        """Gets leads with status NEW for which alerts have NOT been sent."""

        stmt = (
            select(LeadORM)
            .outerjoin(LeadAlertORM, LeadORM.id == LeadAlertORM.lead_id)
            .filter(
                LeadORM.status == 'MQL',
                LeadAlertORM.id.is_(None) 
            )
        )
        results = self.session.execute(stmt).scalars().all()
        if results: 
            return [self._to_domain(result) for result in results]

    def add_mql_alert(self, lead_id: int):
        lead_alert_orm = LeadAlertORM(lead_id=lead_id)
        self.session.add(lead_alert_orm)
    
    def check_mql_alert_exists(self, lead_id: int) -> bool:
        stmt = select(LeadAlertORM).where(LeadAlertORM.lead_id == lead_id)
        result = self.session.execute(stmt).scalar_one_or_none()
        return True if result is not None else False
    
    def check_team_member_exists(self, email: str) -> bool:
        normalized_email = email.strip().lower()
        hashed = calculate_email_row_hash(normalized_email)
        stmt = select(AlertTeamORM).where(AlertTeamORM.email_hash == hashed)
        result = self.session.execute(stmt).scalar_one_or_none()
        return True if result is not None else False
    
    def add_or_update_alert_team_member(self, member: AlertTeam):
        normalized_email = member.email.strip().lower()
        hashed = calculate_email_row_hash(normalized_email)
        stmt = select(AlertTeamORM).where(AlertTeamORM.email_hash == hashed)
        result = self.session.execute(stmt).scalar_one_or_none()
        if not result: 
            alert_team_orm = AlertTeamORM(
                first_name=member.first_name,
                last_name=member.last_name,
                email=member.email,
                email_hash=member.email_hash,
                sectors=member.sectors
            )
            self.session.add(alert_team_orm)
        else: 
            result.first_name = member.first_name
            result.last_name = member.last_name
            result.sectors = member.sectors
    
    def get_alert_team_member(self, email: str) -> AlertTeam | None:
        normalized_email = email.strip().lower()
        hashed = calculate_email_row_hash(normalized_email)
        stmt = select(AlertTeamORM).where(AlertTeamORM.email_hash == hashed)
        result = self.session.execute(stmt).scalar_one_or_none()
        if result: 
            domain_model = AlertTeam(
                id = result.id,
                first_name=result.first_name,
                last_name=result.last_name,
                email=result.email,
                email_hash=result.email_hash, 
                sectors=result.sectors
            )
            return domain_model
        return None
    
    def get_alert_team_all(self) -> list[AlertTeam]: 
        stmt = select(AlertTeamORM)
        results = self.session.execute(stmt).scalars().all()
        team_members = []
        for result in results:
            domain_model = AlertTeam(
                id=result.id,
                first_name=result.first_name,
                last_name=result.last_name,
                email=result.email,
                email_hash=result.email_hash,
                sectors=result.sectors
            )
            team_members.append(domain_model)            
        return team_members
    
    def update_alert_team_member(self, member: AlertTeam):
        normalized_email = member.email.strip().lower()
        hashed = calculate_email_row_hash(normalized_email)
        
        stmt = select(AlertTeamORM).where(AlertTeamORM.email_hash == hashed)
        result = self.session.execute(stmt).scalar_one_or_none()
        
        if result:

            result.first_name = member.first_name
            result.last_name = member.last_name
            result.sectors = member.sectors