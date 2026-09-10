# src.infrastructure.base

# This is where to register your ORM base classes for migration so that All Your Base Are Belong to Alembic

from src.files.orm import FileORM
from src.infrastructure.database import Base
from src.leads.orm import AlertTeamORM, LeadAlertORM, LeadORM, LeadSnapshotORM
from src.quarantine.orm import QuarantinedRowORM
from src.sales.orm import DimCustomerORM, DimDateORM, DimProductORM, FactSaleORM

models = [Base, 
          FileORM, 
          LeadSnapshotORM, 
          LeadAlertORM, 
          LeadORM,
          AlertTeamORM, 
          QuarantinedRowORM, 
          FactSaleORM, 
          DimProductORM, 
          DimDateORM, 
          DimCustomerORM
          ]