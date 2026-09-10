# src.bootstrap.seed_team

from src.bootstrap.dependencies import get_uow
from src.infrastructure.utils import calculate_email_row_hash
from src.leads.domain import AlertTeam


def seed_alert_team(uow_factory):
    """Seeds the database with fake sales team members for MQL routing."""
    
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

    with uow_factory() as uow:
        for member in team_members:
            uow.leads.add_or_update_alert_team_member(member)
        
        uow.commit()

if __name__ == "__main__":
    uow_factory = get_uow
    seed_alert_team(uow_factory)