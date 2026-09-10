# src.sales.services

from src.sales.domain import CustomerDetails, FactSale, ProductDetails
from src.sales.schemas import SalesData


def process_sales_record(file_id: int, dto: SalesData) -> list[object]:
    
    payload = []
    date_of_sale = dto.sale_timestamp.date()
    
    fact_sale = FactSale(
        source_file_id=file_id,
        transaction_id=dto.transaction_id,
        sale_date=date_of_sale,
        quantity_sold=dto.quantity_sold,
        revenue_amount=dto.revenue_amount,
        sale_timestamp=dto.sale_timestamp,
        product_id=None,
        customer_id=None,
        date_id=None
    )

    product = ProductDetails(
        sku=dto.sku,
        name=dto.product_name,
        category=dto.category
    )
    
    customer = CustomerDetails(
        identifier=dto.customer_identifier,
        region=dto.region,
        industry=dto.industry
    )
   
    payload.append(fact_sale)
    payload.append(product)
    payload.append(customer)
    return payload
