# tests.conftest.fake_sales_repository


from datetime import datetime
from src.sales.domain import FactSale, ProductDetails, CustomerDetails
from src.sales.repo_interface import AbstractSalesRepository
from src.shared.errors import RequiresAdditionalArgsError

class FakeSalesRepository(AbstractSalesRepository):
    
    def __init__(self):
        self._sales: set[FactSale] = set()
        self._products: list[tuple] = []
        self._customers: list[tuple] = []
        self._dates: list[tuple[int, int]] = []
    
    def get_or_create_product(self, product: ProductDetails) -> int:
        """Finds a product dimension by SKU, mocks creating one if it does not exist. Returns the product id."""
        result = next((item[0] for item in self._products if item[1] == product.sku), None)
        
        if result is None: 
            new_id = len(self._products) + 1
            new_entry = (new_id, product.sku)
            self._products.append(new_entry)
            return new_id
        
        return result

    def get_or_create_customer(self, customer: CustomerDetails) -> int:
        """Finds a customer by CRM identifier, or mocks creating customer. Returns the customer id."""
        result = next((item[0] for item in self._customers if item[1] == customer.identifier), None)
        
        if result is None: 
            new_id = len(self._customers) + 1
            
            new_entry = (new_id, customer.identifier)
            self._customers.append(new_entry)
            return new_id
        
        return result

    def get_or_create_date(self, target_date: datetime) -> int:
        """Finds a date dimension by its Smart Key, or mocks creating it. Returns the date id."""
        smart_key_id = int(target_date.strftime("%Y%m%d"))  
        result = next((item[0] for item in self._dates if item[1] == smart_key_id), None)
        
        if result is None: 
            new_id = len(self._dates) + 1
            new_entry = (new_id, smart_key_id)
            
            self._dates.append(new_entry)
            return new_id

        return result

    def check_exists(self, identifier) -> bool:
        """Checks for transaction idempotency to prevent duplicate fact records."""
        if not isinstance(identifier, tuple):
            raise RequiresAdditionalArgsError(
                f"SalesRepository requires a composite identifier (tuple), but got {type(identifier).__name__}."
            )
        else: 
            transaction_id, sku = identifier
            product_id = next((item[0] for item in self._products if item[1] == sku), None)
            result = next((sale for sale in self._sales if sale.transaction_id == transaction_id and sale.product_id == product_id), None)
            return True if result else False



    def get(self, identifier) -> FactSale | None: 
        
        if isinstance(identifier, tuple): 
            transaction_id, sku = identifier
            product_id =  next((item[0] for item in self._products if item[1] == sku), None)
            result = next((sale for sale in self._sales if sale.transaction_id == transaction_id and sale.product_id == product_id), None)
            return result if result else None
        return None

    def delete(self, identifier):
        if isinstance(identifier, tuple): 
            transaction_id, sku = identifier
            product_id = next((item[0] for item in self._products if item[1] == sku), None)
            result = next((sale for sale in self._sales if sale.transaction_id == transaction_id and sale.product_id == product_id), None)
            if result: 
                self._sales.remove(result)
            
            
        to_delete = next(sale for sale in self._sales if sale.source_file_id == identifier)

    def add(self, sale: FactSale, product: ProductDetails, customer: CustomerDetails) -> None:
        """Mocks staging a fact sale to be added to the database."""
        new_product_id = self.get_or_create_product(product)
        new_customer_id = self.get_or_create_customer(customer)
        new_date_id = self.get_or_create_date(sale.sale_timestamp)
        identifier = (sale.transaction_id, product.sku)
        if not self.check_exists(identifier):
            new_sale = FactSale(
                source_file_id=sale.source_file_id,
                transaction_id=sale.transaction_id,
                sale_date=sale.sale_date,
                quantity_sold=sale.quantity_sold,
                revenue_amount=sale.revenue_amount,
                sale_timestamp=sale.sale_timestamp,            
                product_id=sale.product_id if sale.product_id else new_product_id, 
                customer_id=sale.customer_id if sale.customer_id else new_customer_id,
                date_id=sale.date_id if sale.date_id else new_date_id
            )
            self._sales.add(new_sale)
    
    def get_by_source_file(self, file_id: int):
        return [sale for sale in self._sales if sale.source_file_id == file_id]
        
    def delete_by_source_file(self, file_id: int):
        self._sales = {sale for sale in self._sales if sale.source_file_id != file_id}
            