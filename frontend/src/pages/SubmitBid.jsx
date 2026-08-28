import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  Gavel,
  FileText,
  DollarSign,
  Layers,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Send,
  RotateCcw,
  Package,
  Building,
  TrendingDown,
  Truck,
  Clock,
} from 'lucide-react';

import SupplierSection from '../components/SupplierSection';
import { getRFQs, getRFQById, createBid } from '../services/api';

export const SubmitBid = () => {
  const [searchParams] = useSearchParams();
  const initialRfqId = searchParams.get('rfq_id') || '';

  // RFQ List & Selected RFQ State
  const [rfqList, setRfqList] = useState([]);
  const [loadingRfqs, setLoadingRfqs] = useState(true);
  const [selectedRfqId, setSelectedRfqId] = useState(initialRfqId);
  const [selectedRfq, setSelectedRfq] = useState(null);
  const [loadingRfqDetail, setLoadingRfqDetail] = useState(false);

  // Form State
  const [selectedSupplier, setSelectedSupplier] = useState(null);
  const [selectedItemId, setSelectedItemId] = useState('');
  const [amount, setAmount] = useState('');

  // Quote Breakdown Details (PDF Specification)
  const [carrierName, setCarrierName] = useState('');
  const [freightCharges, setFreightCharges] = useState('');
  const [originCharges, setOriginCharges] = useState('');
  const [destinationCharges, setDestinationCharges] = useState('');
  const [transitTime, setTransitTime] = useState('');
  const [validityOfQuote, setValidityOfQuote] = useState('');

  // Validation & Submission State
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiError, setApiError] = useState('');
  const [submittedBidResult, setSubmittedBidResult] = useState(null);

  // Fetch available RFQs on mount
  useEffect(() => {
    let isMounted = true;
    setLoadingRfqs(true);
    getRFQs({ limit: 100 })
      .then((data) => {
        if (isMounted) {
          setRfqList(data);
          setLoadingRfqs(false);
          // If initialRfqId is set, find or load it
          if (initialRfqId) {
            loadRfqDetails(initialRfqId);
          }
        }
      })
      .catch(() => {
        if (isMounted) {
          setLoadingRfqs(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, [initialRfqId]);

  // Load detailed RFQ info when selected
  const loadRfqDetails = async (rfqId) => {
    if (!rfqId) {
      setSelectedRfq(null);
      setSelectedItemId('');
      return;
    }
    setLoadingRfqDetail(true);
    try {
      const data = await getRFQById(rfqId);
      setSelectedRfq(data);
      if (data.items && data.items.length > 0) {
        setSelectedItemId(data.items[0].id);
      } else {
        setSelectedItemId('');
      }
    } catch {
      setSelectedRfq(null);
    } finally {
      setLoadingRfqDetail(false);
    }
  };

  const handleRfqChange = (e) => {
    const id = e.target.value;
    setSelectedRfqId(id);
    if (errors.rfq) {
      setErrors((prev) => ({ ...prev, rfq: '' }));
    }
    loadRfqDetails(id);
  };

  const handleSupplierSelected = (supplier) => {
    setSelectedSupplier(supplier);
    if (errors.supplier) {
      setErrors((prev) => ({ ...prev, supplier: '' }));
    }
  };

  const handleItemSelect = (itemId) => {
    setSelectedItemId(itemId);
    if (errors.item) {
      setErrors((prev) => ({ ...prev, item: '' }));
    }
  };

  const handleAmountChange = (e) => {
    setAmount(e.target.value);
    if (errors.amount) {
      setErrors((prev) => ({ ...prev, amount: '' }));
    }
  };

  // Validation
  const validateForm = () => {
    const newErrors = {};

    // 1. RFQ Validation
    if (!selectedRfqId || !selectedRfq) {
      newErrors.rfq = 'RFQ is required.';
    }

    // 2. Supplier Validation
    if (!selectedSupplier || !selectedSupplier.id) {
      newErrors.supplier = 'Supplier is required.';
    }

    // 3. RFQ Item Validation (if RFQ has items)
    if (selectedRfq && selectedRfq.items && selectedRfq.items.length > 0) {
      if (!selectedItemId) {
        newErrors.item = 'RFQ item is required.';
      }
    }

    // 4. Bid Amount Validation
    if (amount === '' || amount === null || amount === undefined) {
      newErrors.amount = 'Bid amount is required.';
    } else {
      const numVal = parseFloat(amount);
      if (isNaN(numVal) || numVal < 0) {
        newErrors.amount = 'Bid amount must be greater than or equal to 0.';
      }
    }

    // 5. Quote Breakdown Validation (if filled, must be non-negative)
    if (freightCharges !== '' && freightCharges !== null && freightCharges !== undefined) {
      const val = parseFloat(freightCharges);
      if (isNaN(val) || val < 0) {
        newErrors.freightCharges = 'Freight charges must be greater than or equal to 0.';
      }
    }
    if (originCharges !== '' && originCharges !== null && originCharges !== undefined) {
      const val = parseFloat(originCharges);
      if (isNaN(val) || val < 0) {
        newErrors.originCharges = 'Origin charges must be greater than or equal to 0.';
      }
    }
    if (destinationCharges !== '' && destinationCharges !== null && destinationCharges !== undefined) {
      const val = parseFloat(destinationCharges);
      if (isNaN(val) || val < 0) {
        newErrors.destinationCharges = 'Destination charges must be greater than or equal to 0.';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Submission handler
  const handleSubmit = async (e) => {
    e.preventDefault();
    setApiError('');

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        rfq_id: selectedRfq.id,
        supplier_id: selectedSupplier.id,
        amount: parseFloat(amount),
        rfq_item_id: selectedItemId || undefined,
        carrier_name: carrierName.trim() || undefined,
        freight_charges: freightCharges !== '' ? parseFloat(freightCharges) : undefined,
        origin_charges: originCharges !== '' ? parseFloat(originCharges) : undefined,
        destination_charges: destinationCharges !== '' ? parseFloat(destinationCharges) : undefined,
        transit_time: transitTime.trim() || undefined,
        validity_of_quote: validityOfQuote.trim() || undefined,
      };

      const result = await createBid(payload);
      setSubmittedBidResult(result);
    } catch (err) {
      if (err.response?.status === 404) {
        setApiError('RFQ or Supplier not found. Please verify your selection.');
      } else if (err.response?.status === 400 && err.response?.data?.detail) {
        setApiError(err.response.data.detail);
      } else if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (Array.isArray(detail)) {
          setApiError(detail.map((d) => d.msg || d).join(', '));
        } else {
          setApiError(String(detail));
        }
      } else {
        setApiError('Unable to submit bid. Please check the form and try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Reset form handler
  const handleResetForm = () => {
    setSelectedRfqId('');
    setSelectedRfq(null);
    setSelectedSupplier(null);
    setSelectedItemId('');
    setAmount('');
    setCarrierName('');
    setFreightCharges('');
    setOriginCharges('');
    setDestinationCharges('');
    setTransitTime('');
    setValidityOfQuote('');
    setErrors({});
    setApiError('');
    setSubmittedBidResult(null);
  };

  return (
    <div className="page-container" id="page-submit-bid">
      <div className="page-header">
        <h1 className="page-title">Submit Supplier Bid</h1>
        <p className="page-subtitle">
          Place a quotation bid against an active Request for Quotation (RFQ) line specification.
        </p>
      </div>

      {/* Success State */}
      {submittedBidResult ? (
        <div className="success-card" id="bid-success-card">
          <div className="success-icon-large">
            <CheckCircle2 size={36} />
          </div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)' }}>
            Bid submitted successfully.
          </h2>
          <p style={{ color: 'var(--text-secondary)', maxWidth: '540px' }}>
            Your supplier quotation has been verified and registered on the British Auction RFQ backend.
          </p>

          <div className="success-details" id="bid-success-details">
            <div className="success-row">
              <span>Bid ID:</span>
              <strong id="created-bid-id" style={{ fontFamily: 'monospace', color: '#38bdf8' }}>
                {submittedBidResult.id}
              </strong>
            </div>
            <div className="success-row">
              <span>RFQ:</span>
              <strong id="created-bid-rfq-title">
                {selectedRfq?.title || submittedBidResult.rfq_id}
              </strong>
            </div>
            <div className="success-row">
              <span>Supplier:</span>
              <strong id="created-bid-supplier">
                {selectedSupplier?.name || submittedBidResult.supplier_id}
              </strong>
            </div>
            <div className="success-row">
              <span>Bid Amount:</span>
              <strong id="created-bid-amount" style={{ color: '#10b981', fontSize: '1.1rem' }}>
                {submittedBidResult.amount} {selectedRfq?.currency || 'USD'}
              </strong>
            </div>
            <div className="success-row">
              <span>Submitted At:</span>
              <strong id="created-bid-timestamp">
                {new Date(submittedBidResult.submitted_at).toLocaleString()}
              </strong>
            </div>
            <div className="success-row">
              <span>Status:</span>
              <span className="badge badge-success">Valid</span>
            </div>
            {submittedBidResult.carrier_name && (
              <div className="success-row">
                <span>Carrier Name:</span>
                <strong id="created-bid-carrier">{submittedBidResult.carrier_name}</strong>
              </div>
            )}
            {submittedBidResult.freight_charges !== null && submittedBidResult.freight_charges !== undefined && (
              <div className="success-row">
                <span>Freight Charges:</span>
                <strong id="created-bid-freight">
                  {submittedBidResult.freight_charges} {selectedRfq?.currency || 'USD'}
                </strong>
              </div>
            )}
            {submittedBidResult.origin_charges !== null && submittedBidResult.origin_charges !== undefined && (
              <div className="success-row">
                <span>Origin Charges:</span>
                <strong id="created-bid-origin">
                  {submittedBidResult.origin_charges} {selectedRfq?.currency || 'USD'}
                </strong>
              </div>
            )}
            {submittedBidResult.destination_charges !== null && submittedBidResult.destination_charges !== undefined && (
              <div className="success-row">
                <span>Destination Charges:</span>
                <strong id="created-bid-destination">
                  {submittedBidResult.destination_charges} {selectedRfq?.currency || 'USD'}
                </strong>
              </div>
            )}
            {submittedBidResult.transit_time && (
              <div className="success-row">
                <span>Transit Time:</span>
                <strong id="created-bid-transit">{submittedBidResult.transit_time}</strong>
              </div>
            )}
            {submittedBidResult.validity_of_quote && (
              <div className="success-row">
                <span>Quote Validity:</span>
                <strong id="created-bid-validity">{submittedBidResult.validity_of_quote}</strong>
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem', flexWrap: 'wrap', justifyContent: 'center' }}>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleResetForm}
              id="btn-submit-another-bid"
            >
              <RotateCcw size={16} />
              <span>Submit Another Bid</span>
            </button>

            <Link
              to={`/rfqs/${submittedBidResult.rfq_id || selectedRfq?.id}/ranking`}
              className="btn btn-secondary"
              id="btn-view-bid-rankings"
            >
              <TrendingDown size={16} />
              <span>View Bid Rankings</span>
            </Link>
          </div>
        </div>

      ) : (
        /* Bid Submission Form */
        <form onSubmit={handleSubmit} noValidate id="form-submit-bid">
          {apiError && (
            <div className="alert alert-error" role="alert" id="bid-api-error">
              <AlertCircle size={18} className="alert-icon" />
              <div className="alert-content">
                <div className="alert-title">Bid Submission Failed</div>
                <div>{apiError}</div>
              </div>
            </div>
          )}

          {/* Section 1: RFQ Selection */}
          <div className="form-section" id="section-rfq-select">
            <div className="section-header">
              <div className="section-title">
                <FileText size={20} color="#6366f1" />
                <span>1. Select RFQ</span>
              </div>
              <span className="section-badge">Required</span>
            </div>

            <div className="form-group">
              <label htmlFor="select-rfq" className="form-label">
                Target RFQ <span className="required">*</span>
              </label>
              <select
                id="select-rfq"
                className={`form-control ${errors.rfq ? 'error' : ''}`}
                value={selectedRfqId}
                onChange={handleRfqChange}
                disabled={isSubmitting || loadingRfqs}
              >
                <option value="">-- Choose an RFQ to bid on --</option>
                {rfqList.map((rfq) => (
                  <option key={rfq.id} value={rfq.id}>
                    {rfq.title} — Baseline: {rfq.baseline_price} {rfq.currency} ({rfq.status})
                  </option>
                ))}
              </select>

              {loadingRfqs && (
                <span className="helper-text">Loading active RFQs from backend...</span>
              )}

              {errors.rfq && (
                <span className="error-text" id="rfq-required-error">
                  <AlertCircle size={13} />
                  {errors.rfq}
                </span>
              )}
            </div>

            {/* Selected RFQ Preview */}
            {loadingRfqDetail && (
              <div className="helper-text" style={{ marginTop: '0.5rem' }}>
                Loading RFQ line items and details...
              </div>
            )}

            {selectedRfq && !loadingRfqDetail && (
              <div className="buyer-status-box" id="selected-rfq-preview" style={{ marginTop: '1rem' }}>
                <div className="buyer-empty-state">
                  <div className="buyer-icon-wrapper active">
                    <FileText size={22} />
                  </div>
                  <div className="buyer-info-text">
                    <span className="buyer-name" id="preview-rfq-title">{selectedRfq.title}</span>
                    <span className="buyer-company" id="preview-rfq-baseline">
                      <DollarSign size={13} style={{ display: 'inline', verticalAlign: 'middle' }} />
                      Baseline Price: {selectedRfq.baseline_price} {selectedRfq.currency}
                    </span>
                    {selectedRfq.description && (
                      <span className="helper-text" id="preview-rfq-desc">
                        {selectedRfq.description}
                      </span>
                    )}
                  </div>
                </div>
                <span className="badge badge-info">{selectedRfq.status}</span>
              </div>
            )}
          </div>

          {/* Section 2: Supplier Section */}
          <SupplierSection
            selectedSupplier={selectedSupplier}
            onSupplierSelected={handleSupplierSelected}
            error={errors.supplier}
          />

          {/* Section 3: RFQ Items Selection */}
          {selectedRfq && selectedRfq.items && selectedRfq.items.length > 0 && (
            <div className="form-section" id="section-rfq-items-select">
              <div className="section-header">
                <div className="section-title">
                  <Layers size={20} color="#6366f1" />
                  <span>3. RFQ Item Selection</span>
                </div>
                <span className="section-badge">
                  {selectedRfq.items.length} {selectedRfq.items.length === 1 ? 'Item' : 'Items'}
                </span>
              </div>

              {errors.item && (
                <div className="alert alert-error" style={{ marginBottom: '1rem' }}>
                  <AlertCircle size={16} />
                  <span>{errors.item}</span>
                </div>
              )}

              <div className="card-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
                {selectedRfq.items.map((item, idx) => {
                  const isSelected = selectedItemId === item.id;
                  return (
                    <div
                      key={item.id}
                      className={`card ${isSelected ? 'selected-item-card' : ''}`}
                      onClick={() => handleItemSelect(item.id)}
                      id={`rfq-item-select-${idx}`}
                      style={{
                        cursor: 'pointer',
                        border: isSelected ? '2px solid #6366f1' : '1px solid var(--border-color)',
                        backgroundColor: isSelected ? 'rgba(99, 102, 241, 0.08)' : 'var(--card-bg)',
                        transition: 'all 0.15s ease-in-out',
                      }}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          handleItemSelect(item.id);
                        }
                      }}
                    >
                      <div className="card-header" style={{ marginBottom: '0.5rem' }}>
                        <div className="card-title" style={{ fontSize: '1rem' }}>
                          <Package size={18} color={isSelected ? '#6366f1' : '#94a3b8'} />
                          <span style={{ fontWeight: 600 }}>{item.name}</span>
                        </div>
                        <input
                          type="radio"
                          name="rfq_item_choice"
                          checked={isSelected}
                          onChange={() => handleItemSelect(item.id)}
                          aria-label={`Select ${item.name}`}
                        />
                      </div>
                      <p className="card-desc" style={{ marginBottom: '0.5rem', fontSize: '0.85rem' }}>
                        {item.description || 'No specific description'}
                      </p>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        <strong>Quantity:</strong> {item.quantity} {item.unit}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Section 4: Bid Amount */}
          <div className="form-section" id="section-bid-amount">
            <div className="section-header">
              <div className="section-title">
                <DollarSign size={20} color="#6366f1" />
                <span>4. Bid Information</span>
              </div>
              <span className="section-badge">Required</span>
            </div>

            <div className="form-group">
              <label htmlFor="bid-amount-input" className="form-label">
                Bid Amount ({selectedRfq?.currency || 'USD'}) <span className="required">*</span>
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  id="bid-amount-input"
                  type="number"
                  step="any"
                  min="0"
                  className={`form-control ${errors.amount ? 'error' : ''}`}
                  placeholder="e.g. 45000.00"
                  value={amount}
                  onChange={handleAmountChange}
                  disabled={isSubmitting}
                  style={{ paddingRight: '4rem' }}
                />
                <span
                  style={{
                    position: 'absolute',
                    right: '12px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--text-secondary)',
                    fontWeight: 600,
                    fontSize: '0.85rem',
                    pointerEvents: 'none',
                  }}
                >
                  {selectedRfq?.currency || 'USD'}
                </span>
              </div>

              {errors.amount && (
                <span className="error-text" id="bid-amount-error">
                  <AlertCircle size={13} />
                  {errors.amount}
                </span>
              )}
            </div>
          </div>

          {/* Section 5: Quote Breakdown & Shipping Details (PDF Specification) */}
          <div className="form-section" id="section-quote-details">
            <div className="section-header">
              <div className="section-title">
                <Truck size={20} color="#38bdf8" />
                <span>5. Quotation Breakdown & Logistics (Optional)</span>
              </div>
              <span className="section-badge" style={{ backgroundColor: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8' }}>
                Quote Details
              </span>
            </div>
            <p className="card-desc" style={{ marginBottom: '1.25rem' }}>
              Specify freight carriers, line cost items, transit estimates, and formal proposal validity as required by the procurement guidelines.
            </p>

            <div className="form-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
              <div className="form-group">
                <label htmlFor="carrier-name-input" className="form-label">
                  Carrier Name
                </label>
                <input
                  id="carrier-name-input"
                  type="text"
                  className="form-control"
                  placeholder="e.g. Maersk / DHL Logistics"
                  value={carrierName}
                  onChange={(e) => setCarrierName(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>

              <div className="form-group">
                <label htmlFor="freight-charges-input" className="form-label">
                  Freight Charges ({selectedRfq?.currency || 'USD'})
                </label>
                <input
                  id="freight-charges-input"
                  type="number"
                  step="any"
                  min="0"
                  className={`form-control ${errors.freightCharges ? 'error' : ''}`}
                  placeholder="e.g. 1200.00"
                  value={freightCharges}
                  onChange={(e) => {
                    setFreightCharges(e.target.value);
                    if (errors.freightCharges) setErrors((prev) => ({ ...prev, freightCharges: '' }));
                  }}
                  disabled={isSubmitting}
                />
                {errors.freightCharges && (
                  <span className="error-text">
                    <AlertCircle size={13} />
                    {errors.freightCharges}
                  </span>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="origin-charges-input" className="form-label">
                  Origin Charges ({selectedRfq?.currency || 'USD'})
                </label>
                <input
                  id="origin-charges-input"
                  type="number"
                  step="any"
                  min="0"
                  className={`form-control ${errors.originCharges ? 'error' : ''}`}
                  placeholder="e.g. 350.00"
                  value={originCharges}
                  onChange={(e) => {
                    setOriginCharges(e.target.value);
                    if (errors.originCharges) setErrors((prev) => ({ ...prev, originCharges: '' }));
                  }}
                  disabled={isSubmitting}
                />
                {errors.originCharges && (
                  <span className="error-text">
                    <AlertCircle size={13} />
                    {errors.originCharges}
                  </span>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="destination-charges-input" className="form-label">
                  Destination Charges ({selectedRfq?.currency || 'USD'})
                </label>
                <input
                  id="destination-charges-input"
                  type="number"
                  step="any"
                  min="0"
                  className={`form-control ${errors.destinationCharges ? 'error' : ''}`}
                  placeholder="e.g. 450.00"
                  value={destinationCharges}
                  onChange={(e) => {
                    setDestinationCharges(e.target.value);
                    if (errors.destinationCharges) setErrors((prev) => ({ ...prev, destinationCharges: '' }));
                  }}
                  disabled={isSubmitting}
                />
                {errors.destinationCharges && (
                  <span className="error-text">
                    <AlertCircle size={13} />
                    {errors.destinationCharges}
                  </span>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="transit-time-input" className="form-label">
                  Transit Time
                </label>
                <input
                  id="transit-time-input"
                  type="text"
                  className="form-control"
                  placeholder="e.g. 5 days / 2 weeks"
                  value={transitTime}
                  onChange={(e) => setTransitTime(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>

              <div className="form-group">
                <label htmlFor="quote-validity-input" className="form-label">
                  Validity of Quote
                </label>
                <input
                  id="quote-validity-input"
                  type="text"
                  className="form-control"
                  placeholder="e.g. 30 days / Until Sept 30"
                  value={validityOfQuote}
                  onChange={(e) => setValidityOfQuote(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>
            </div>
          </div>

          {/* Form Actions */}
          <div className="form-actions">
            <button
              type="submit"
              className="btn btn-primary btn-submit"
              disabled={isSubmitting}
              id="btn-submit-bid"
            >
              {isSubmitting ? (
                <>
                  <RefreshCw size={18} className="spinner" />
                  <span>Submitting Bid...</span>
                </>
              ) : (
                <>
                  <Send size={18} />
                  <span>Submit Bid</span>
                </>
              )}
            </button>
          </div>
        </form>
      )}
    </div>
  );
};

export default SubmitBid;
