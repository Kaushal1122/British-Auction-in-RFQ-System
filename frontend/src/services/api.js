import axios from 'axios';

// Resolve base URL from environment or default to local backend
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Request interceptor for future authentication or tracing
apiClient.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for centralized error formatting
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Keep internal log for debugging while letting caller receive structured error
    return Promise.reject(error);
  }
);

/**
 * Health check API service
 * Calls GET /health to verify backend connectivity
 */
export const checkHealth = async () => {
  const response = await apiClient.get('/health');
  return response.data;
};

/**
 * Create a new buyer
 * Calls POST /api/v1/buyers
 * @param {Object} buyerData { name: string, email: string, company_name?: string }
 * @returns {Promise<Object>} BuyerResponse
 */
export const createBuyer = async (buyerData) => {
  const response = await apiClient.post('/api/v1/buyers', buyerData);
  return response.data;
};

/**
 * Retrieve a buyer by UUID
 * Calls GET /api/v1/buyers/{buyer_id}
 * @param {string} buyerId UUID of the buyer
 * @returns {Promise<Object>} BuyerResponse
 */
export const getBuyerById = async (buyerId) => {
  const response = await apiClient.get(`/api/v1/buyers/${buyerId}`);
  return response.data;
};

/**
 * List all buyers
 * Calls GET /api/v1/buyers
 * @param {Object} [params] { skip?: number, limit?: number }
 * @returns {Promise<Array>} List of BuyerResponse
 */
export const getBuyers = async (params = {}) => {
  const response = await apiClient.get('/api/v1/buyers', { params });
  return response.data;
};

export const listBuyers = getBuyers;


/**
 * Create an RFQ with line items
 * Calls POST /api/v1/rfqs
 * @param {Object} rfqData { buyer_id: string, title: string, description?: string, category?: string, currency: string, baseline_price: number, items: Array }
 * @returns {Promise<Object>} RFQDetailResponse
 */
export const createRFQ = async (rfqData) => {
  const response = await apiClient.post('/api/v1/rfqs', rfqData);
  return response.data;
};

/**
 * Retrieve an RFQ by UUID with its line items
 * Calls GET /api/v1/rfqs/{rfq_id}
 * @param {string} rfqId UUID of the RFQ
 * @returns {Promise<Object>} RFQDetailResponse
 */
export const getRFQById = async (rfqId) => {
  const response = await apiClient.get(`/api/v1/rfqs/${rfqId}`);
  return response.data;
};

/**
 * List all RFQs with summary details
 * Calls GET /api/v1/rfqs
 * @param {Object} [params] { skip?: number, limit?: number }
 * @returns {Promise<Array>} List of RFQListItemResponse
 */
export const getRFQs = async (params = {}) => {
  const response = await apiClient.get('/api/v1/rfqs', { params });
  return response.data;
};

/**
 * Create a new supplier profile
 * Calls POST /api/v1/suppliers
 * @param {Object} supplierData { name: string, email: string, company_name?: string }
 * @returns {Promise<Object>} SupplierResponse
 */
export const createSupplier = async (supplierData) => {
  const response = await apiClient.post('/api/v1/suppliers', supplierData);
  return response.data;
};

/**
 * Retrieve a supplier by UUID
 * Calls GET /api/v1/suppliers/{supplier_id}
 * @param {string} supplierId UUID of the supplier
 * @returns {Promise<Object>} SupplierResponse
 */
export const getSupplierById = async (supplierId) => {
  const response = await apiClient.get(`/api/v1/suppliers/${supplierId}`);
  return response.data;
};

/**
 * List all suppliers
 * Calls GET /api/v1/suppliers
 * @param {Object} [params] { skip?: number, limit?: number }
 * @returns {Promise<Array>} List of SupplierResponse
 */
export const listSuppliers = async (params = {}) => {
  const response = await apiClient.get('/api/v1/suppliers', { params });
  return response.data;
};

/**
 * Submit a supplier bid against an RFQ
 * Calls POST /api/v1/bids
 * @param {Object} bidData { rfq_id: string, supplier_id: string, amount: number, rfq_item_id?: string }
 * @returns {Promise<Object>} BidResponse
 */
export const createBid = async (bidData) => {
  const response = await apiClient.post('/api/v1/bids', bidData);
  return response.data;
};

/**
 * Retrieve a bid by UUID
 * Calls GET /api/v1/bids/{bid_id}
 * @param {string} bidId UUID of the bid
 * @returns {Promise<Object>} BidResponse
 */
export const getBidById = async (bidId) => {
  const response = await apiClient.get(`/api/v1/bids/${bidId}`);
  return response.data;
};

/**
 * Retrieve bid rankings for an RFQ
 * Calls GET /api/v1/rfqs/{rfq_id}/ranking
 * @param {string} rfqId UUID of the RFQ
 * @returns {Promise<Object>} RFQRankingResponse { rfq_id, rfq_title, currency, baseline_price, total_bids, rankings: Array }
 */
export const getRFQRanking = async (rfqId) => {
  const response = await apiClient.get(`/api/v1/rfqs/${rfqId}/ranking`);
  return response.data;
};

/**
 * List all British Auctions with current lowest bids, timers, and status
 * Calls GET /api/v1/auctions
 * @param {Object} [params] { skip?: number, limit?: number }
 * @returns {Promise<Array>} List of AuctionListItemResponse
 */
export const getAuctions = async (params = {}) => {
  const response = await apiClient.get('/api/v1/auctions', { params });
  return response.data;
};

export const listAuctions = getAuctions;

/**
 * Retrieve full Auction details by Auction UUID or RFQ UUID
 * Calls GET /api/v1/auctions/{id}
 * @param {string} identifier UUID of Auction or RFQ
 * @returns {Promise<Object>} AuctionDetailFullResponse
 */
export const getAuctionById = async (identifier) => {
  const response = await apiClient.get(`/api/v1/auctions/${identifier}`);
  return response.data;
};

/**
 * Retrieve activity logs for an RFQ
 * Calls GET /api/v1/rfqs/{rfq_id}/activity
 * @param {string} rfqId UUID of the RFQ
 * @returns {Promise<Array>} List of ActivityLogResponse
 */
export const getRfqActivityLogs = async (rfqId) => {
  const response = await apiClient.get(`/api/v1/rfqs/${rfqId}/activity`);
  return response.data;
};

/**
 * Retrieve activity logs for an Auction
 * Calls GET /api/v1/auctions/{auction_id}/activity
 * @param {string} auctionId UUID of the Auction
 * @returns {Promise<Array>} List of ActivityLogResponse
 */
export const getAuctionActivityLogs = async (auctionId) => {
  const response = await apiClient.get(`/api/v1/auctions/${auctionId}/activity`);
  return response.data;
};

export default apiClient;



