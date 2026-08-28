import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import { Gavel, LayoutDashboard, PlusCircle, Layers, TrendingDown } from 'lucide-react';
import HealthBadge from './HealthBadge';

export const Navbar = () => {
  return (
    <header className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="nav-brand" id="nav-brand-logo">
          <div className="brand-icon">
            <Gavel size={20} />
          </div>
          <span>British Auction RFQ</span>
        </Link>

        <nav>
          <ul className="nav-links">
            <li>
              <NavLink
                to="/"
                end
                className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}
                id="nav-link-dashboard"
              >
                <LayoutDashboard size={18} />
                <span>Dashboard</span>
              </NavLink>
            </li>
            <li>
              <NavLink
                to="/rfqs/create"
                className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}
                id="nav-link-create-rfq"
              >
                <PlusCircle size={18} />
                <span>Create RFQ</span>
              </NavLink>
            </li>
            <li>
              <NavLink
                to="/submit-bid"
                className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}
                id="nav-link-submit-bid"
              >
                <Gavel size={18} />
                <span>Submit Bid</span>
              </NavLink>
            </li>
            <li>
              <NavLink
                to="/ranking"
                className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}
                id="nav-link-ranking"
              >
                <TrendingDown size={18} />
                <span>Bid Ranking</span>
              </NavLink>
            </li>
            <li>
              <NavLink
                to="/auctions"
                className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}
                id="nav-link-auctions"
              >
                <Layers size={18} />
                <span>Auctions</span>
              </NavLink>
            </li>
          </ul>
        </nav>


        <div className="nav-actions">
          <HealthBadge />
        </div>
      </div>
    </header>
  );
};

export default Navbar;
