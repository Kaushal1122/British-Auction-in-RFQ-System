import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import RfqRanking from '../pages/RfqRanking';
import * as api from '../services/api';

// Mock the API module
vi.mock('../services/api', () => ({
  getRFQs: vi.fn(),
  getRFQRanking: vi.fn(),
}));

const mockRfqs = [
  {
    id: 'rfq-aaaa-1111',
    title: 'Industrial Component Procurement',
    baseline_price: 50000.0,
    currency: 'USD',
    status: 'PUBLISHED',
  },
  {
    id: 'rfq-bbbb-2222',
    title: 'Sensor Hardware Batch',
    baseline_price: 30000.0,
    currency: 'EUR',
    status: 'PUBLISHED',
  },
];

const mockRankingData = {
  rfq_id: 'rfq-aaaa-1111',
  rfq_title: 'Industrial Component Procurement',
  currency: 'USD',
  baseline_price: 50000.0,
  total_bids: 3,
  rankings: [
    {
      rank: 1,
      bid_id: 'bid-001',
      supplier_id: 'sup-beta',
      supplier_name: 'Supplier Beta',
      supplier_company: 'Beta Industrial Supply',
      amount: 45000.0,
      submitted_at: '2026-08-28T09:00:00Z',
      is_valid: true,
      supplier: {
        id: 'sup-beta',
        name: 'Supplier Beta',
        email: 'beta@industrial.com',
        company_name: 'Beta Industrial Supply',
      },
    },
    {
      rank: 2,
      bid_id: 'bid-002',
      supplier_id: 'sup-gamma',
      supplier_name: 'Supplier Gamma',
      supplier_company: 'Gamma Dynamics',
      amount: 47000.0,
      submitted_at: '2026-08-28T09:15:00Z',
      is_valid: true,
      supplier: {
        id: 'sup-gamma',
        name: 'Supplier Gamma',
        email: 'gamma@dynamics.com',
        company_name: 'Gamma Dynamics',
      },
    },
    {
      rank: 3,
      bid_id: 'bid-003',
      supplier_id: 'sup-alpha',
      supplier_name: 'Supplier Alpha',
      supplier_company: 'Alpha Tech Ltd',
      amount: 48000.0,
      submitted_at: '2026-08-28T08:45:00Z',
      is_valid: true,
      supplier: {
        id: 'sup-alpha',
        name: 'Supplier Alpha',
        email: 'alpha@alphatech.com',
        company_name: 'Alpha Tech Ltd',
      },
    },
  ],
};

const mockEmptyRankingData = {
  rfq_id: 'rfq-bbbb-2222',
  rfq_title: 'Sensor Hardware Batch',
  currency: 'EUR',
  baseline_price: 30000.0,
  total_bids: 0,
  rankings: [],
};

