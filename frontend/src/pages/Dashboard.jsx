import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { PlusCircle, Layers, Activity, ShieldCheck, ArrowRight, Gavel, TrendingDown } from 'lucide-react';
import { checkHealth } from '../services/api';

export const Dashboard = () => {
  const [healthStatus, setHealthStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkHealth()
      .then((data) => {
        setHealthStatus(data);
        setLoading(false);
      })
      .catch(() => {
        setHealthStatus({ status: 'offline' });
        setLoading(false);
      });
  }, []);

  return (
    <div className="page-container" id="page-dashboard">
      <div className="page-header">
        <h1 className="page-title">British Auction RFQ System</h1>
        <p className="page-subtitle">
          Procurement & dynamic bidding platform for buyer Requests for Quotation (RFQ) and multi-round supplier auctions.
        </p>
      </div>

      <div className="card-grid">
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <PlusCircle size={22} color="#6366f1" />
              <span>Create RFQ</span>
            </div>
          </div>
          <p className="card-desc">
            Define new procurement requirements, configure target pricing, and invite qualified suppliers to submit quotation bids.
          </p>
          <Link to="/rfqs/create" className="btn btn-primary" id="btn-goto-create-rfq">
            <span>New RFQ</span>
            <ArrowRight size={16} />
          </Link>
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <Gavel size={22} color="#8b5cf6" />
              <span>Submit Bid</span>
            </div>
          </div>
          <p className="card-desc">
            Submit a supplier quotation bid against an existing published RFQ with line item specification and price validation.
          </p>
          <Link to="/submit-bid" className="btn btn-primary" id="btn-goto-submit-bid">
            <span>Submit Bid</span>
            <ArrowRight size={16} />
          </Link>
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <TrendingDown size={22} color="#10b981" />
              <span>Bid Ranking</span>
            </div>
          </div>
          <p className="card-desc">
            Inspect real-time deterministic price rankings for RFQs, highlighting the best current supplier bids and competition tiers.
          </p>
          <Link to="/ranking" className="btn btn-primary" id="btn-goto-ranking">
            <span>View Rankings</span>
            <ArrowRight size={16} />
          </Link>
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <Layers size={22} color="#06b6d4" />
              <span>Live Auctions</span>
            </div>
            <span className="badge badge-info">Multi-Round</span>
          </div>
          <p className="card-desc">
            Monitor real-time British reverse auctions, ranking progressions, supplier bids, dynamic extensions, and closing events.
          </p>
          <Link to="/auctions" className="btn btn-secondary" id="btn-goto-auctions">
            <span>View Auctions</span>
            <ArrowRight size={16} />
          </Link>
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <Activity size={22} color="#10b981" />
              <span>Backend Status</span>
            </div>
            <span className={`badge ${healthStatus?.status === 'ok' ? 'badge-success' : 'badge-info'}`}>
              {loading ? 'Checking...' : healthStatus?.status === 'ok' ? 'Online' : 'Offline'}
            </span>
          </div>
          <p className="card-desc">
            FastAPI backend health and database connectivity probe endpoint (<code>GET /health</code>).
          </p>
          <div className="code-box">
            {loading ? 'Probing backend status...' : JSON.stringify(healthStatus, null, 2)}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

