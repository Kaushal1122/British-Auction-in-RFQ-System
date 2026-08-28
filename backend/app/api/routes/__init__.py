from fastapi import APIRouter
from .health import router as health_router
from .db_health import router as db_health_router
from .buyers import router as buyers_router
from .rfqs import router as rfqs_router
from .suppliers import router as suppliers_router
from .bids import router as bids_router
from .auctions import router as auctions_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(db_health_router, tags=["Database Health"])
api_router.include_router(buyers_router, prefix="/buyers", tags=["Buyers"])
api_router.include_router(rfqs_router, prefix="/rfqs", tags=["RFQs"])
api_router.include_router(suppliers_router, prefix="/suppliers", tags=["Suppliers"])
api_router.include_router(bids_router, prefix="/bids", tags=["Bids"])
api_router.include_router(auctions_router, prefix="/auctions", tags=["Auctions"])

__all__ = ["api_router"]

