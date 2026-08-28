import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import CreateRfq from './pages/CreateRfq';
import SubmitBid from './pages/SubmitBid';
import RfqRanking from './pages/RfqRanking';
import Auctions from './pages/Auctions';
import AuctionDetails from './pages/AuctionDetails';

export function App() {
  return (
    <BrowserRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <div className="app-container">
        <Navbar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/rfqs/create" element={<CreateRfq />} />
            <Route path="/submit-bid" element={<SubmitBid />} />
            <Route path="/bids/submit" element={<SubmitBid />} />
            <Route path="/bids/create" element={<SubmitBid />} />
            <Route path="/rfqs/:rfqId/ranking" element={<RfqRanking />} />
            <Route path="/ranking" element={<RfqRanking />} />
            <Route path="/rfqs/ranking" element={<RfqRanking />} />
            <Route path="/auctions" element={<Auctions />} />
            <Route path="/auctions/:id" element={<AuctionDetails />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <footer className="footer">
          <p>British Auction in RFQ System &copy; {new Date().getFullYear()} &bull; Final Step 10 Completed</p>
        </footer>
      </div>
    </BrowserRouter>
  );
}

export default App;

