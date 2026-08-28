import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  TrendingDown,
  FileText,
  DollarSign,
  AlertCircle,
  RefreshCw,
  Award,
  Layers,
  ArrowLeft,
  Building,
  Calendar,
  Gavel,
  PlusCircle,
} from 'lucide-react';
import { getRFQRanking, getRFQs } from '../services/api';

export const RfqRanking = () => {
  const { rfqId: paramRfqId } = useParams();
  const navigate = useNavigate();

  // State
  const [rfqList, setRfqList] = useState([]);
  const [loadingRfqList, setLoadingRfqList] = useState(false);
  const [selectedRfqId, setSelectedRfqId] = useState(paramRfqId || '');
  const [rankingData, setRankingData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Sync route param with state
  useEffect(() => {
    if (paramRfqId) {
      setSelectedRfqId(paramRfqId);
    }
  }, [paramRfqId]);

  // Load RFQ list for the dropdown selector
  useEffect(() => {
    let isMounted = true;
    setLoadingRfqList(true);
    getRFQs({ limit: 100 })
      .then((data) => {
        if (isMounted) {
          setRfqList(data || []);
          setLoadingRfqList(false);
          // If no specific RFQ ID is selected yet, default to the first one if available
          if (!paramRfqId && !selectedRfqId && data && data.length > 0) {
            setSelectedRfqId(data[0].id);
          }
        }
      })
      .catch(() => {
        if (isMounted) {
          setLoadingRfqList(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, [paramRfqId]);

  // Fetch rankings whenever selectedRfqId changes
  const fetchRankings = async (rfqId, isManualRefresh = false) => {
    if (!rfqId) {
      setRankingData(null);
      return;
    }

    if (isManualRefresh) {
      setIsRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const data = await getRFQRanking(rfqId);
      setRankingData(data);
    } catch (err) {
      if (err.response?.status === 404) {
        setError('RFQ not found.');
      } else if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        setError(typeof detail === 'string' ? detail : 'Unable to load bid rankings. Please try again.');
      } else {
        setError('Unable to load bid rankings. Please try again.');
      }
      setRankingData(null);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    if (selectedRfqId) {
      fetchRankings(selectedRfqId);
    }
  }, [selectedRfqId]);

  const handleRfqSelectChange = (e) => {
    const newId = e.target.value;
    setSelectedRfqId(newId);
    if (newId) {
      navigate(`/rfqs/${newId}/ranking`, { replace: true });
    }
  };

  const handleManualRefresh = () => {
    if (selectedRfqId) {
      fetchRankings(selectedRfqId, true);
    }
  };

  // Helper for formatting currency amounts
  const formatCurrency = (amount, currency = 'USD') => {
    if (amount === null || amount === undefined) return '—';
    const num = parseFloat(amount);
    if (isNaN(num)) return `${amount} ${currency}`;
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency.length === 3 ? currency : 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);
  };

  return (
    <div className="page-container" id="page-rfq-ranking">
      {/* Page Header */}
      <div className="page-header" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h1 className="page-title" id="ranking-page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <TrendingDown size={28} color="#6366f1" />
              <span>Bid Ranking</span>
            </h1>
            <p className="page-subtitle">
              Real-time competitive bid hierarchy ranked from lowest to highest submitted quote.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            {selectedRfqId && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleManualRefresh}
                disabled={loading || isRefreshing}
                id="btn-refresh-ranking"
                title="Refresh rankings"
              >
                <RefreshCw size={16} className={isRefreshing ? 'spinner' : ''} />
                <span>{isRefreshing ? 'Refreshing...' : 'Refresh'}</span>
              </button>
            )}

            <Link
              to={selectedRfqId ? `/submit-bid?rfq_id=${selectedRfqId}` : '/submit-bid'}
              className="btn btn-primary"
              id="btn-goto-submit-bid-from-ranking"
            >
              <Gavel size={16} />
              <span>Submit Bid</span>
            </Link>
          </div>
        </div>
      </div>

      {/* RFQ Selector Section */}
      <div className="form-section" style={{ marginBottom: '1.5rem', padding: '1rem 1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1, minWidth: '280px' }}>
            <FileText size={18} color="#6366f1" />
            <label htmlFor="select-ranking-rfq" style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              Selected RFQ:
            </label>
            <select
              id="select-ranking-rfq"
              className="form-control"
              value={selectedRfqId}
              onChange={handleRfqSelectChange}
              disabled={loadingRfqList}
              style={{ flex: 1, minWidth: '240px' }}
            >
              <option value="">-- Choose an RFQ --</option>
              {rfqList.map((rfq) => (
                <option key={rfq.id} value={rfq.id}>
                  {rfq.title} ({rfq.currency}) — Baseline: {rfq.baseline_price}
                </option>
              ))}
            </select>
          </div>

          {loadingRfqList && (
            <span className="helper-text" style={{ margin: 0 }}>
              Loading RFQs...
            </span>
          )}
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="alert alert-error" role="alert" id="ranking-error-alert" style={{ marginBottom: '1.5rem' }}>
          <AlertCircle size={20} className="alert-icon" />
          <div className="alert-content">
            <div className="alert-title">Unable to Display Bid Ranking</div>
            <div id="ranking-error-message">{error}</div>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && !error && (
        <div className="empty-ranking-box" id="ranking-loading-state">
          <RefreshCw size={36} className="spinner" color="#6366f1" />
          <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            Loading bid rankings...
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Querying active bids and computing deterministic price rankings.
          </p>
        </div>
      )}

      {/* Ranking Content (when data is loaded) */}
      {!loading && !error && rankingData && (
        <div id="ranking-content-area">
          {/* RFQ Context & Summary Header */}
          <div className="ranking-summary-grid" id="ranking-summary-cards">
            <div className="ranking-stat-card">
              <span className="ranking-stat-label">RFQ Title</span>
              <span className="ranking-stat-value" id="rfq-summary-title" style={{ fontSize: '1.15rem' }}>
                {rankingData.rfq_title}
              </span>
            </div>

            <div className="ranking-stat-card">
              <span className="ranking-stat-label">Baseline Ceiling</span>
              <span className="ranking-stat-value" id="rfq-summary-baseline" style={{ color: '#38bdf8' }}>
                {formatCurrency(rankingData.baseline_price, rankingData.currency)}
              </span>
            </div>

            <div className="ranking-stat-card">
              <span className="ranking-stat-label">Total Valid Bids</span>
              <span className="ranking-stat-value" id="rfq-summary-total-bids" style={{ color: '#a5b4fc' }}>
                {rankingData.total_bids}
              </span>
            </div>

            <div className="ranking-stat-card">
              <span className="ranking-stat-label">Best Current Bid</span>
              <span
                className="ranking-stat-value"
                id="rfq-summary-best-bid"
                style={{ color: rankingData.rankings.length > 0 ? '#34d399' : 'var(--text-muted)' }}
              >
                {rankingData.rankings.length > 0
                  ? formatCurrency(rankingData.rankings[0].amount, rankingData.currency)
                  : 'None'}
              </span>
            </div>
          </div>

          {/* Empty State: No bids submitted */}
          {rankingData.rankings.length === 0 ? (
            <div className="empty-ranking-box" id="ranking-empty-state">
              <div className="empty-ranking-icon">
                <Gavel size={32} />
              </div>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                No bids have been submitted yet.
              </h3>
              <p style={{ color: 'var(--text-secondary)', maxWidth: '480px', fontSize: '0.95rem' }}>
                Suppliers have not placed any quotation bids for this RFQ yet. Be the first supplier to submit a quotation.
              </p>
              <Link
                to={`/submit-bid?rfq_id=${rankingData.rfq_id}`}
                className="btn btn-primary"
                id="btn-submit-first-bid"
                style={{ marginTop: '0.5rem' }}
              >
                <PlusCircle size={16} />
                <span>Submit Initial Bid</span>
              </Link>
            </div>
          ) : (
            /* Ranked Bids Table */
            <div className="ranking-table-container" id="ranking-table-container">
              <table className="ranking-table" id="table-bid-rankings">
                <thead>
                  <tr>
                    <th style={{ width: '90px', textAlign: 'center' }}>Rank</th>
                    <th>Supplier</th>
                    <th style={{ textAlign: 'right' }}>Bid Amount</th>
                    <th>Submitted At</th>
                    <th style={{ textAlign: 'center' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rankingData.rankings.map((bid, index) => {
                    const isRank1 = bid.rank === 1;
                    const rankClass =
                      bid.rank === 1
                        ? 'rank-pill rank-pill-1'
                        : bid.rank === 2
                        ? 'rank-pill rank-pill-2'
                        : bid.rank === 3
                        ? 'rank-pill rank-pill-3'
                        : 'rank-pill';

                    return (
                      <tr
                        key={bid.bid_id}
                        className={isRank1 ? 'rank-1-row' : ''}
                        id={`ranking-row-${bid.rank}`}
                      >
                        {/* Rank Position */}
                        <td style={{ textAlign: 'center' }}>
                          <span className={rankClass} id={`rank-badge-${bid.rank}`}>
                            {bid.rank}
                          </span>
                        </td>

                        {/* Supplier Information */}
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '0.35rem' }}>
                            <span
                              style={{ fontWeight: 600, color: 'var(--text-primary)' }}
                              id={`supplier-name-${bid.rank}`}
                            >
                              {bid.supplier_name || (bid.supplier ? bid.supplier.name : bid.supplier_id)}
                            </span>

                            {/* Rank 1 Best Bid Badge (Neutral Wording) */}
                            {isRank1 && (
                              <span className="best-bid-tag" id="tag-best-current-bid">
                                <Award size={12} />
                                <span>#1 Best Current Bid</span>
                              </span>
                            )}
                          </div>

                          {(bid.supplier_company || bid.supplier?.company_name) && (
                            <div
                              style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.3rem', marginTop: '0.2rem' }}
                              id={`supplier-company-${bid.rank}`}
                            >
                              <Building size={12} />
                              <span>{bid.supplier_company || bid.supplier?.company_name}</span>
                            </div>
                          )}

                          {bid.carrier_name && (
                            <div style={{ fontSize: '0.78rem', color: '#38bdf8', marginTop: '0.15rem' }}>
                              Carrier: <strong>{bid.carrier_name}</strong>
                              {bid.transit_time ? ` (${bid.transit_time})` : ''}
                            </div>
                          )}

                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace', marginTop: '0.15rem' }}>
                            ID: {bid.supplier_id}
                          </div>
                        </td>

                        {/* Bid Amount */}
                        <td style={{ textAlign: 'right' }}>
                          <span
                            className="bid-amount-display"
                            id={`bid-amount-${bid.rank}`}
                            style={{ color: isRank1 ? '#34d399' : 'var(--text-primary)' }}
                          >
                            {formatCurrency(bid.amount, rankingData.currency)}
                          </span>
                        </td>

                        {/* Submission Timestamp */}
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                            <Calendar size={13} />
                            <span id={`bid-timestamp-${bid.rank}`}>
                              {new Date(bid.submitted_at).toLocaleString()}
                            </span>
                          </div>
                        </td>

                        {/* Validity Status */}
                        <td style={{ textAlign: 'center' }}>
                          <span className="badge badge-success" id={`bid-status-${bid.rank}`}>
                            Valid
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default RfqRanking;
