import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Gavel,
  ArrowLeft,
  RefreshCw,
  TrendingDown,
  Clock,
  ShieldAlert,
  AlertCircle,
  PlusCircle,
  Truck,
  Building,
  User,
  Calendar,
  Layers,
  Activity,
  DollarSign,
  CheckCircle2,
  Sliders,
  History,
  Send,
} from 'lucide-react';
import { getAuctionById } from '../services/api';

export const AuctionDetails = () => {
  const { id } = useParams();
  const [auction, setAuction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('bids'); // 'bids' | 'activity' | 'specs'

  const fetchAuctionDetail = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getAuctionById(id);
      setAuction(data);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          'Failed to load auction details. Please check the auction ID or backend connection.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuctionDetail();
  }, [id]);

  const getStatusBadge = (displayStatus, rawStatus) => {
    const statusStr = (displayStatus || rawStatus || 'ACTIVE').toUpperCase();
    if (statusStr === 'FORCE CLOSED' || statusStr === 'FORCE_CLOSED') {
      return (
        <span className="badge badge-danger" id="badge-auction-status" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
          <ShieldAlert size={12} />
          Force Closed
        </span>
      );
    }
    if (statusStr === 'CLOSED') {
      return <span className="badge badge-secondary" id="badge-auction-status">Closed</span>;
    }
    if (statusStr === 'SCHEDULED') {
      return <span className="badge badge-info" id="badge-auction-status">Scheduled</span>;
    }
    if (statusStr === 'PAUSED') {
      return <span className="badge badge-warning" id="badge-auction-status">Paused</span>;
    }
    return (
      <span
        className="badge badge-success"
        id="badge-auction-status"
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
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getTriggerLabel = (trigger) => {
    switch (trigger) {
      case 'BID_RECEIVED':
        return 'Bid Received in Last X Minutes';
      case 'ANY_RANK_CHANGE':
        return 'Any Supplier Rank Change in Last X Minutes';
      case 'L1_RANK_CHANGE':
        return 'Lowest Bidder (L1) Rank Change in Last X Minutes';
      default:
        return trigger || 'Bid Received in Last X Minutes';
    }
  };

  const getRankBadgeClass = (rank) => {
    if (rank === 1) return 'badge-success';
    if (rank === 2) return 'badge-info';
    if (rank === 3) return 'badge-warning';
    return 'badge-secondary';
  };

  return (
    <div className="page-container" id="page-auction-details">
      {/* Header Navigation */}
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <Link
            to="/auctions"
            className="btn btn-secondary"
            id="btn-back-to-auctions"
            style={{ width: 'fit-content', marginBottom: '0.75rem', padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}
          >
            <ArrowLeft size={15} />
            <span>Back to Auctions</span>
          </Link>
          <h1 className="page-title" id="auction-details-title">
            {auction ? auction.rfq_title : 'Auction Details'}
          </h1>
          <p className="page-subtitle" id="auction-details-subtitle">
            Live British Auction room and complete quotation details for RFQ ID: <strong>{auction?.rfq_id || id}</strong>
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={fetchAuctionDetail}
            disabled={loading}
            id="btn-refresh-auction-details"
          >
            <RefreshCw size={16} className={loading ? 'spinner' : ''} />
            <span>Refresh Room</span>
          </button>
          {auction && (
            <Link
              to={`/bids/submit?rfq_id=${auction.rfq_id}`}
              className="btn btn-primary"
              id="btn-place-bid-details"
            >
              <Send size={16} />
              <span>Submit Bid / Quote</span>
            </Link>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="alert alert-error" role="alert" style={{ marginBottom: '1.5rem' }}>
          <AlertCircle size={18} className="alert-icon" />
          <div className="alert-content">
            <div className="alert-title">Error Loading Auction</div>
            <div>{error}</div>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="loading-state" style={{ textAlign: 'center', padding: '4rem 0' }}>
          <RefreshCw size={36} className="spinner" style={{ color: 'var(--primary-color)', margin: '0 auto 1rem' }} />
          <p style={{ color: 'var(--text-secondary)' }}>Loading live British Auction room...</p>
        </div>
      )}

      {!loading && auction && (
        <>
          {/* Top Metric Cards */}
          <div
            className="card-grid"
            style={{
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '1rem',
              marginBottom: '1.5rem',
            }}
          >
            {/* Metric 1: Current Lowest Bid (L1) */}
            <div className="card" id="metric-lowest-bid" style={{ padding: '1.25rem' }}>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.35rem' }}>
                Current Lowest Bid (L1)
              </div>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: auction.lowest_bid ? '#10b981' : 'var(--text-secondary)' }} id="value-lowest-bid">
                {auction.lowest_bid ? (
                  <>
                    {auction.lowest_bid} <span style={{ fontSize: '1rem', fontWeight: 600 }}>{auction.currency}</span>
                  </>
                ) : (
                  'No Bids'
                )}
              </div>
              <div style={{ fontSize: '0.8rem', color: '#38bdf8', marginTop: '0.25rem' }} id="value-lowest-bidder">
                {auction.lowest_bidder_name ? `Leading Supplier: ${auction.lowest_bidder_name}` : 'Waiting for initial bid'}
              </div>
            </div>

            {/* Metric 2: Current Bid Close Time */}
            <div className="card" id="metric-close-time" style={{ padding: '1.25rem' }}>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.35rem' }}>
                Current Bid Close Time
              </div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#a5b4fc' }} id="value-bid-close-time">
                {formatDateTime(auction.bid_close_time)}
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                Dynamic clock (extends on late activity)
              </div>
            </div>

            {/* Metric 3: Forced Close Time */}
            <div className="card" id="metric-forced-close" style={{ padding: '1.25rem' }}>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.35rem' }}>
                Forced Close Time (Hard Cap)
              </div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fca5a5' }} id="value-forced-close-time">
                {formatDateTime(auction.forced_bid_close_time)}
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                Extensions cannot exceed this boundary
              </div>
            </div>

            {/* Metric 4: Auction Status */}
            <div className="card" id="metric-status" style={{ padding: '1.25rem' }}>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.35rem' }}>
                Auction Lifecycle Status
              </div>
              <div style={{ marginTop: '0.35rem' }}>
                {getStatusBadge(auction.display_status, auction.status)}
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
                Baseline: <strong>{auction.baseline_price} {auction.currency}</strong>
              </div>
            </div>
          </div>

          {/* British Auction Configuration Panel */}
          <div
            className="card"
            id="panel-auction-config"
            style={{
              marginBottom: '1.5rem',
              padding: '1.25rem 1.5rem',
              borderLeft: '4px solid #6366f1',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <Sliders size={18} color="#6366f1" />
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                British Auction Configuration Parameters
              </h3>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                gap: '1rem',
                fontSize: '0.9rem',
              }}
            >
              <div style={{ backgroundColor: 'rgba(255, 255, 255, 0.02)', padding: '0.75rem', borderRadius: '6px' }}>
                <span style={{ color: 'var(--text-secondary)', display: 'block', fontSize: '0.8rem' }}>
                  Trigger Monitoring Window (X):
                </span>
                <strong style={{ color: 'var(--text-primary)', fontSize: '1.05rem' }} id="value-trigger-window">
                  {auction.trigger_window_minutes} Minutes
                </strong>
                <span style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '0.75rem', marginTop: '2px' }}>
                  Activity monitored within [Close - {auction.trigger_window_minutes}m, Close]
                </span>
              </div>

              <div style={{ backgroundColor: 'rgba(255, 255, 255, 0.02)', padding: '0.75rem', borderRadius: '6px' }}>
                <span style={{ color: 'var(--text-secondary)', display: 'block', fontSize: '0.8rem' }}>
                  Extension Duration (Y):
                </span>
                <strong style={{ color: 'var(--text-primary)', fontSize: '1.05rem' }} id="value-extension-duration">
                  +{auction.extension_duration_minutes} Minutes
                </strong>
                <span style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '0.75rem', marginTop: '2px' }}>
                  Added upon qualifying event (capped at Forced Close)
                </span>
              </div>

              <div style={{ backgroundColor: 'rgba(255, 255, 255, 0.02)', padding: '0.75rem', borderRadius: '6px' }}>
                <span style={{ color: 'var(--text-secondary)', display: 'block', fontSize: '0.8rem' }}>
                  Configured Extension Trigger:
                </span>
                <strong style={{ color: '#38bdf8', fontSize: '0.95rem' }} id="value-extension-trigger">
                  {getTriggerLabel(auction.extension_trigger)}
                </strong>
                <span style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '0.75rem', marginTop: '2px' }}>
                  Code: <code>{auction.extension_trigger}</code>
                </span>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div
            style={{
              display: 'flex',
              gap: '0.5rem',
              borderBottom: '1px solid var(--border-color)',
              marginBottom: '1.5rem',
            }}
          >
            <button
              type="button"
              className={`btn ${activeTab === 'bids' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ borderRadius: '6px 6px 0 0', borderBottom: 'none' }}
              onClick={() => setActiveTab('bids')}
              id="tab-supplier-bids"
            >
              <Gavel size={16} />
              <span>Supplier Bids & Ranking ({auction.bids.length})</span>
            </button>

            <button
              type="button"
              className={`btn ${activeTab === 'activity' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ borderRadius: '6px 6px 0 0', borderBottom: 'none' }}
              onClick={() => setActiveTab('activity')}
              id="tab-activity-logs"
            >
              <History size={16} />
              <span>Activity Log ({auction.activity_logs.length})</span>
            </button>

            <button
              type="button"
              className={`btn ${activeTab === 'specs' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ borderRadius: '6px 6px 0 0', borderBottom: 'none' }}
              onClick={() => setActiveTab('specs')}
              id="tab-rfq-specs"
            >
              <Layers size={16} />
              <span>RFQ Items & Specs ({auction.items.length})</span>
            </button>
          </div>

          {/* Tab 1: Supplier Bids & Ranking Table */}
          {activeTab === 'bids' && (
            <div className="card" id="panel-supplier-bids" style={{ padding: '1.5rem' }}>
              <div className="card-header" style={{ marginBottom: '1rem' }}>
                <div className="card-title">
                  <TrendingDown size={20} color="#10b981" />
                  <span>Supplier Bids & Ranking (Lowest Bid First)</span>
                </div>
                <span className="badge badge-info">{auction.bids.length} Bid{auction.bids.length === 1 ? '' : 's'} Submitted</span>
              </div>

              {auction.bids.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
                  <Gavel size={40} style={{ color: 'var(--text-secondary)', margin: '0 auto 1rem', opacity: 0.5 }} />
                  <p style={{ color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
                    No supplier bids have been submitted for this auction yet.
                  </p>
                  <Link to={`/bids/submit?rfq_id=${auction.rfq_id}`} className="btn btn-primary">
                    <Send size={15} />
                    <span>Submit First Bid</span>
                  </Link>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                        <th style={{ padding: '0.75rem' }}>Rank</th>
                        <th style={{ padding: '0.75rem' }}>Supplier</th>
                        <th style={{ padding: '0.75rem' }}>Bid Amount</th>
                        <th style={{ padding: '0.75rem' }}>Submitted At</th>
                        <th style={{ padding: '0.75rem' }}>Quote Breakdown & Logistics</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auction.bids.map((bid) => (
                        <tr
                          key={bid.bid_id}
                          id={`bid-row-${bid.rank}`}
                          style={{
                            borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                            backgroundColor: bid.rank === 1 ? 'rgba(16, 185, 129, 0.04)' : 'transparent',
                          }}
                        >
                          {/* Rank */}
                          <td style={{ padding: '0.85rem 0.75rem' }}>
                            <span
                              className={`badge ${getRankBadgeClass(bid.rank)}`}
                              id={`rank-badge-${bid.rank}`}
                              style={{ fontWeight: 800, fontSize: '0.85rem', padding: '0.35rem 0.6rem' }}
                            >
                              L{bid.rank}
                            </span>
                          </td>

                          {/* Supplier */}
                          <td style={{ padding: '0.85rem 0.75rem' }}>
                            <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                              {bid.supplier_name || 'Unknown Supplier'}
                            </div>
                            {bid.supplier_company && (
                              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                {bid.supplier_company}
                              </div>
                            )}
                          </td>

                          {/* Bid Amount */}
                          <td style={{ padding: '0.85rem 0.75rem' }}>
                            <strong
                              style={{
                                color: bid.rank === 1 ? '#10b981' : 'var(--text-primary)',
                                fontSize: '1.1rem',
                              }}
                            >
                              {bid.amount} {auction.currency}
                            </strong>
                          </td>

                          {/* Submitted Timestamp */}
                          <td style={{ padding: '0.85rem 0.75rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                            {formatDateTime(bid.submitted_at)}
                          </td>

                          {/* Quote Breakdown Details */}
                          <td style={{ padding: '0.85rem 0.75rem', fontSize: '0.82rem' }}>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                              {bid.carrier_name && (
                                <div>
                                  <span style={{ color: 'var(--text-secondary)' }}>Carrier:</span>{' '}
                                  <strong style={{ color: '#38bdf8' }}>{bid.carrier_name}</strong>
                                </div>
                              )}
                              {bid.freight_charges !== null && bid.freight_charges !== undefined && (
                                <div>
                                  <span style={{ color: 'var(--text-secondary)' }}>Freight:</span>{' '}
                                  <span>{bid.freight_charges} {auction.currency}</span>
                                </div>
                              )}
                              {bid.origin_charges !== null && bid.origin_charges !== undefined && (
                                <div>
                                  <span style={{ color: 'var(--text-secondary)' }}>Origin:</span>{' '}
                                  <span>{bid.origin_charges} {auction.currency}</span>
                                </div>
                              )}
                              {bid.destination_charges !== null && bid.destination_charges !== undefined && (
                                <div>
                                  <span style={{ color: 'var(--text-secondary)' }}>Destination:</span>{' '}
                                  <span>{bid.destination_charges} {auction.currency}</span>
                                </div>
                              )}
                              {bid.transit_time && (
                                <div>
                                  <span style={{ color: 'var(--text-secondary)' }}>Transit:</span>{' '}
                                  <span>{bid.transit_time}</span>
                                </div>
                              )}
                              {bid.validity_of_quote && (
                                <div>
                                  <span style={{ color: 'var(--text-secondary)' }}>Validity:</span>{' '}
                                  <span>{bid.validity_of_quote}</span>
                                </div>
                              )}
                              {!bid.carrier_name &&
                                bid.freight_charges === null &&
                                bid.origin_charges === null &&
                                bid.destination_charges === null &&
                                !bid.transit_time &&
                                !bid.validity_of_quote && (
                                  <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                                    Standard quote
                                  </span>
                                )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Activity Log Timeline */}
          {activeTab === 'activity' && (
            <div className="card" id="panel-activity-log" style={{ padding: '1.5rem' }}>
              <div className="card-header" style={{ marginBottom: '1rem' }}>
                <div className="card-title">
                  <Activity size={20} color="#a5b4fc" />
                  <span>Auction Activity & Extension Timeline</span>
                </div>
                <span className="badge badge-info">{auction.activity_logs.length} Event{auction.activity_logs.length === 1 ? '' : 's'}</span>
              </div>

              {auction.activity_logs.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '2rem' }}>
                  No activity events recorded yet.
                </p>
              ) : (
                <div className="timeline" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {auction.activity_logs.map((log) => {
                    const isExtension = log.event_type === 'AUCTION_EXTENDED';
                    const isBid = log.event_type === 'BID_SUBMITTED';

                    return (
                      <div
                        key={log.id}
                        id={`activity-event-${log.id}`}
                        style={{
                          backgroundColor: isExtension
                            ? 'rgba(99, 102, 241, 0.08)'
                            : isBid
                            ? 'rgba(16, 185, 129, 0.04)'
                            : 'rgba(255, 255, 255, 0.02)',
                          border: `1px solid ${
                            isExtension
                              ? 'rgba(99, 102, 241, 0.3)'
                              : isBid
                              ? 'rgba(16, 185, 129, 0.2)'
                              : 'var(--border-color)'
                          }`,
                          borderRadius: '8px',
                          padding: '1rem',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span
                              className={`badge ${
                                isExtension ? 'badge-primary' : isBid ? 'badge-success' : 'badge-secondary'
                              }`}
                              style={{ fontSize: '0.75rem', textTransform: 'uppercase' }}
                            >
                              {log.event_type.replace(/_/g, ' ')}
                            </span>
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                              Actor: <strong>{log.actor_type}</strong>
                            </span>
                          </div>

                          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                            {formatDateTime(log.created_at)}
                          </div>
                        </div>

                        <p style={{ color: 'var(--text-primary)', margin: '0.35rem 0', fontWeight: 500 }}>
                          {log.message}
                        </p>

                        {/* Extension Reason & Detailed Metadata */}
                        {log.metadata_json && Object.keys(log.metadata_json).length > 0 && (
                          <div
                            style={{
                              marginTop: '0.5rem',
                              padding: '0.5rem 0.75rem',
                              backgroundColor: 'rgba(0, 0, 0, 0.2)',
                              borderRadius: '6px',
                              fontSize: '0.8rem',
                              color: 'var(--text-secondary)',
                            }}
                          >
                            {log.metadata_json.reason && (
                              <div style={{ color: '#38bdf8', marginBottom: '4px' }}>
                                <strong>Trigger Reason:</strong> {log.metadata_json.reason}
                              </div>
                            )}
                            {log.metadata_json.previous_close_time && log.metadata_json.new_close_time && (
                              <div>
                                <strong>Extension:</strong>{' '}
                                {formatDateTime(log.metadata_json.previous_close_time)} &rarr;{' '}
                                <span style={{ color: '#10b981', fontWeight: 600 }}>
                                  {formatDateTime(log.metadata_json.new_close_time)}
                                </span>{' '}
                                (+{log.metadata_json.extension_duration_minutes}m)
                              </div>
                            )}
                            {log.metadata_json.carrier_name && (
                              <div>
                                <strong>Carrier:</strong> {log.metadata_json.carrier_name}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Tab 3: RFQ Specifications & Items */}
          {activeTab === 'specs' && (
            <div className="card" id="panel-rfq-specs" style={{ padding: '1.5rem' }}>
              <div className="card-header" style={{ marginBottom: '1rem' }}>
                <div className="card-title">
                  <Layers size={20} color="#6366f1" />
                  <span>RFQ Line Item Specifications</span>
                </div>
                <span className="badge badge-info">{auction.items.length} Item{auction.items.length === 1 ? '' : 's'}</span>
              </div>

              {auction.rfq_description && (
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
                  {auction.rfq_description}
                </p>
              )}

              <div className="card-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
                {auction.items.map((item) => (
                  <div
                    key={item.id}
                    className="card"
                    style={{ backgroundColor: 'rgba(255, 255, 255, 0.02)', padding: '1rem' }}
                  >
                    <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                      {item.name}
                    </div>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                      {item.description || 'No additional specifications provided.'}
                    </p>
                    <div style={{ fontSize: '0.85rem', color: '#38bdf8' }}>
                      <strong>Quantity Required:</strong> {item.quantity} {item.unit}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default AuctionDetails;