describe('RfqRanking Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getRFQs.mockResolvedValue(mockRfqs);
    api.getRFQRanking.mockImplementation(async (id) => {
      if (id === 'rfq-aaaa-1111') return mockRankingData;
      if (id === 'rfq-bbbb-2222') return mockEmptyRankingData;
      const error = new Error('RFQ not found');
      error.response = { status: 404, data: { detail: "RFQ with id 'non-existent' not found" } };
      throw error;
    });
  });

  const renderWithRouter = (initialRoute = '/rfqs/rfq-aaaa-1111/ranking') => {
    return render(
      <MemoryRouter
        initialEntries={[initialRoute]}
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <Routes>
          <Route path="/rfqs/:rfqId/ranking" element={<RfqRanking />} />
          <Route path="/ranking" element={<RfqRanking />} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('renders Bid Ranking page with header and context cards', async () => {
    renderWithRouter();

    expect(screen.getByRole('heading', { name: /bid ranking/i })).toBeInTheDocument();
    expect(screen.getByText(/real-time competitive bid hierarchy/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Industrial Component Procurement')).toBeInTheDocument();
      expect(screen.getByText('Total Valid Bids')).toBeInTheDocument();
    });
  });

  it('calls ranking API with the correct RFQ ID from route params', async () => {
    renderWithRouter('/rfqs/rfq-aaaa-1111/ranking');

    await waitFor(() => {
      expect(api.getRFQRanking).toHaveBeenCalledWith('rfq-aaaa-1111');
    });
  });

  it('displays ranked bids in correct numerical order (lowest bid is Rank 1)', async () => {
    renderWithRouter('/rfqs/rfq-aaaa-1111/ranking');

    await waitFor(() => {
      expect(screen.getByText('Supplier Beta')).toBeInTheDocument();
      expect(screen.getByText('Supplier Gamma')).toBeInTheDocument();
      expect(screen.getByText('Supplier Alpha')).toBeInTheDocument();
    });

    // Verify Rank numbers
    expect(document.getElementById('rank-badge-1')).toHaveTextContent('1');
    expect(document.getElementById('rank-badge-2')).toHaveTextContent('2');
    expect(document.getElementById('rank-badge-3')).toHaveTextContent('3');

    // Verify Rank 1 is Supplier Beta ($45,000)
    const rank1Row = document.getElementById('ranking-row-1');
    expect(rank1Row).toBeInTheDocument();
    expect(rank1Row).toHaveTextContent('Supplier Beta');
    expect(rank1Row).toHaveTextContent('$45,000.00');

    // Verify Rank 2 is Supplier Gamma ($47,000)
    const rank2Row = document.getElementById('ranking-row-2');
    expect(rank2Row).toBeInTheDocument();
    expect(rank2Row).toHaveTextContent('Supplier Gamma');
    expect(rank2Row).toHaveTextContent('$47,000.00');

    // Verify Rank 3 is Supplier Alpha ($48,000)
    const rank3Row = document.getElementById('ranking-row-3');
    expect(rank3Row).toBeInTheDocument();
    expect(rank3Row).toHaveTextContent('Supplier Alpha');
    expect(rank3Row).toHaveTextContent('$48,000.00');
  });

  it('highlights Rank 1 with neutral Best Current Bid badge (no winner language)', async () => {
    renderWithRouter('/rfqs/rfq-aaaa-1111/ranking');

    await waitFor(() => {
      const bestBidTag = document.getElementById('tag-best-current-bid');
      expect(bestBidTag).toBeInTheDocument();
      expect(bestBidTag).toHaveTextContent('#1 Best Current Bid');
    });

    // Confirm no winner terminology
    expect(screen.queryByText(/winner/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/auction won/i)).not.toBeInTheDocument();
  });

  it('displays supplier company name and identifier correctly', async () => {
    renderWithRouter('/rfqs/rfq-aaaa-1111/ranking');

    await waitFor(() => {
      expect(screen.getByText('Beta Industrial Supply')).toBeInTheDocument();
      expect(screen.getByText('Gamma Dynamics')).toBeInTheDocument();
      expect(screen.getByText('Alpha Tech Ltd')).toBeInTheDocument();
    });
  });

  it('formats bid amounts with RFQ currency', async () => {
    renderWithRouter('/rfqs/rfq-aaaa-1111/ranking');

    await waitFor(() => {
      expect(document.getElementById('bid-amount-1')).toHaveTextContent('$45,000.00');
      expect(document.getElementById('bid-amount-2')).toHaveTextContent('$47,000.00');
      expect(document.getElementById('bid-amount-3')).toHaveTextContent('$48,000.00');
    });
  });


  it('displays empty state message when no bids have been submitted', async () => {
    renderWithRouter('/rfqs/rfq-bbbb-2222/ranking');

    await waitFor(() => {
      expect(screen.getByText('No bids have been submitted yet.')).toBeInTheDocument();
    });

    expect(screen.getByRole('link', { name: /submit initial bid/i })).toBeInTheDocument();
    expect(document.getElementById('table-bid-rankings')).not.toBeInTheDocument();
  });

  it('displays clean error message when RFQ is not found (404)', async () => {
    renderWithRouter('/rfqs/non-existent-uuid/ranking');

    await waitFor(() => {
      expect(screen.getByText('RFQ not found.')).toBeInTheDocument();
    });

    expect(screen.queryByText(/AxiosError/i)).not.toBeInTheDocument();
  });

  it('displays clean error message on generic backend server error', async () => {
    api.getRFQRanking.mockRejectedValueOnce(new Error('Network Error'));

    renderWithRouter('/rfqs/rfq-aaaa-1111/ranking');

    await waitFor(() => {
      expect(screen.getByText('Unable to load bid rankings. Please try again.')).toBeInTheDocument();
    });
  });

  it('allows changing selected RFQ from dropdown selector', async () => {
    renderWithRouter('/ranking');

    await waitFor(() => {
      expect(screen.getByLabelText(/selected rfq/i)).toBeInTheDocument();
    });

    const selectEl = screen.getByLabelText(/selected rfq/i);
    fireEvent.change(selectEl, { target: { value: 'rfq-bbbb-2222' } });

    await waitFor(() => {
      expect(api.getRFQRanking).toHaveBeenCalledWith('rfq-bbbb-2222');
    });
  });

  it('supports manual refresh button to reload ranking data', async () => {
    renderWithRouter('/rfqs/rfq-aaaa-1111/ranking');

    await waitFor(() => {
      expect(screen.getByText('Supplier Beta')).toBeInTheDocument();
    });

    const refreshBtn = document.getElementById('btn-refresh-ranking');
    expect(refreshBtn).toBeInTheDocument();

    fireEvent.click(refreshBtn);

    await waitFor(() => {
      expect(api.getRFQRanking).toHaveBeenCalledTimes(2);
    });
  });
});
