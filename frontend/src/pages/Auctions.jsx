import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Gavel,
  ArrowRight,
  RefreshCw,
  Search,
  Filter,
  TrendingDown,
  Clock,
  ShieldAlert,
  AlertCircle,
  PlusCircle,
  Sparkles,
  Layers,
  Building,
} from 'lucide-react';
import { getAuctions } from '../services/api';

export const Auctions = () => {
  const [auctions, setAuctions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  const fetchAuctions = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getAuctions();
      setAuctions(data);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          'Failed to retrieve auctions from the server. Please check your backend connection.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuctions();
  }, []);

  const filteredAuctions = auctions.filter((auction) => {
    const matchesSearch =
      auction.rfq_title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      auction.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      auction.rfq_id.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus =
      statusFilter === 'ALL' ||
      auction.display_status?.toUpperCase() === statusFilter.toUpperCase() ||
      auction.status?.toUpperCase() === statusFilter.toUpperCase();

    return matchesSearch && matchesStatus;
  });

  const getStatusBadge = (displayStatus, rawStatus) => {
    const statusStr = (displayStatus || rawStatus || 'ACTIVE').toUpperCase();
    if (statusStr === 'FORCE CLOSED' || statusStr === 'FORCE_CLOSED') {
      return (
        <span className="badge badge-danger" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
          <ShieldAlert size={12} />
          Force Closed
        </span>
      );
    }
    if (statusStr === 'CLOSED') {
      return <span className="badge badge-secondary">Closed</span>;
    }
    if (statusStr === 'SCHEDULED') {
      return <span className="badge badge-info">Scheduled</span>;
    }
    if (statusStr === 'PAUSED') {
      return <span className="badge badge-warning">Paused</span>;
    }
    return (
      <span
        className="badge badge-success"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          boxShadow: '0 0 8px rgba(16, 185, 129, 0.3)',
        }}
      >
        <span
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: '#10b981',
            animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
          }}
        />
        Active
      </span>
    );
  };

  const formatDateTime = (dateStr) => {
    if (!dateStr) return 'Not configured';
    return new Date(dateStr).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getTriggerLabel = (trigger) => {
    switch (trigger) {
      case 'BID_RECEIVED':
        return 'Bid Received in Last X min';
      case 'ANY_RANK_CHANGE':
        return 'Any Rank Change in Last X min';
      case 'L1_RANK_CHANGE':
        return 'Lowest Bidder (L1) Change in Last X min';
      default:
        return trigger || 'Bid Received';
    }
  };

  return (
    <div className="page-container" id="page-auctions">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 className="page-title">British Auctions</h1>
          <p className="page-subtitle">
            Explore active, scheduled, and closed British Auctions across all published RFQs with live countdowns and dynamic extensions.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={fetchAuctions}
            disabled={loading}
            id="btn-refresh-auctions"
          >
            <RefreshCw size={16} className={loading ? 'spinner' : ''} />
            <span>Refresh</span>
          </button>
          <Link to="/rfqs/create" className="btn btn-primary" id="btn-create-rfq-auction">
            <PlusCircle size={16} />
            <span>Create RFQ</span>
          </Link>
        </div>
      </div>

      {/* Filter and Search Controls */}
      <div
        className="card"
        style={{
          marginBottom: '1.5rem',
          padding: '1rem 1.25rem',
          display: 'flex',
          gap: '1rem',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ position: 'relative', flex: '1 1 280px', maxWidth: '450px' }}>
          <Search
            size={16}
            style={{
              position: 'absolute',
              left: '12px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--text-secondary)',
            }}
          />
          <input
            type="text"
            className="form-control"
            placeholder="Search by RFQ title or auction ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            id="input-search-auctions"
            style={{ paddingLeft: '2.25rem' }}
          />
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Filter size={14} /> Status:
          </span>
          {['ALL', 'ACTIVE', 'CLOSED', 'FORCE CLOSED', 'SCHEDULED'].map((statusOption) => (
            <button
              key={statusOption}
              type="button"
              className={`btn ${statusFilter === statusOption ? 'btn-primary' : 'btn-secondary'}`}
              style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}
              onClick={() => setStatusFilter(statusOption)}
              id={`filter-status-${statusOption.toLowerCase().replace(/\s+/g, '-')}`}
            >
              {statusOption === 'ALL' ? 'All Auctions' : statusOption}
            </button>
          ))}
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="alert alert-error" role="alert" style={{ marginBottom: '1.5rem' }}>
          <AlertCircle size={18} className="alert-icon" />
          <div className="alert-content">
            <div className="alert-title">Error Loading Auctions</div>
            <div>{error}</div>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="loading-state" style={{ textAlign: 'center', padding: '3rem 0' }}>
          <RefreshCw size={32} className="spinner" style={{ color: 'var(--primary-color)', margin: '0 auto 1rem' }} />
          <p style={{ color: 'var(--text-secondary)' }}>Loading British Auctions from database...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filteredAuctions.length === 0 && (
        <div className="empty-state card" style={{ textAlign: 'center', padding: '3.5rem 1.5rem' }}>
          <Gavel size={48} style={{ color: 'var(--primary-color)', margin: '0 auto 1rem', opacity: 0.7 }} />
          <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '0.5rem' }}>
            {auctions.length === 0 ? 'No Auctions Created Yet' : 'No Auctions Matching Filter'}
          </h3>
          <p style={{ color: 'var(--text-secondary)', maxWidth: '460px', margin: '0 auto 1.5rem' }}>
            {auctions.length === 0
              ? 'Create a Request for Quotation (RFQ) with British Auction schedule parameters to launch your first auction room.'
              : 'Try clearing the search query or selecting a different status filter.'}
          </p>
          {auctions.length === 0 ? (
            <Link to="/rfqs/create" className="btn btn-primary">
              <PlusCircle size={16} />
              <span>Create RFQ & Launch Auction</span>
            </Link>
          ) : (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                setSearchTerm('');
                setStatusFilter('ALL');
              }}
            >
              Reset Filters
            </button>
          )}
        </div>
      )}

      {/* Auction Cards Grid */}
      {!loading && !error && filteredAuctions.length > 0 && (
        <div className="card-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))' }}>
          {filteredAuctions.map((auction) => (
            <div
              key={auction.id}
              className="card"
              id={`auction-card-${auction.id}`}
              style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                transition: 'transform 0.2s ease, border-color 0.2s ease',
              }}
            >
              <div>
                {/* Header */}
                <div className="card-header" style={{ marginBottom: '1rem' }}>
                  <div className="card-title" style={{ alignItems: 'flex-start' }}>
                    <Gavel size={20} color="#6366f1" style={{ marginTop: '2px', flexShrink: 0 }} />
                    <div>
                      <span style={{ fontSize: '1.1rem', fontWeight: 700, display: 'block', color: 'var(--text-primary)' }}>
                        {auction.rfq_title}
                      </span>
                      <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>
                        RFQ: {auction.rfq_id}
                      </span>
                    </div>
                  </div>
                  <div>{getStatusBadge(auction.display_status, auction.status)}</div>
                </div>

                {/* Lowest Bid & Baseline Price Banner */}
                <div
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    padding: '0.75rem 1rem',
                    marginBottom: '1rem',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Current Lowest Bid (L1)
                    </div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, color: auction.lowest_bid ? '#10b981' : 'var(--text-secondary)' }}>
                      {auction.lowest_bid ? (
                        <>
                          {auction.lowest_bid} <span style={{ fontSize: '0.85rem' }}>{auction.currency}</span>
                        </>
                      ) : (
                        <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>No bids yet</span>
                      )}
                    </div>
                    {auction.lowest_bidder_name && (
                      <div style={{ fontSize: '0.75rem', color: '#38bdf8' }}>
                        by {auction.lowest_bidder_name}
                      </div>
                    )}
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Ceiling / Baseline
                    </div>
                    <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {auction.baseline_price} {auction.currency}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      {auction.total_bids} total bid{auction.total_bids === 1 ? '' : 's'}
                    </div>
                  </div>
                </div>

                {/* Timers & Configuration Details */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.6rem', marginBottom: '1rem', fontSize: '0.85rem' }}>
                  <div style={{ backgroundColor: 'rgba(99, 102, 241, 0.05)', padding: '0.5rem 0.65rem', borderRadius: '6px' }}>
                    <span style={{ color: 'var(--text-secondary)', display: 'block', fontSize: '0.72rem' }}>
                      Current Close Time:
                    </span>
                    <strong style={{ color: '#a5b4fc', fontSize: '0.82rem' }}>
                      {formatDateTime(auction.bid_close_time)}
                    </strong>
                  </div>

                  <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.05)', padding: '0.5rem 0.65rem', borderRadius: '6px' }}>
                    <span style={{ color: 'var(--text-secondary)', display: 'block', fontSize: '0.72rem' }}>
                      Forced Close Time:
                    </span>
                    <strong style={{ color: '#fca5a5', fontSize: '0.82rem' }}>
                      {formatDateTime(auction.forced_bid_close_time)}
                    </strong>
                  </div>
                </div>

                {/* Extension Configuration Pill */}
                <div
                  style={{
                    fontSize: '0.75rem',
                    color: 'var(--text-secondary)',
                    backgroundColor: 'rgba(255, 255, 255, 0.02)',
                    padding: '0.4rem 0.65rem',
                    borderRadius: '6px',
                    marginBottom: '1.25rem',
                    borderLeft: '3px solid #6366f1',
                  }}
                >
                  <div>
                    <strong>Extension Rules:</strong> Window X = {auction.trigger_window_minutes}m, Duration Y = +{auction.extension_duration_minutes}m
                  </div>
                  <div style={{ color: '#94a3b8', marginTop: '2px' }}>
                    Trigger: {getTriggerLabel(auction.extension_trigger)}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
                <Link
                  to={`/auctions/${auction.id}`}
                  className="btn btn-primary"
                  id={`btn-view-auction-${auction.id}`}
                  style={{ flex: '1 1 140px', justifyContent: 'center' }}
                >
                  <span>Auction Details</span>
                  <ArrowRight size={15} />
                </Link>

                <Link
                  to={`/bids/submit?rfq_id=${auction.rfq_id}`}
                  className="btn btn-secondary"
                  id={`btn-bid-auction-${auction.id}`}
                  style={{ flex: '1 1 100px', justifyContent: 'center' }}
                >
                  <span>Place Bid</span>
                </Link>

                <Link
                  to={`/rfqs/${auction.rfq_id}/ranking`}
                  className="btn btn-secondary"
                  id={`btn-ranking-auction-${auction.id}`}
                  title="View Leaderboard"
                  style={{ padding: '0.5rem 0.75rem' }}
                >
                  <TrendingDown size={16} />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Auctions;
