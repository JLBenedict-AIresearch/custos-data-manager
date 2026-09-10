# src.sales.schemas.py

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.shared.errors import CustomerIdentifierError


class SalesRowSchema(BaseModel):
    """
    Validates and standardizes a flat row of incoming sales data.

    This schema acts as the application-level boundary for the sales domain. 
    It ensures that quantitative metrics meet mathematical constraints and 
    that descriptive attributes are properly formatted before the payload 
    is decomposed into the dimensional star schema.

    Attributes:
        sku (str): The product's Stock Keeping Unit (SKU) code.
        product_name (str): The name of the product.
        category (str): The product category.
        customer_identifier (str): The CRM-generated customer ID.
        region (str): The geographic sales region.
        industry (str): The customer's commercial sector.
        quantity_sold (int): The number of units (must be strictly positive).
        revenue_amount (float): The total transaction value (cannot be negative).
        sale_date (datetime): The parsed timestamp of the transaction.
    """
    
    # You can input as aliases the particular column header names expected/used in your enterprise;
    # the aliases given here match the fields that I used in the data/samples csv files.
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    sku: str = Field(..., alias="SKU_Code")
    product_name: str = Field(..., alias="Product_Name")
    category: str = Field(..., alias="Category")

    customer_identifier: str = Field(..., alias="Customer_ID")
    region: str = Field(..., alias="Region")
    industry: str = Field(..., alias="Industry")

    quantity_sold: int = Field(..., gt=0, alias="Quantity")
    revenue_amount: float = Field(..., ge=0.0, alias="Revenue")
    
    sale_timestamp: datetime = Field(..., alias="Transaction_Date")
    transaction_id: str = Field(..., alias="Transaction_ID")
    

    @field_validator('sku')
    @classmethod
    def sanitize_sku(cls, v: str) -> str:
        """Ensures the SKU is strictly uppercase and free of whitespace padding."""
        return v.strip().upper()

    @field_validator('customer_identifier')
    @classmethod
    def validate_customer_id_format(cls, v: str) -> str:
        """Enforces a specific enterprise format for Customer IDs (e.g., 'CUST-XXXX')."""
        cleaned = v.strip().upper()
        if not cleaned.startswith("CUST-"):
            raise CustomerIdentifierError("CUST_ID_ERR", "Customer identifier must begin wtih 'CUST-' prefix.")
        return cleaned
    
@dataclass(frozen=True)
class SalesData:
    sku: str 
    product_name: str 
    category: str 

    customer_identifier: str
    region: str 
    industry: str 

    quantity_sold: int 
    revenue_amount: float 
    
    sale_timestamp: datetime 
    transaction_id: str 