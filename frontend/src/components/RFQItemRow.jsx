import React from 'react';
import { Trash2, AlertCircle, Package } from 'lucide-react';

export const RFQItemRow = ({
  item,
  index,
  onChange,
  onRemove,
  canRemove,
  errors = {},
  disabled = false,
}) => {
  const itemNumber = index + 1;

  const handleFieldChange = (field, value) => {
    onChange(index, field, value);
  };

  return (
    <div className="item-card" id={`rfq-item-row-${index}`}>
      <div className="item-header">
        <span className="item-number">
          <Package size={15} />
          <span>Item #{itemNumber}</span>
        </span>
        <button
          type="button"
          className="btn-remove-item"
          onClick={() => onRemove(index)}
          disabled={!canRemove || disabled}
          id={`btn-remove-item-${index}`}
          aria-label={`Remove Item ${itemNumber}`}
        >
          <Trash2 size={13} />
          <span>Remove</span>
        </button>
      </div>

      <div className="item-fields-grid">
        {/* Item Name */}
        <div className="form-group">
          <label htmlFor={`item-name-${index}`} className="form-label">
            Name <span className="required">*</span>
          </label>
          <input
            id={`item-name-${index}`}
            type="text"
            className={`form-control ${errors.name ? 'error' : ''}`}
            placeholder="e.g. Steel Bearing"
            value={item.name}
            onChange={(e) => handleFieldChange('name', e.target.value)}
            disabled={disabled}
          />
          {errors.name && (
            <span className="error-text">
              <AlertCircle size={12} />
              {errors.name}
            </span>
          )}
        </div>

        {/* Item Description */}
        <div className="form-group">
          <label htmlFor={`item-desc-${index}`} className="form-label">
            Description
          </label>
          <input
            id={`item-desc-${index}`}
            type="text"
            className="form-control"
            placeholder="e.g. Heavy duty industrial bearing (Optional)"
            value={item.description}
            onChange={(e) => handleFieldChange('description', e.target.value)}
            disabled={disabled}
          />
        </div>

        {/* Item Quantity */}
        <div className="form-group">
          <label htmlFor={`item-qty-${index}`} className="form-label">
            Quantity <span className="required">*</span>
          </label>
          <input
            id={`item-qty-${index}`}
            type="number"
            step="any"
            min="0.0001"
            className={`form-control ${errors.quantity ? 'error' : ''}`}
            placeholder="e.g. 100"
            value={item.quantity}
            onChange={(e) => handleFieldChange('quantity', e.target.value)}
            disabled={disabled}
          />
          {errors.quantity && (
            <span className="error-text">
              <AlertCircle size={12} />
              {errors.quantity}
            </span>
          )}
        </div>

        {/* Item Unit */}
        <div className="form-group">
          <label htmlFor={`item-unit-${index}`} className="form-label">
            Unit <span className="required">*</span>
          </label>
          <input
            id={`item-unit-${index}`}
            type="text"
            className={`form-control ${errors.unit ? 'error' : ''}`}
            placeholder="e.g. units"
            value={item.unit}
            onChange={(e) => handleFieldChange('unit', e.target.value)}
            disabled={disabled}
          />
          {errors.unit && (
            <span className="error-text">
              <AlertCircle size={12} />
              {errors.unit}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default RFQItemRow;
