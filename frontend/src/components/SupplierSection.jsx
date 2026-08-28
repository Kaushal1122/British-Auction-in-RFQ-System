import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import {
  Briefcase,
  UserPlus,
  UserCheck,
  AlertCircle,
  RefreshCw,
  X,
  Building2,
  Mail,
  RotateCcw,
} from 'lucide-react';
import { createSupplier, listSuppliers } from '../services/api';

export const SupplierSection = ({ selectedSupplier, onSupplierSelected, error }) => {
  // Supplier List State
  const [supplierList, setSupplierList] = useState([]);
  const [loadingSuppliers, setLoadingSuppliers] = useState(true);
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
  const [existingSupplierMatch, setExistingSupplierMatch] = useState(null);

  // Fetch available suppliers on mount
  const fetchSuppliers = async () => {
    setLoadingSuppliers(true);
    setLoadError('');
    try {
      const data = await listSuppliers({ limit: 100 });
      setSupplierList(Array.isArray(data) ? data : []);
    } catch {
      setLoadError('Unable to load suppliers. Please try again.');
    } finally {
      setLoadingSuppliers(false);
    }
  };

  useEffect(() => {
    fetchSuppliers();
  }, []);

  const handleOpenModal = () => {
    setFormData({
      name: '',
      email: '',
      company_name: '',
    });
    setFieldErrors({});
    setModalError('');
    setExistingSupplierMatch(null);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    if (isSubmitting) return;
    setIsModalOpen(false);
    setFieldErrors({});
    setModalError('');
    setExistingSupplierMatch(null);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (fieldErrors[name]) {
      setFieldErrors((prev) => ({ ...prev, [name]: '' }));
    }
    if (modalError) {
      setModalError('');
      setExistingSupplierMatch(null);
    }
  };

  const handleDropdownSelect = (e) => {
    const supplierId = e.target.value;
    if (!supplierId) {
      onSupplierSelected(null);
      return;
    }
    const found = supplierList.find((s) => s.id === supplierId);
    if (found) {
      onSupplierSelected(found);
    }
  };

  const handleChangeSupplier = () => {
    onSupplierSelected(null);
  };

  const validateSupplierForm = () => {
    const errors = {};
    if (!formData.name || !formData.name.trim()) {
      errors.name = 'Supplier name is required.';
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

  const handleSubmitSupplier = async (e) => {
    e.preventDefault();
    if (!validateSupplierForm()) return;

    setIsSubmitting(true);
    setModalError('');
    setExistingSupplierMatch(null);

    const normalizedEmail = formData.email.trim().toLowerCase();

    try {
      const payload = {
        name: formData.name.trim(),
        email: normalizedEmail,
        company_name: formData.company_name.trim() || undefined,
      };

      const createdSupplier = await createSupplier(payload);
      // Prepend or add newly created supplier to list
      setSupplierList((prev) => [
        createdSupplier,
        ...prev.filter((s) => s.id !== createdSupplier.id),
      ]);
      // Automatically select the newly created supplier
      onSupplierSelected(createdSupplier);
      setIsModalOpen(false);
    } catch (err) {
      if (err.response?.status === 409) {
        setModalError('A supplier with this email already exists. Please select the existing supplier.');
        // Check if we already have this supplier in our loaded list
        let match = supplierList.find((s) => s.email?.toLowerCase() === normalizedEmail);
        if (!match) {
          try {
            const fetched = await listSuppliers({ email: normalizedEmail });
            if (Array.isArray(fetched) && fetched.length > 0) {
              match = fetched[0];
              setSupplierList((prev) => [
                match,
                ...prev.filter((s) => s.id !== match.id),
              ]);
            }
          } catch {
            // Ignore backend lookup errors
          }
        }
        if (match) {
          setExistingSupplierMatch(match);
        }
      } else if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (Array.isArray(detail)) {
          setModalError(detail.map((d) => d.msg || d).join(', '));
        } else {
          setModalError(String(detail));
        }
      } else {
        setModalError('Unable to create supplier. Please check the details and try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSelectExistingFromConflict = () => {
    if (existingSupplierMatch) {
      onSupplierSelected(existingSupplierMatch);
      handleCloseModal();
    }
  };

  return (
    <div className="form-section" id="section-supplier-info">
      <div className="section-header">
        <div className="section-title">
          <Briefcase size={20} color="#6366f1" />
          <span>2. Supplier Identity</span>
        </div>
        <span className="section-badge">Required</span>
      </div>

      {/* Selected Supplier Display */}
      {selectedSupplier ? (
        <div className="buyer-status-box" id="supplier-selected-display">
          <div className="buyer-empty-state">
            <div className="buyer-icon-wrapper active">
              <UserCheck size={24} />
            </div>
            <div className="buyer-info-text">
              <span className="buyer-name" id="selected-supplier-name">
                {selectedSupplier.name}
              </span>
              {selectedSupplier.company_name && (
                <span className="buyer-company" id="selected-supplier-company">
                  <Building2 size={13} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'middle' }} />
                  {selectedSupplier.company_name}
                </span>
              )}
              <span className="buyer-email" id="selected-supplier-email">
                <Mail size={13} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'middle' }} />
                {selectedSupplier.email}
              </span>
            </div>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleChangeSupplier}
            id="btn-change-supplier"
          >
            Change Supplier
          </button>
        </div>
      ) : (
        /* Supplier Selection & Creation Controls */
        <div id="supplier-selection-container">
          {/* Loading State */}
          {loadingSuppliers && (
            <div className="buyer-status-box" id="supplier-loading-state">
              <div className="buyer-empty-state">
                <div className="buyer-icon-wrapper">
                  <RefreshCw size={20} className="spinner" />
                </div>
                <div className="buyer-info-text">
                  <span className="buyer-name" style={{ color: 'var(--text-secondary)' }}>
                    Loading suppliers...
                  </span>
                  <span className="helper-text">Fetching registered suppliers from backend...</span>
                </div>
              </div>
            </div>
          )}

          {/* Load Error State */}
          {!loadingSuppliers && loadError && (
            <div className="alert alert-error" role="alert" id="supplier-load-error" style={{ marginBottom: '1rem' }}>
              <AlertCircle size={18} className="alert-icon" />
              <div className="alert-content" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', flexWrap: 'wrap', gap: '0.5rem' }}>
                <div>
                  <div className="alert-title">Supplier Loading Failed</div>
                  <div>{loadError}</div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={fetchSuppliers}
                    id="btn-retry-load-suppliers"
                    style={{ padding: '0.35rem 0.75rem', fontSize: '0.85rem' }}
                  >
                    <RotateCcw size={14} />
                    <span>Retry</span>
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={handleOpenModal}
                    id="btn-create-supplier-open"
                    style={{ padding: '0.35rem 0.75rem', fontSize: '0.85rem' }}
                  >
                    <UserPlus size={14} />
                    <span>Create Supplier</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Loaded Suppliers Dropdown & Create Option */}
          {!loadingSuppliers && !loadError && (
            <>
              {supplierList.length === 0 ? (
                <div className="buyer-status-box" id="supplier-empty-state">
                  <div className="buyer-empty-state">
                    <div className="buyer-icon-wrapper">
                      <Briefcase size={24} />
                    </div>
                    <div className="buyer-info-text">
                      <span className="buyer-name" id="no-suppliers-msg" style={{ color: 'var(--text-secondary)' }}>
                        No suppliers found.
                      </span>
                      <span className="helper-text">
                        Register a new supplier profile to place a bid on this RFQ.
                      </span>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={handleOpenModal}
                    id="btn-create-supplier-open"
                  >
                    <UserPlus size={16} />
                    <span>Create Supplier</span>
                  </button>
                </div>
              ) : (
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label htmlFor="select-supplier" className="form-label">
                    Select Existing Supplier <span className="required">*</span>
                  </label>
                  <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
                    <select
                      id="select-supplier"
                      aria-label="Select Existing Supplier"
                      className={`form-control ${error ? 'error' : ''}`}
                      value=""
                      onChange={handleDropdownSelect}
                      style={{ flex: '1 1 280px' }}
                    >
                      <option value="">-- Choose an existing supplier --</option>
                      {supplierList.map((sup) => (
                        <option key={sup.id} value={sup.id}>
                          {sup.name}{sup.company_name ? ` — ${sup.company_name}` : ''} — {sup.email}
                        </option>
                      ))}
                    </select>

                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={handleOpenModal}
                      id="btn-create-supplier-open"
                      style={{ whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                    >
                      <UserPlus size={16} />
                      <span>+ Create New Supplier</span>
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {error && !selectedSupplier && (
        <div className="error-text" id="supplier-required-error" style={{ marginTop: '0.75rem' }}>
          <AlertCircle size={14} />
          <span>{error}</span>
        </div>
      )}

      {/* Create Supplier Modal */}
      {isModalOpen && typeof document !== 'undefined' && createPortal(
        <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="modal-supplier-title">
          <div className="modal-dialog">
            <div className="modal-header">
              <div className="modal-title" id="modal-supplier-title">
                <UserPlus size={20} color="#6366f1" />
                <span>Create Supplier Profile</span>
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
              id="form-create-supplier"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleSubmitSupplier(e);
                }
              }}
            >
              <div className="modal-body">
                {modalError && (
                  <div className="alert alert-error" role="alert" id="supplier-modal-error">
                    <AlertCircle size={16} className="alert-icon" />
                    <div className="alert-content" style={{ width: '100%' }}>
                      <div className="alert-title">Profile Setup Failed</div>
                      <div>{modalError}</div>
                      {existingSupplierMatch && (
                        <div style={{ marginTop: '0.5rem' }}>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={handleSelectExistingFromConflict}
                            id="btn-select-existing-supplier-conflict"
                            style={{ fontSize: '0.825rem', padding: '0.3rem 0.65rem' }}
                          >
                            Select Existing Supplier ({existingSupplierMatch.name})
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                <div className="form-group">
                  <label htmlFor="supplier-input-name" className="form-label">
                    Full Name / Contact <span className="required">*</span>
                  </label>
                  <input
                    id="supplier-input-name"
                    name="name"
                    type="text"
                    className={`form-control ${fieldErrors.name ? 'error' : ''}`}
                    placeholder="e.g. Acme Industrial Supplies"
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
                  <label htmlFor="supplier-input-email" className="form-label">
                    Email Address <span className="required">*</span>
                  </label>
                  <input
                    id="supplier-input-email"
                    name="email"
                    type="email"
                    className={`form-control ${fieldErrors.email ? 'error' : ''}`}
                    placeholder="e.g. supplier@example.com"
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
                  <label htmlFor="supplier-input-company" className="form-label">
                    Company Name
                  </label>
                  <input
                    id="supplier-input-company"
                    name="company_name"
                    type="text"
                    className="form-control"
                    placeholder="e.g. Acme Corporation (Optional)"
                    value={formData.company_name}
                    onChange={handleChange}
                    disabled={isSubmitting}
                  />
                  <span className="helper-text">Optional organization or business entity</span>
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
                  onClick={handleSubmitSupplier}
                  disabled={isSubmitting}
                  id="btn-submit-supplier"
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw size={16} className="spinner" />
                      <span>Saving Profile...</span>
                    </>
                  ) : (
                    <span>Save Supplier</span>
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

export default SupplierSection;
