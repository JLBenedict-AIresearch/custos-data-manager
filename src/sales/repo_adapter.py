# src.sales.repo_adapter

from datetime import datetime

import holidays
from sqlalchemy import select
from sqlalchemy.orm import Session, contains_eager

from src.sales.domain import CustomerDetails, FactSale, ProductDetails
from src.sales.orm import DimCustomerORM, DimDateORM, DimProductORM, FactSaleORM
from src.sales.repo_interface import AbstractSalesRepository
from src.shared.errors import RequiresAdditionalArgsError


class SQLAlchemySalesRepository(AbstractSalesRepository):
    def __init__(self, session: Session):
        self.session = session
        self.seen: set[FactSale] = set()
        self.seen_sales_identifiers: set[tuple] = set()
        self.seen_products: dict[str, int] = {}       # sku: orm_id
        self.seen_customers: dict[str, int] = {}      # cust identifier: orm_id
        self.seen_dates: dict[int, int] = {}          # smart_key_id : orm_id
        self.us_holidays = holidays.US() 

    def get_or_create_product(self, product: ProductDetails) -> int:
    
        if product.sku in self.seen_products: 
            return self.seen_products[product.sku]
    
        stmt = select(DimProductORM).where(DimProductORM.sku == product.sku)
        existing = self.session.execute(stmt).scalar_one_or_none()    
        if existing:
            return existing.id         

        new_product = DimProductORM(sku=product.sku, name=product.name, category=product.category)
        
        self.session.add(new_product)
        self.session.flush() # Flushes to generate the ID
        self.seen_products[product.sku] = new_product.id
        return new_product.id


    def get_or_create_customer(self, customer: CustomerDetails) -> int:
        
        if customer.identifier in self.seen_customers: 
            return self.seen_customers[customer.identifier]
        
        stmt = select(DimCustomerORM).where(DimCustomerORM.customer_identifier == customer.identifier)
        existing = self.session.execute(stmt).scalar_one_or_none()
        if existing:
            return existing.id
        new_customer = DimCustomerORM(
            customer_identifier=customer.identifier,
            region=customer.region,
            industry=customer.industry
        )

        self.session.add(new_customer)
        self.session.flush()
        self.seen_customers[customer.identifier] = new_customer.id
        return new_customer.id

    def get_or_create_date(self, target_date: datetime) -> int:
        
        actual_date = target_date.date()
        # Generates a smart integer key (e.g., 20260824)
        smart_key_id = int(actual_date.strftime("%Y%m%d"))  
        
        if smart_key_id in self.seen_dates:
            return self.seen_dates[smart_key_id]
        
        existing_date = self.session.get(DimDateORM, smart_key_id)

        if existing_date:
            return existing_date.id          

        new_date = DimDateORM(
            id=smart_key_id,
            full_date=target_date,
            year=target_date.year,
            quarter=(target_date.month - 1) // 3 + 1,
            month=target_date.month,
            day=target_date.day,
            is_weekend=(target_date.weekday() >= 5),
            is_holiday=(target_date in self.us_holidays)
        )      

        self.session.add(new_date)
        self.seen_dates[smart_key_id] = new_date.id
        self.session.flush()
        
        return new_date.id

# internal helper methods

    def _to_orm(self, domain_sale: FactSale, product: ProductDetails, customer: CustomerDetails) -> FactSaleORM:
        """Translates the nested domain object into flat foreign keys for the Star Schema."""
        
        product_id = domain_sale.product_id if domain_sale.product_id else self.get_or_create_product(product)        
        customer_id = domain_sale.customer_id if domain_sale.customer_id else self.get_or_create_customer(customer)    
        date_id = domain_sale.date_id if domain_sale.date_id else self.get_or_create_date(domain_sale.sale_timestamp)
        
        return FactSaleORM(
            source_file_id=domain_sale.source_file_id,
            transaction_id=domain_sale.transaction_id,
            product_id=product_id,
            customer_id=customer_id,
            date_id=date_id,
            quantity_sold=domain_sale.quantity_sold,
            revenue_amount=domain_sale.revenue_amount,
            sale_timestamp=domain_sale.sale_timestamp
        )

    def _to_domain(self, orm_sale: FactSaleORM) -> FactSale:
        """Rebuilds the rich, nested Domain dataclass from the SQLAlchemy model."""
        
        product = ProductDetails(
            sku=orm_sale.product.sku,
            name=orm_sale.product.name,
            category=orm_sale.product.category
        )
        
        customer = CustomerDetails(
            identifier=orm_sale.customer.customer_identifier,
            region=orm_sale.customer.region,
            industry=orm_sale.customer.industry
        )
        
        return FactSale(
            source_file_id=orm_sale.source_file_id,
            transaction_id=orm_sale.transaction_id,
            sale_date=orm_sale.sale_date.full_date,
            quantity_sold=orm_sale.quantity_sold,
            revenue_amount=orm_sale.revenue_amount,
            sale_timestamp=orm_sale.sale_timestamp,
            product_id=orm_sale.product_id,
            customer_id=orm_sale.customer_id,
            date_id=orm_sale.date_id
        )

