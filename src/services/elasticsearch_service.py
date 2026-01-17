"""
Elasticsearch Service
Handles indexing and searching of expenses
"""

from typing import Optional, Dict, Any, List

from src.models.expense import Expense
from src.config.settings import settings
from src.utils.logger import setup_logger

logger = setup_logger()

# Check if Elasticsearch is available
try:
    from elasticsearch import Elasticsearch, NotFoundError
    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    ELASTICSEARCH_AVAILABLE = False
    logger.warning("Elasticsearch not available - search functionality will be limited")


class ElasticsearchService:
    """Service for Elasticsearch operations"""
    
    def __init__(self):
        """Initialize Elasticsearch connection"""
        if ELASTICSEARCH_AVAILABLE:
            self.es = Elasticsearch([settings.ELASTICSEARCH_URL])
            self.index_name = settings.ELASTICSEARCH_INDEX
        else:
            self.es = None
            logger.warning("Elasticsearch service initialized without connection")
    
    async def create_index(self):
        """
        Create Elasticsearch index with mapping
        """
        if not self.es:
            return
        
        try:
            # Check if index already exists
            if self.es.indices.exists(index=self.index_name):
                logger.info(f"Elasticsearch index '{self.index_name}' already exists")
                return
            
            # Define index mapping
            mapping = {
                "mappings": {
                    "properties": {
                        "expense_number": {"type": "keyword"},
                        "employee_id": {"type": "integer"},
                        "employee_name": {"type": "text"},
                        "category": {"type": "keyword"},
                        "amount": {"type": "float"},
                        "description": {"type": "text"},
                        "status": {"type": "keyword"},
                        "expense_date": {"type": "date"},
                        "created_at": {"type": "date"},
                        "vendor_name": {"type": "text"},
                        "ai_summary": {"type": "text"}
                    }
                }
            }
            
            # Create index
            self.es.indices.create(index=self.index_name, body=mapping)
            logger.info(f"Created Elasticsearch index: {self.index_name}")
            
        except Exception as e:
            logger.error(f"Error creating Elasticsearch index: {str(e)}")
    
    async def index_expense(self, expense: Expense):
        """
        Index an expense document in Elasticsearch
        
        Args:
            expense: Expense object to index
        """
        if not self.es:
            return
        
        try:
            # Prepare document
            doc = {
                "expense_number": expense.expense_number,
                "employee_id": expense.employee_id,
                "employee_name": expense.employee.full_name,
                "category": expense.category.value,
                "amount": expense.amount,
                "description": expense.description,
                "status": expense.status.value,
                "expense_date": expense.expense_date.isoformat(),
                "created_at": expense.created_at.isoformat(),
                "vendor_name": expense.vendor_name,
                "ai_summary": expense.ai_summary
            }
            
            # Index document
            self.es.index(index=self.index_name, id=expense.id, body=doc)
            logger.info(f"Indexed expense {expense.expense_number} in Elasticsearch")
            
        except Exception as e:
            logger.error(f"Error indexing expense: {str(e)}")
    
    async def update_expense(self, expense: Expense):
        """
        Update an existing expense document
        
        Args:
            expense: Expense object with updated data
        """
        if not self.es:
            return
        
        try:
            # Prepare update document
            doc = {
                "status": expense.status.value,
                "ai_summary": expense.ai_summary
            }
            
            # Update document
            self.es.update(
                index=self.index_name,
                id=expense.id,
                body={"doc": doc}
            )
            logger.info(f"Updated expense {expense.expense_number} in Elasticsearch")
            
        except Exception as e:
            logger.error(f"Error updating expense: {str(e)}")
    
    async def delete_expense(self, expense_id: int):
        """
        Delete an expense document from index
        
        Args:
            expense_id: ID of expense to delete
        """
        if not self.es:
            return
        
        try:
            self.es.delete(index=self.index_name, id=expense_id)
            logger.info(f"Deleted expense {expense_id} from Elasticsearch")
        except Exception as e:
            logger.error(f"Error deleting expense: {str(e)}")
    
    async def search_expenses(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        size: int = 50
    ) -> List[Dict]:
        """
        Search expenses with full-text search
        
        Args:
            query: Search query string
            filters: Optional filters (category, status, employee_id)
            size: Maximum number of results
            
        Returns:
            List of matching expense documents
        """
        if not self.es:
            return []
        
        try:
            # Build search query
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": [
                                        "description",
                                        "vendor_name",
                                        "ai_summary",
                                        "employee_name"
                                    ],
                                    "fuzziness": "AUTO"
                                }
                            }
                        ],
                        "filter": []
                    }
                },
                "size": size,
                "sort": [{"created_at": {"order": "desc"}}]
            }
            
            # Add filters if provided
            if filters:
                if filters.get("category"):
                    search_body["query"]["bool"]["filter"].append(
                        {"term": {"category": filters["category"]}}
                    )
                if filters.get("status"):
                    search_body["query"]["bool"]["filter"].append(
                        {"term": {"status": filters["status"]}}
                    )
                if filters.get("employee_id"):
                    search_body["query"]["bool"]["filter"].append(
                        {"term": {"employee_id": filters["employee_id"]}}
                    )
            
            # Execute search
            result = self.es.search(index=self.index_name, body=search_body)
            
            # Extract and return results
            return [hit["_source"] for hit in result["hits"]["hits"]]
            
        except Exception as e:
            logger.error(f"Error searching expenses: {str(e)}")
            return []


# Create singleton instance
elasticsearch_service = ElasticsearchService() if ELASTICSEARCH_AVAILABLE else None