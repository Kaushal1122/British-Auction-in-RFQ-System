import React, { useState } from 'react';
import {
  FileText,
  DollarSign,
  Layers,
  Plus,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Send,
  RotateCcw,
  Clock,
  Zap,
  Calendar,
} from 'lucide-react';
import BuyerSection from '../components/BuyerSection';
import RFQItemRow from '../components/RFQItemRow';
import { createRFQ } from '../services/api';

const CURRENCY_OPTIONS = ['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY'];

const EXTENSION_TRIGGER_OPTIONS = [
  { value: 'BID_RECEIVED', label: 'Bid Received in Last X Minutes' },
  { value: 'ANY_RANK_CHANGE', label: 'Any Supplier Rank Change in Last X Minutes' },
  { value: 'L1_RANK_CHANGE', label: 'Lowest Bidder (L1) Rank Change in Last X Minutes' },
];

let itemCounter = 1;
const createEmptyItem = () => ({
  id: ++itemCounter,
  name: '',
  description: '',
  quantity: '',
  unit: 'units',
});

export const CreateRfq = () => {
  // Form State - RFQ Details
  const [selectedBuyer, setSelectedBuyer] = useState(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [baselinePrice, setBaselinePrice] = useState('');

  // Form State - Auction Schedule
  const [bidStartTime, setBidStartTime] = useState('');
  const [bidCloseTime, setBidCloseTime] = useState('');
  const [forcedBidCloseTime, setForcedBidCloseTime] = useState('');
  const [pickupServiceDate, setPickupServiceDate] = useState('');

  // Form State - British Auction Configuration
  const [triggerWindowMinutes, setTriggerWindowMinutes] = useState(10);
  const [extensionDurationMinutes, setExtensionDurationMinutes] = useState(5);
  const [extensionTrigger, setExtensionTrigger] = useState('BID_RECEIVED');

  // Form State - Items
  const [items, setItems] = useState([createEmptyItem()]);

  // Validation & Submission State
  const [errors, setErrors] = useState({});
  const [itemErrors, setItemErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiError, setApiError] = useState('');
  const [createdRfqResult, setCreatedRfqResult] = useState(null);

  // Buyer selection handler
  const handleBuyerSelected = (buyer) => {
    setSelectedBuyer(buyer);
    if (errors.buyer) {
      setErrors((prev) => ({ ...prev, buyer: '' }));
    }
  };

  // RFQ Field changes
  const handleTitleChange = (e) => {
    setTitle(e.target.value);
    if (errors.title) {
      setErrors((prev) => ({ ...prev, title: '' }));
    }
  };

  const handleBaselinePriceChange = (e) => {
    setBaselinePrice(e.target.value);
    if (errors.baselinePrice) {
      setErrors((prev) => ({ ...prev, baselinePrice: '' }));
    }
  };

  // Auction Schedule changes with dynamic validation
  const handleBidStartTimeChange = (e) => {
    const val = e.target.value;
    setBidStartTime(val);
    setErrors((prev) => {
      const next = { ...prev };
      delete next.bidStartTime;

      const startMs = val ? new Date(val).getTime() : NaN;
      const closeMs = bidCloseTime ? new Date(bidCloseTime).getTime() : NaN;
      const forcedMs = forcedBidCloseTime ? new Date(forcedBidCloseTime).getTime() : NaN;

      if (!isNaN(startMs) && !isNaN(closeMs)) {
        if (closeMs <= startMs) {
          next.bidCloseTime = 'Bid close time must be later than bid start time.';
        } else {
          delete next.bidCloseTime;
          if (!isNaN(forcedMs) && forcedMs <= closeMs) {
            next.forcedBidCloseTime = 'Forced close time must be later than bid close time.';
          } else if (!isNaN(forcedMs)) {
            delete next.forcedBidCloseTime;
          }
        }
      }

      if (!val && prev.bidStartTime) {
        next.bidStartTime = 'Bid start date & time is required.';
      }
      return next;
    });
  };

  const handleBidCloseTimeChange = (e) => {
    const val = e.target.value;
    setBidCloseTime(val);
    setErrors((prev) => {
      const next = { ...prev };
      delete next.bidCloseTime;

      const startMs = bidStartTime ? new Date(bidStartTime).getTime() : NaN;
      const closeMs = val ? new Date(val).getTime() : NaN;
      const forcedMs = forcedBidCloseTime ? new Date(forcedBidCloseTime).getTime() : NaN;

      if (!isNaN(startMs) && !isNaN(closeMs)) {
        if (closeMs <= startMs) {
          next.bidCloseTime = 'Bid close time must be later than bid start time.';
        }
      }

      if (!isNaN(closeMs) && !isNaN(forcedMs)) {
        if (forcedMs <= closeMs) {
          next.forcedBidCloseTime = 'Forced close time must be later than bid close time.';
        } else {
          delete next.forcedBidCloseTime;
        }
      }

      if (!val && prev.bidCloseTime) {
        next.bidCloseTime = 'Bid close date & time is required.';
      }
      return next;
    });
  };

  const handleForcedBidCloseTimeChange = (e) => {
    const val = e.target.value;
    setForcedBidCloseTime(val);
    setErrors((prev) => {
      const next = { ...prev };
      delete next.forcedBidCloseTime;

      const closeMs = bidCloseTime ? new Date(bidCloseTime).getTime() : NaN;
      const forcedMs = val ? new Date(val).getTime() : NaN;

      if (!isNaN(closeMs) && !isNaN(forcedMs)) {
        if (forcedMs <= closeMs) {
          next.forcedBidCloseTime = 'Forced close time must be later than bid close time.';
        }
      }

      if (!val && prev.forcedBidCloseTime) {
        next.forcedBidCloseTime = 'Forced bid close date & time is required.';
      }
      return next;
    });
  };

  const handlePickupServiceDateChange = (e) => {
    setPickupServiceDate(e.target.value);
  };

  // British Auction Configuration changes
  const handleTriggerWindowChange = (e) => {
    const val = e.target.value;
    setTriggerWindowMinutes(val);
    setErrors((prev) => {
      const next = { ...prev };
      if (val === '' || val === null || isNaN(Number(val)) || Number(val) <= 0) {
        if (prev.triggerWindowMinutes) {
          next.triggerWindowMinutes = 'Trigger window must be greater than 0 minutes.';
        }
      } else {
        delete next.triggerWindowMinutes;
      }
      return next;
    });
  };

  const handleExtensionDurationChange = (e) => {
    const val = e.target.value;
    setExtensionDurationMinutes(val);
    setErrors((prev) => {
      const next = { ...prev };
      if (val === '' || val === null || isNaN(Number(val)) || Number(val) <= 0) {
        if (prev.extensionDurationMinutes) {
          next.extensionDurationMinutes = 'Extension duration must be greater than 0 minutes.';
        }
      } else {
        delete next.extensionDurationMinutes;
      }
      return next;
    });
  };

  const handleExtensionTriggerChange = (e) => {
    setExtensionTrigger(e.target.value);
    if (errors.extensionTrigger) {
      setErrors((prev) => ({ ...prev, extensionTrigger: '' }));
    }
  };

  // Dynamic Line Items operations
  const handleAddItem = () => {
    setItems((prev) => [...prev, createEmptyItem()]);
  };

  const handleRemoveItem = (index) => {
    if (items.length <= 1) return;
    setItems((prev) => prev.filter((_, i) => i !== index));
    setItemErrors((prev) => {
      const next = { ...prev };
      delete next[index];
      return next;
    });
  };

  const handleItemChange = (index, field, value) => {
    setItems((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });

    if (itemErrors[index]?.[field]) {
      setItemErrors((prev) => ({
        ...prev,
        [index]: { ...prev[index], [field]: '' },
      }));
    }
  };

  // Validation logic
  const validateForm = () => {
    const formErrs = {};
    const itemErrs = {};

    // 1. Buyer Validation
    if (!selectedBuyer || !selectedBuyer.id) {
      formErrs.buyer = 'Buyer is required.';
    }

    // 2. Title Validation
    if (!title || !title.trim()) {
      formErrs.title = 'RFQ title is required.';
    }

    // 3. Baseline Price Validation
    if (baselinePrice === '' || baselinePrice === null || baselinePrice === undefined) {
      formErrs.baselinePrice = 'Baseline price must be 0 or greater.';
    } else {
      const numVal = parseFloat(baselinePrice);
      if (isNaN(numVal) || numVal < 0) {
        formErrs.baselinePrice = 'Baseline price must be 0 or greater.';
      }
    }

    // 4. Auction Schedule Validation
    if (!bidStartTime) {
      formErrs.bidStartTime = 'Bid start date & time is required.';
    }

    if (!bidCloseTime) {
      formErrs.bidCloseTime = 'Bid close date & time is required.';
    }

    if (!forcedBidCloseTime) {
      formErrs.forcedBidCloseTime = 'Forced bid close date & time is required.';
    }

    // Chronological & Forced Close Consistency
    if (bidStartTime && bidCloseTime) {
      const startMs = new Date(bidStartTime).getTime();
      const closeMs = new Date(bidCloseTime).getTime();
      if (closeMs <= startMs) {
        formErrs.bidCloseTime = 'Bid close time must be later than bid start time.';
      }
    }

    if (bidCloseTime && forcedBidCloseTime) {
      const closeMs = new Date(bidCloseTime).getTime();
      const forcedMs = new Date(forcedBidCloseTime).getTime();
      if (forcedMs <= closeMs) {
        formErrs.forcedBidCloseTime = 'Forced close time must be later than bid close time.';
      }
    } else if (bidStartTime && forcedBidCloseTime) {
      const startMs = new Date(bidStartTime).getTime();
      const forcedMs = new Date(forcedBidCloseTime).getTime();
      if (forcedMs <= startMs) {
        formErrs.forcedBidCloseTime = 'Forced close time must be later than bid start time.';
      }
    }

    // 5. British Auction Configuration Validation
    if (triggerWindowMinutes === '' || triggerWindowMinutes === null || triggerWindowMinutes === undefined) {
      formErrs.triggerWindowMinutes = 'Trigger window must be greater than 0 minutes.';
    } else {
      const xNum = Number(triggerWindowMinutes);
      if (isNaN(xNum) || xNum <= 0) {
        formErrs.triggerWindowMinutes = 'Trigger window must be greater than 0 minutes.';
      }
    }

    if (extensionDurationMinutes === '' || extensionDurationMinutes === null || extensionDurationMinutes === undefined) {
      formErrs.extensionDurationMinutes = 'Extension duration must be greater than 0 minutes.';
    } else {
      const yNum = Number(extensionDurationMinutes);
      if (isNaN(yNum) || yNum <= 0) {
        formErrs.extensionDurationMinutes = 'Extension duration must be greater than 0 minutes.';
      }
    }

    if (!extensionTrigger) {
      formErrs.extensionTrigger = 'Extension trigger is required.';
    }

    // 6. Line Items Validation
    if (!items || items.length === 0) {
      formErrs.items = 'At least one RFQ item is required.';
    } else {
      items.forEach((it, idx) => {
        const itErr = {};
        if (!it.name || !it.name.trim()) {
          itErr.name = 'Item name is required.';
        }

        if (it.quantity === '' || it.quantity === null || it.quantity === undefined) {
          itErr.quantity = 'Quantity must be greater than 0.';
        } else {
          const qtyNum = parseFloat(it.quantity);
          if (isNaN(qtyNum) || qtyNum <= 0) {
            itErr.quantity = 'Quantity must be greater than 0.';
          }
        }

        if (!it.unit || !it.unit.trim()) {
          itErr.unit = 'Unit cannot be empty.';
        }

        if (Object.keys(itErr).length > 0) {
          itemErrs[idx] = itErr;
        }
      });
    }

    setErrors(formErrs);
    setItemErrors(itemErrs);

    return Object.keys(formErrs).length === 0 && Object.keys(itemErrs).length === 0;
  };

  // Form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setApiError('');

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        buyer_id: selectedBuyer.id,
        title: title.trim(),
        description: description.trim() || undefined,
        category: category.trim() || undefined,
        currency: currency.trim().toUpperCase(),
        baseline_price: parseFloat(baselinePrice),
        bid_start_time: bidStartTime ? new Date(bidStartTime).toISOString() : undefined,
        bid_close_time: bidCloseTime ? new Date(bidCloseTime).toISOString() : undefined,
        forced_bid_close_time: forcedBidCloseTime ? new Date(forcedBidCloseTime).toISOString() : undefined,
        pickup_service_date: pickupServiceDate ? new Date(pickupServiceDate).toISOString() : undefined,
        trigger_window_minutes: parseInt(triggerWindowMinutes, 10),
        extension_duration_minutes: parseInt(extensionDurationMinutes, 10),
        extension_trigger: extensionTrigger,
        items: items.map((it) => ({
          name: it.name.trim(),
          description: it.description.trim() || undefined,
          quantity: parseFloat(it.quantity),
          unit: it.unit.trim(),
        })),
      };

      const result = await createRFQ(payload);
      setCreatedRfqResult(result);
    } catch (err) {
      if (err.response?.status === 404) {
        setApiError('Buyer not found. Please select a valid buyer.');
      } else if (err.response?.status === 409) {
        setApiError('A conflict occurred with the submitted data.');
      } else if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (Array.isArray(detail)) {
          setApiError(detail.map((d) => d.msg || d).join(', '));
        } else {
          setApiError(String(detail));
        }
      } else {
        setApiError('Unable to create RFQ. Please check the form and try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Reset form handler
  const handleResetForm = () => {
    setSelectedBuyer(null);
    setTitle('');
    setDescription('');
    setCategory('');
    setCurrency('USD');
    setBaselinePrice('');
    setBidStartTime('');
    setBidCloseTime('');
    setForcedBidCloseTime('');
    setPickupServiceDate('');
    setTriggerWindowMinutes(10);
    setExtensionDurationMinutes(5);
    setExtensionTrigger('BID_RECEIVED');
    setItems([createEmptyItem()]);
    setErrors({});
    setItemErrors({});
    setApiError('');
    setCreatedRfqResult(null);
  };

  return (
    <div className="page-container" id="page-create-rfq">
      <div className="page-header">
        <h1 className="page-title">Create RFQ</h1>
        <p className="page-subtitle">
          Configure procurement requirements, British Auction schedule, and extension parameters.
        </p>
      </div>

      {/* Success State */}
      {createdRfqResult ? (
        <div className="success-card" id="rfq-success-card">
          <div className="success-icon-large">
            <CheckCircle2 size={36} />
          </div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)' }}>
            RFQ created successfully.
          </h2>
          <p style={{ color: 'var(--text-secondary)', maxWidth: '540px' }}>
            The Request for Quotation and British Auction configuration have been saved and scheduled.
          </p>

          <div className="success-details" id="rfq-success-details">
            <div className="success-row">
              <span>RFQ ID:</span>
              <strong id="created-rfq-id" style={{ fontFamily: 'monospace', color: '#38bdf8' }}>
                {createdRfqResult.id}
              </strong>
            </div>
            <div className="success-row">
              <span>Title:</span>
              <strong id="created-rfq-title">{createdRfqResult.title}</strong>
            </div>
            <div className="success-row">
              <span>Baseline Price:</span>
              <strong id="created-rfq-price">
                {createdRfqResult.baseline_price} {createdRfqResult.currency}
              </strong>
            </div>
            <div className="success-row">
              <span>Trigger Window:</span>
              <strong id="created-rfq-trigger-window">
                {createdRfqResult.trigger_window_minutes || createdRfqResult.auction?.trigger_window_minutes || triggerWindowMinutes} Minutes
              </strong>
            </div>
            <div className="success-row">
              <span>Extension Duration:</span>
              <strong id="created-rfq-extension-duration">
                {createdRfqResult.extension_duration_minutes || createdRfqResult.auction?.extension_duration_minutes || extensionDurationMinutes} Minutes
              </strong>
            </div>
            <div className="success-row">
              <span>Extension Trigger:</span>
              <strong id="created-rfq-extension-trigger">
                {createdRfqResult.extension_trigger || createdRfqResult.auction?.extension_trigger || extensionTrigger}
              </strong>
            </div>
            <div className="success-row">
              <span>Line Items:</span>
              <strong id="created-rfq-items-count">
                {createdRfqResult.items?.length || 0} item(s)
              </strong>
            </div>
            <div className="success-row">
              <span>Status:</span>
              <span className="badge badge-info">{createdRfqResult.status}</span>
            </div>
          </div>

          <button
            type="button"
            className="btn btn-primary"
            onClick={handleResetForm}
            id="btn-create-another-rfq"
            style={{ marginTop: '0.5rem' }}
          >
            <RotateCcw size={16} />
            <span>Create Another RFQ</span>
          </button>
        </div>
      ) : (
        /* RFQ Creation Form */
        <form onSubmit={handleSubmit} noValidate id="form-create-rfq">
          {apiError && (
            <div className="alert alert-error" role="alert" id="rfq-api-error">
              <AlertCircle size={18} className="alert-icon" />
              <div className="alert-content">
                <div className="alert-title">Submission Failed</div>
                <div>{apiError}</div>
              </div>
            </div>
          )}

          {/* Section 1: Buyer Information */}
          <BuyerSection
            selectedBuyer={selectedBuyer}
            onBuyerSelected={handleBuyerSelected}
            error={errors.buyer}
          />

          {/* Section 2: RFQ Information */}
          <div className="form-section" id="section-rfq-info">
            <div className="section-header">
              <div className="section-title">
                <FileText size={20} color="#6366f1" />
                <span>2. RFQ Information</span>
              </div>
              <span className="section-badge">Required</span>
            </div>

            <div className="form-grid">
              {/* RFQ Title */}
              <div className="form-group">
                <label htmlFor="rfq-title" className="form-label">
                  RFQ Title <span className="required">*</span>
                </label>
                <input
                  id="rfq-title"
                  type="text"
                  className={`form-control ${errors.title ? 'error' : ''}`}
                  placeholder="e.g. Industrial Component Procurement"
                  value={title}
                  onChange={handleTitleChange}
                  disabled={isSubmitting}
                />
                {errors.title && (
                  <span className="error-text">
                    <AlertCircle size={13} />
                    {errors.title}
                  </span>
                )}
              </div>

              {/* Description */}
              <div className="form-group">
                <label htmlFor="rfq-description" className="form-label">
                  Description
                </label>
                <textarea
                  id="rfq-description"
                  className="form-control"
                  placeholder="Detailed procurement specifications and commercial requirements (Optional)"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  disabled={isSubmitting}
                  rows={3}
                />
              </div>

              {/* Category, Currency, Baseline Price */}
              <div className="form-grid-3">
                <div className="form-group">
                  <label htmlFor="rfq-category" className="form-label">
                    Category
                  </label>
                  <input
                    id="rfq-category"
                    type="text"
                    className="form-control"
                    placeholder="e.g. Industrial Components"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    disabled={isSubmitting}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="rfq-currency" className="form-label">
                    Currency <span className="required">*</span>
                  </label>
                  <select
                    id="rfq-currency"
                    className="form-control"
                    value={currency}
                    onChange={(e) => setCurrency(e.target.value)}
                    disabled={isSubmitting}
                  >
                    {CURRENCY_OPTIONS.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="rfq-baseline-price" className="form-label">
                    Baseline Price <span className="required">*</span>
                  </label>
                  <input
                    id="rfq-baseline-price"
                    type="number"
                    step="any"
                    min="0"
                    className={`form-control ${errors.baselinePrice ? 'error' : ''}`}
                    placeholder="e.g. 50000"
                    value={baselinePrice}
                    onChange={handleBaselinePriceChange}
                    disabled={isSubmitting}
                  />
                  {errors.baselinePrice && (
                    <span className="error-text">
                      <AlertCircle size={13} />
                      {errors.baselinePrice}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Section 3: Auction Schedule */}
          <div className="form-section" id="section-auction-schedule">
            <div className="section-header">
              <div className="section-title">
                <Clock size={20} color="#6366f1" />
                <span>3. Auction Schedule</span>
              </div>
              <span className="section-badge">Required</span>
            </div>

            <div className="form-grid-2">
              {/* Bid Start Date & Time */}
              <div className="form-group">
                <label htmlFor="rfq-bid-start-time" className="form-label">
                  Bid Start Date & Time <span className="required">*</span>
                </label>
                <input
                  id="rfq-bid-start-time"
                  type="datetime-local"
                  className={`form-control ${errors.bidStartTime ? 'error' : ''}`}
                  value={bidStartTime}
                  onChange={handleBidStartTimeChange}
                  disabled={isSubmitting}
                />
                <span className="helper-text">When bidding opens for participating suppliers.</span>
                {errors.bidStartTime && (
                  <span className="error-text">
                    <AlertCircle size={13} />
                    {errors.bidStartTime}
                  </span>
                )}
              </div>

              {/* Bid Close Date & Time */}
              <div className="form-group">
                <label htmlFor="rfq-bid-close-time" className="form-label">
                  Bid Close Date & Time <span className="required">*</span>
                </label>
                <input
                  id="rfq-bid-close-time"
                  type="datetime-local"
                  className={`form-control ${errors.bidCloseTime ? 'error' : ''}`}
                  value={bidCloseTime}
                  onChange={handleBidCloseTimeChange}
                  disabled={isSubmitting}
                />
                <span className="helper-text">Scheduled initial closing time for bidding.</span>
                {errors.bidCloseTime && (
                  <span className="error-text">
                    <AlertCircle size={13} />
                    {errors.bidCloseTime}
                  </span>
                )}
              </div>

              {/* Forced Bid Close Date & Time */}
              <div className="form-group">
                <label htmlFor="rfq-forced-bid-close-time" className="form-label">
                  Forced Bid Close Date & Time <span className="required">*</span>
                </label>
                <input
                  id="rfq-forced-bid-close-time"
                  type="datetime-local"
                  className={`form-control ${errors.forcedBidCloseTime ? 'error' : ''}`}
                  value={forcedBidCloseTime}
                  onChange={handleForcedBidCloseTimeChange}
                  disabled={isSubmitting}
                />
                <span className="helper-text">The auction cannot be extended beyond this time.</span>
                {errors.forcedBidCloseTime && (
                  <span className="error-text">
                    <AlertCircle size={13} />
                    {errors.forcedBidCloseTime}
                  </span>
                )}
              </div>

              {/* Pickup / Service Date */}
              <div className="form-group">
                <label htmlFor="rfq-pickup-service-date" className="form-label">
                  Pickup / Service Date
                </label>
                <input
                  id="rfq-pickup-service-date"
                  type="datetime-local"
                  className="form-control"
                  value={pickupServiceDate}
                  onChange={handlePickupServiceDateChange}
                  disabled={isSubmitting}
                />
                <span className="helper-text">Expected fulfillment / delivery date (Optional).</span>
              </div>
            </div>
          </div>

          {/* Section 4: British Auction Configuration */}
          <div className="form-section" id="section-british-auction-config">
            <div className="section-header">
              <div className="section-title">
                <Zap size={20} color="#06b6d4" />
                <span>4. British Auction Configuration</span>
              </div>
              <span className="section-badge">Dynamic Rules</span>
            </div>

            <div className="form-grid-3">
              {/* Trigger Window X */}
              <div className="form-group">
                <label htmlFor="rfq-trigger-window" className="form-label">
                  Trigger Window (X Minutes) <span className="required">*</span>
                </label>
                <input
                  id="rfq-trigger-window"
                  type="number"
                  min="1"
                  step="1"
                  className={`form-control ${errors.triggerWindowMinutes ? 'error' : ''}`}
                  placeholder="e.g. 10"
                  value={triggerWindowMinutes}
                  onChange={handleTriggerWindowChange}
                  disabled={isSubmitting}
                />
                <span className="helper-text">How many minutes before the current bid close time the system monitors activity.</span>
                {errors.triggerWindowMinutes && (
                  <span className="error-text">
                    <AlertCircle size={13} />
                    {errors.triggerWindowMinutes}
                  </span>
                )}
              </div>

              {/* Extension Duration Y */}
              <div className="form-group">
                <label htmlFor="rfq-extension-duration" className="form-label">
                  Extension Duration (Y Minutes) <span className="required">*</span>
                </label>
                <input
                  id="rfq-extension-duration"
                  type="number"
                  min="1"
                  step="1"
                  className={`form-control ${errors.extensionDurationMinutes ? 'error' : ''}`}
                  placeholder="e.g. 5"
                  value={extensionDurationMinutes}
                  onChange={handleExtensionDurationChange}
                  disabled={isSubmitting}
                />
                <span className="helper-text">How many minutes are added when the configured trigger occurs.</span>
                {errors.extensionDurationMinutes && (
                  <span className="error-text">
                    <AlertCircle size={13} />
                    {errors.extensionDurationMinutes}
                  </span>
                )}
              </div>

              {/* Extension Trigger */}
              <div className="form-group">
                <label htmlFor="rfq-extension-trigger" className="form-label">
                  Extension Trigger <span className="required">*</span>
                </label>
                <select
                  id="rfq-extension-trigger"
                  className={`form-control ${errors.extensionTrigger ? 'error' : ''}`}
                  value={extensionTrigger}
                  onChange={handleExtensionTriggerChange}
                  disabled={isSubmitting}
                >
                  {EXTENSION_TRIGGER_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                <span className="helper-text">Defines which bidding/ranking activity causes an automatic extension.</span>
                {errors.extensionTrigger && (
                  <span className="error-text">
                    <AlertCircle size={13} />
                    {errors.extensionTrigger}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Section 5: RFQ Line Items */}
          <div className="form-section" id="section-rfq-items">
            <div className="section-header">
              <div className="section-title">
                <Layers size={20} color="#6366f1" />
                <span>5. RFQ Line Items</span>
              </div>
              <span className="section-badge">
                {items.length} {items.length === 1 ? 'Item' : 'Items'}
              </span>
            </div>

            {errors.items && (
              <div className="alert alert-error" style={{ marginBottom: '1rem' }}>
                <AlertCircle size={16} />
                <span>{errors.items}</span>
              </div>
            )}

            <div className="items-container" id="rfq-items-list">
              {items.map((item, index) => (
                <RFQItemRow
                  key={item.id}
                  item={item}
                  index={index}
                  onChange={handleItemChange}
                  onRemove={handleRemoveItem}
                  canRemove={items.length > 1}
                  errors={itemErrors[index]}
                  disabled={isSubmitting}
                />
              ))}
            </div>

            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleAddItem}
              disabled={isSubmitting}
              id="btn-add-item"
            >
              <Plus size={16} />
              <span>Add Item</span>
            </button>
          </div>

          {/* Form Actions */}
          <div className="form-actions">
            <button
              type="submit"
              className="btn btn-primary btn-submit"
              disabled={isSubmitting}
              id="btn-submit-rfq"
            >
              {isSubmitting ? (
                <>
                  <RefreshCw size={18} className="spinner" />
                  <span>Creating RFQ...</span>
                </>
              ) : (
                <>
                  <Send size={18} />
                  <span>Create RFQ</span>
                </>
              )}
            </button>
          </div>
        </form>
      )}
    </div>
  );
};

export default CreateRfq;

