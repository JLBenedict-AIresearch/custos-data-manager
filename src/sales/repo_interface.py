# src.sales.repo_interface

import abc
from datetime import datetime

from src.sales.domain import CustomerDetails, FactSale, ProductDetails
from src.shared.interfaces.repository_interface import AbstractDomainRepository


class AbstractSalesRepository(AbstractDomainRepository):
    
    @abc.abstractmethod
    def get_or_create_product(self, product: ProductDetails) -> int:
        """Finds a product by SKU, or creates it if it doesn't exist. Returns the database ID."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_or_create_customer(self, customer: CustomerDetails) -> int:
        """Finds a customer by CRM identifier, or creates it. Returns the database ID."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_or_create_date(self, target_date: datetime) -> int:
        """Finds a date dimension by its Smart Key, or creates it. Returns the database ID."""
        raise NotImplementedError

# Other basic methods are inherited from the parent Abstract Domain Repository