# Abstract Base class methods

    def check_exists(self, identifier) -> bool:
        """Checks if a FactSale exists by transaction ID (identifier) and product SKU"""
        if not isinstance(identifier, tuple):
            raise RequiresAdditionalArgsError(
                f"SalesRepository requires a composite identifier (tuple), but got {type(identifier).__name__}."
            )

        transaction_id, sku = identifier
        if identifier in self.seen_sales_identifiers: 
            return True
        
        base_query = (
            select(FactSaleORM.id)
            .join(FactSaleORM.product)
            .options(contains_eager(FactSaleORM.product))
            .where(
                FactSaleORM.transaction_id == transaction_id,
                DimProductORM.sku == sku
            )
        )

        exists_stmt = select(base_query.exists())
        
        return True if self.session.execute(exists_stmt).scalar() else False        


    def add(self, sale: FactSale, product: ProductDetails, customer: CustomerDetails) -> None:
        """
        Takes a pure Domain object, translates it to ORM, checks idempotency, 
        and adds it to the session.
        """
        identifier = (sale.transaction_id, product.sku)
        if self.check_exists(identifier): 
            return     
        
        
        orm_sale = self._to_orm(sale, product, customer)
        
        # Enforce idempotency 
        stmt = select(DimProductORM).where(DimProductORM.id == orm_sale.product_id)                                           
        orm_product = self.session.execute(stmt).scalar_one_or_none()       
        if orm_product: 
            identifier = (orm_sale.transaction_id, orm_product.sku)
            if not self.check_exists(identifier):
                self.session.add(orm_sale)
                tuple = (sale.transaction_id, product.sku)
                self.seen_sales_identifiers.add(tuple)

            


    def get(self, identifier) -> FactSale | None: 
        """Gets a FactSale from transaction ID (identifier) and product ID (identifier2)"""
        if not isinstance(identifier, tuple):
            raise RequiresAdditionalArgsError(
                f"SalesRepository requires a composite identifier (tuple), but got {type(identifier).__name__}."
            )
        transaction_id, sku = identifier
        query = (
        select(FactSaleORM)
        .join(FactSaleORM.product)
        .options(contains_eager(FactSaleORM.product))
        .where(FactSaleORM.transaction_id == transaction_id, DimProductORM.sku == sku)
        )
        
        result = self.session.execute(query).scalar_one_or_none()
        if result is not None: 
            entity = self._to_domain(result)
            return entity
        return None

    def delete(self, identifier):
        if not isinstance(identifier, tuple):
            raise RequiresAdditionalArgsError(
                f"SalesRepository requires a composite identifier (tuple), but got {type(identifier).__name__}."
            )
        transaction_id, sku = identifier
            
        query = (
            select(FactSaleORM).
            join(FactSaleORM.product).
            options(contains_eager(FactSaleORM.product))
            .where(FactSaleORM.transaction_id == transaction_id, DimProductORM.sku == sku)
        )
        orm_results = self.session.execute(query).scalars().all()
        
        if orm_results: 
            self.session.delete(o for o in orm_results)
            
            
    def delete_by_source_file(self, file_id: int):
         
         stmt = select(FactSaleORM).where(FactSaleORM.source_file_id == file_id)
         
         results = self.session.execute(stmt).scalars().all()
         if results: 
             self.session.delete(r for r in results)
             

    def get_by_source_file(self, file_id: int) -> list[FactSale] | None:
        stmt = select(FactSaleORM).where(FactSaleORM.source_file_id == file_id)
        orm_results = self.session.execute(stmt).scalars().all()
        if orm_results: 
            return [self._to_domain(orm) for orm in orm_results]
        
        return None
    
    