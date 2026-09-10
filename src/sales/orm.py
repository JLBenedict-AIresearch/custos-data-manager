# src.sales.orm

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.infrastructure.database import Base

# These tables are arranged using the Star Method 
# and include a central Fact Sales table and multiple Dimension tables for Product, Date, and Customer.

class DimProductORM(Base):

    """
    ORM model representing a product dimension entity.

    This class maps to the 'dim_products' table. It persists descriptive 
    attributes about inventory items, allowing for categorical filtering 
    in sales reporting.

    Attributes:
        id (int): The primary key.
        sku (str): The unique stock keeping unit identifier, indexed.
        name (str): The name of the product.
        category (str): The primary product grouping, indexed.
    """
    __tablename__ = "dim_products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sku: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String, index=True)
    sales: Mapped[list["FactSaleORM"]] = relationship(back_populates="product")

    
    
class DimCustomerORM(Base):
    """
    ORM model representing a customer dimension entity.

    This class maps to the 'dim_customers' table. It persists descriptive 
    attributes about the purchasing entity, enabling demographic analysis.

    Attributes:
        id (int): The primary key.
        customer_identifier (str): The unique internal CRM ID (indexed).
        region (str): The geographic sales territory.
        industry (str): The commercial sector of the customer.
    """
    __tablename__ = "dim_customers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_identifier: Mapped[str] = mapped_column(String, unique=True, index=True)
    region: Mapped[str] = mapped_column(String)
    industry: Mapped[str] = mapped_column(String)

    sales: Mapped[list["FactSaleORM"]] = relationship(back_populates="customer")
    

class DimDateORM(Base):
    """
    ORM model representing a calendar date dimension entity.

    This class maps to the 'dim_dates' table. It persists pre-calculated 
    calendar attributes, enabling highly optimized temporal filtering 
    and aggregation in sales reporting without requiring on-the-fly SQL date math.

    Attributes:
        id (int): The primary key =  smart integer (e.g., 20260705).
        full_date (date): The full calendar date.
        year (int): The calendar year.
        quarter (int): The fiscal calendar quarter (1-4).
        month (int): The calendar month (1-12).
        day (int): The day of the month (1-31).
        is_weekend (bool): True if the date falls on a Saturday or Sunday.
        is_holiday (bool): True if the date is a recognized public or corporate holiday.
    """
    __tablename__ = "dim_dates"
    
    __table_args__ = (
        CheckConstraint('quarter >= 1 AND quarter <= 4', name='check_valid_quarter'),
        CheckConstraint('month >= 1 AND month <= 12', name='check_valid_month'),
        CheckConstraint('day >= 1 AND day <= 31', name='check_valid_day')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False, index=True)
    full_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    year: Mapped[int] = mapped_column(Integer)
    quarter: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    day: Mapped[int] = mapped_column(Integer)
    is_weekend: Mapped[bool] = mapped_column(Boolean, default=False)
    is_holiday: Mapped[bool] = mapped_column(Boolean, default=False)

    sales: Mapped[list["FactSaleORM"]] = relationship(back_populates="sale_date")


class FactSaleORM(Base):
    """
    ORM model representing a quantitative sales transaction.

    This class maps to the 'fact_sales' table. As the central fact table 
    in the star schema, it persists measurable metrics (facts) alongside 
    foreign keys that route to descriptive dimension tables. Multiple attributes are 
    indexed here to permit sales analysis and idempotency checks.

    Attributes:
        id (int): The primary key.
        product_id (int): Foreign key linking to DimProduct, indexed.
        customer_id (int): Foreign key linking to DimCustomer, indexed.
        date_id (int): Foreign key linking to DimDate, indexed.
        quantity_sold (int): The number of individual units purchased.
        revenue_amount (float): The total monetary value of the transaction, indexed.
        sale_timestamp (datetime): The exact timestamp of the transaction execution.
        transaction_id (str): The id of the transaction, indexed.
        product (DimProduct): The parent product entity.
        customer (DimCustomer): The parent customer entity.
    """
    __tablename__ = "fact_sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_file_id: Mapped[int] = mapped_column(Integer, ForeignKey("files.id"), index=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_products.id"), index=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_customers.id"), index=True)
    date_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_dates.id"), index=True)
    quantity_sold: Mapped[int] = mapped_column(Integer)
    revenue_amount: Mapped[float] = mapped_column(Float, index=True)
    sale_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    transaction_id: Mapped[str] = mapped_column(String, index=True)
    product: Mapped["DimProductORM"] = relationship(back_populates="sales")
    customer: Mapped["DimCustomerORM"] = relationship(back_populates="sales")
    sale_date: Mapped["DimDateORM"] = relationship(back_populates="sales")
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

