# src.sales.domain

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class ProductDetails:
    sku: str
    name: str
    category: str

@dataclass(frozen=True)
class CustomerDetails:
    identifier: str
    region: str
    industry: str


class FactSale:
    def __init__(
        self, 
        source_file_id: int, 
        transaction_id: str,
        sale_date: date,
        quantity_sold: int,
        revenue_amount: float,
        sale_timestamp: datetime,
        product_id: int | None,
        customer_id: int | None,
        date_id: int | None
    ):
        self.source_file_id = source_file_id
        self.transaction_id = transaction_id
        self.sale_date=sale_date
        self.quantity_sold=quantity_sold
        self.revenue_amount=revenue_amount
        self.sale_timestamp=sale_timestamp
        self.product_id=product_id if product_id else None
        self.customer_id=customer_id if customer_id else None
        self.date_id=date_id if date_id else None


    

    