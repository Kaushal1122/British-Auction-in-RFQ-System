import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import {
  User,
  UserPlus,
  UserCheck,
  AlertCircle,
  RefreshCw,
  X,
  Building2,
  Mail,
  RotateCcw,
} from 'lucide-react';
import { createBuyer, getBuyers } from '../services/api';

export const BuyerSection = ({ selectedBuyer, onBuyerSelected, error }) => {
  // Buyer List State
  const [buyerList, setBuyerList] = useState([]);
  const [loadingBuyers, setLoadingBuyers] = useState(true);
  const [loadError, setLoadError] = useState('');

  // Modal & Form State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company_name: '',
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [modalError, setModalError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [existingBuyerMatch, setExistingBuyerMatch] = useState(null);

  // Fetch available buyers on mount
  const fetchBuyers = async () => {
    setLoadingBuyers(true);
    setLoadError('');
    try {
      const data = await getBuyers({ limit: 1000 });
      setBuyerList(Array.isArray(data) ? data : []);
    } catch {
      setLoadError('Unable to load buyers. Please try again.');
    } finally {
      setLoadingBuyers(false);
    }
  };

  useEffect(() => {
    fetchBuyers();
  }, []);

  const handleOpenModal = () => {
    setFormData({
      name: '',
      email: '',
      company_name: '',
    });
    setFieldErrors({});
    setModalError('');
    setExistingBuyerMatch(null);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    if (isSubmitting) return;
    setIsModalOpen(false);
    setFieldErrors({});
    setModalError('');
    setExistingBuyerMatch(null);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (fieldErrors[name]) {
      setFieldErrors((prev) => ({ ...prev, [name]: '' }));
    }
    if (modalError) {
      setModalError('');
      setExistingBuyerMatch(null);
    }
  };

  const handleDropdownSelect = (e) => {
    const buyerId = e.target.value;
    if (!buyerId) {
      onBuyerSelected(null);
      return;
    }
    const found = buyerList.find((b) => b.id === buyerId);
    if (found) {
      onBuyerSelected(found);
    }
  };

  const handleChangeBuyer = () => {
    onBuyerSelected(null);
  };

  const validateBuyerForm = () => {
    const errors = {};
    if (!formData.name || !formData.name.trim()) {
      errors.name = 'Buyer name is required.';
    }

    if (!formData.email || !formData.email.trim()) {
      errors.email = 'Email address is required.';
    } else {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(formData.email.trim())) {
        errors.email = 'Please enter a valid email address.';
      }
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmitBuyer = async (e) => {
    e.preventDefault();
    if (!validateBuyerForm()) return;

    setIsSubmitting(true);
    setModalError('');
    setExistingBuyerMatch(null);

    const normalizedEmail = formData.email.trim().toLowerCase();

    try {
      const payload = {
        name: formData.name.trim(),
        email: normalizedEmail,
        company_name: formData.company_name.trim() || undefined,
      };

      const createdBuyer = await createBuyer(payload);
      // Prepend or add newly created buyer to list
      setBuyerList((prev) => [
        createdBuyer,
        ...prev.filter((b) => b.id !== createdBuyer.id),
      ]);
      // Automatically select the newly created buyer
      onBuyerSelected(createdBuyer);
      setIsModalOpen(false);
    } catch (err) {
      if (err.response?.status === 409) {
        setModalError('A buyer with this email already exists.');
        // Check if we already have this buyer in our loaded list
        let match = buyerList.find((b) => b.email?.toLowerCase() === normalizedEmail);
        if (!match) {
          try {
            const fetched = await getBuyers({ email: normalizedEmail });
            if (Array.isArray(fetched) && fetched.length > 0) {
              match = fetched[0];
              setBuyerList((prev) => [
                match,
                ...prev.filter((b) => b.id !== match.id),
              ]);
            }
          } catch {
            // Ignore backend lookup errors
          }
        }
        if (match) {
          setExistingBuyerMatch(match);
        }
      } else if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (Array.isArray(detail)) {
          setModalError(detail.map((d) => d.msg || d).join(', '));
        } else {
          setModalError(String(detail));
        }
      } else {
        setModalError('Unable to create buyer. Please check the form and try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSelectExistingFromConflict = () => {
    if (existingBuyerMatch) {
      onBuyerSelected(existingBuyerMatch);
      handleCloseModal();
    }
  };

  return (
    <div className="form-section" id="section-buyer-info">
      <div className="section-header">
        <div className="section-title">
          <User size={20} color="#6366f1" />
          <span>1. Buyer Information</span>
        </div>
        <span className="section-badge">Required</span>
      </div>

      {/* Selected Buyer Display */}
      {selectedBuyer ? (
        <div className="buyer-status-box" id="buyer-selected-display">
          <div className="buyer-empty-state">
            <div className="buyer-icon-wrapper active">
              <UserCheck size={24} />
            </div>
            <div className="buyer-info-text">
              <span className="buyer-name" id="selected-buyer-name">{selectedBuyer.name}</span>
              {selectedBuyer.company_name && (
                <span className="buyer-company" id="selected-buyer-company">
                  <Building2 size={13} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'middle' }} />
                  {selectedBuyer.company_name}
                </span>
              )}
              <span className="buyer-email" id="selected-buyer-email">
                <Mail size={13} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'middle' }} />
                {selectedBuyer.email}
              </span>
            </div>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleChangeBuyer}
            id="btn-change-buyer"
          >
            Change Buyer
          </button>
        </div>
      ) : (
        /* Buyer Selection & Creation Controls */
        <div id="buyer-selection-container">
          {/* Loading State */}
          {loadingBuyers && (
            <div className="buyer-status-box" id="buyer-loading-state">
              <div className="buyer-empty-state">
                <div className="buyer-icon-wrapper">
                  <RefreshCw size={20} className="spinner" />
                </div>
                <div className="buyer-info-text">
                  <span className="buyer-name" style={{ color: 'var(--text-secondary)' }}>
                    Loading buyers...
                  </span>
                  <span className="helper-text">Fetching registered buyers from backend...</span>
                </div>
              </div>
            </div>
          )}

          {/* Load Error State */}
          {!loadingBuyers && loadError && (
            <div className="alert alert-error" role="alert" id="buyer-load-error" style={{ marginBottom: '1rem' }}>
              <AlertCircle size={18} className="alert-icon" />
              <div className="alert-content" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', flexWrap: 'wrap', gap: '0.5rem' }}>
                <div>
                  <div className="alert-title">Buyer Loading Failed</div>
                  <div>{loadError}</div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={fetchBuyers}
                    id="btn-retry-load-buyers"
                    style={{ padding: '0.35rem 0.75rem', fontSize: '0.85rem' }}
                  >
                    <RotateCcw size={14} />
                    <span>Retry</span>
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={handleOpenModal}
                    id="btn-create-buyer-open"
                    style={{ padding: '0.35rem 0.75rem', fontSize: '0.85rem' }}
                  >
                    <UserPlus size={14} />
                    <span>Create Buyer</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Loaded Buyers Dropdown & Create Option */}
          {!loadingBuyers && !loadError && (
            <>
              {buyerList.length === 0 ? (
                <div className="buyer-status-box" id="buyer-empty-state">
                  <div className="buyer-empty-state">
                    <div className="buyer-icon-wrapper">
                      <User size={24} />
                    </div>
                    <div className="buyer-info-text">
                      <span className="buyer-name" id="no-buyers-msg" style={{ color: 'var(--text-secondary)' }}>
                        No buyers found.
                      </span>
                      <span className="helper-text">
                        A registered buyer profile is required to initiate an RFQ.
                      </span>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={handleOpenModal}
                    id="btn-create-buyer-open"
                  >
                    <UserPlus size={16} />
                    <span>Create Buyer</span>
                  </button>
                </div>
              ) : (
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label htmlFor="select-buyer" className="form-label">
                    Select Existing Buyer <span className="required">*</span>
                  </label>
                  <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
                    <select
                      id="select-buyer"
                      aria-label="Select Existing Buyer"
                      className={`form-control ${error ? 'error' : ''}`}
                      value=""
                      onChange={handleDropdownSelect}
                      style={{ flex: '1 1 280px' }}
                    >
                      <option value="">-- Choose an existing buyer --</option>
                      {buyerList.map((buyer) => (
                        <option key={buyer.id} value={buyer.id}>
                          {buyer.name}{buyer.company_name ? ` — ${buyer.company_name}` : ''} — {buyer.email}
                        </option>
                      ))}
                    </select>

                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={handleOpenModal}
                      id="btn-create-buyer-open"
                      style={{ whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                    >
                      <UserPlus size={16} />
                      <span>+ Create New Buyer</span>
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {error && !selectedBuyer && (
        <div className="error-text" id="buyer-required-error" style={{ marginTop: '0.75rem' }}>
          <AlertCircle size={14} />
          <span>{error}</span>
        </div>
      )}

      {/* Create Buyer Modal */}
      {isModalOpen && typeof document !== 'undefined' && createPortal(
        <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="modal-buyer-title">
          <div className="modal-dialog">
            <div className="modal-header">
              <div className="modal-title" id="modal-buyer-title">
                <UserPlus size={20} color="#6366f1" />
                <span>Create Buyer Profile</span>
              </div>
              <button
                type="button"
                className="btn-close"
                onClick={handleCloseModal}
                disabled={isSubmitting}
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>

            <div
              noValidate
              id="form-create-buyer"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleSubmitBuyer(e);
                }
              }}
            >
              <div className="modal-body">
                {modalError && (
                  <div className="alert alert-error" role="alert" id="buyer-modal-error">
                    <AlertCircle size={16} className="alert-icon" />
                    <div className="alert-content" style={{ width: '100%' }}>
                      <div className="alert-title">Creation Failed</div>
                      <div>{modalError}</div>
                      {existingBuyerMatch && (
                        <div style={{ marginTop: '0.5rem' }}>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={handleSelectExistingFromConflict}
                            id="btn-select-existing-buyer-conflict"
                            style={{ fontSize: '0.825rem', padding: '0.3rem 0.65rem' }}
                          >
                            Select Existing Buyer ({existingBuyerMatch.name})
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                <div className="form-group">
                  <label htmlFor="buyer-input-name" className="form-label">
                    Full Name <span className="required">*</span>
                  </label>
                  <input
                    id="buyer-input-name"
                    name="name"
                    type="text"
                    className={`form-control ${fieldErrors.name ? 'error' : ''}`}
                    placeholder="e.g. John Doe"
                    value={formData.name}
                    onChange={handleChange}
                    disabled={isSubmitting}
                    autoFocus
                  />
                  {fieldErrors.name && (
                    <span className="error-text">
                      <AlertCircle size={13} />
                      {fieldErrors.name}
                    </span>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor="buyer-input-email" className="form-label">
                    Email Address <span className="required">*</span>
                  </label>
                  <input
                    id="buyer-input-email"
                    name="email"
                    type="email"
                    className={`form-control ${fieldErrors.email ? 'error' : ''}`}
                    placeholder="e.g. john@example.com"
                    value={formData.email}
                    onChange={handleChange}
                    disabled={isSubmitting}
                  />
                  {fieldErrors.email && (
                    <span className="error-text">
                      <AlertCircle size={13} />
                      {fieldErrors.email}
                    </span>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor="buyer-input-company" className="form-label">
                    Company Name
                  </label>
                  <input
                    id="buyer-input-company"
                    name="company_name"
                    type="text"
                    className="form-control"
                    placeholder="e.g. ABC Manufacturing Corp (Optional)"
                    value={formData.company_name}
                    onChange={handleChange}
                    disabled={isSubmitting}
                  />
                  <span className="helper-text">Optional organization name</span>
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleCloseModal}
                  disabled={isSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleSubmitBuyer}
                  disabled={isSubmitting}
                  id="btn-submit-buyer"
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw size={16} className="spinner" />
                      <span>Creating Buyer...</span>
                    </>
                  ) : (
                    <span>Create Buyer</span>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};

export default BuyerSection;

