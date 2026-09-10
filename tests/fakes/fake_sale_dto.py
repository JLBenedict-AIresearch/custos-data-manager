
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class FakeSalesData:
    sku: str | None
    product_name: str 
    category: str 

    customer_identifier: str
    region: str 
    industry: str 

    quantity_sold: int 
    revenue_amount: float 
    
    sale_timestamp: datetime 
    transaction_id: str | None