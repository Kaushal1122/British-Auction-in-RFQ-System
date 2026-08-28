import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import App from '../App';

// Mock the API client
vi.mock('../services/api', () => ({
  checkHealth: vi.fn().mockResolvedValue({ status: 'ok' }),
  apiClient: {
    get: vi.fn().mockResolvedValue({ data: { status: 'ok' } }),
  },
}));

describe('British Auction RFQ App Router and Components', () => {
  it('renders navbar brand and navigation links', async () => {
    await act(async () => {
      render(<App />);
    });
    expect(screen.getByRole('link', { name: /British Auction RFQ/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^Dashboard$/i })).toBeInTheDocument();
    expect(document.getElementById('nav-link-create-rfq')).toBeInTheDocument();
    expect(document.getElementById('nav-link-submit-bid')).toBeInTheDocument();
    expect(document.getElementById('nav-link-ranking')).toBeInTheDocument();
    expect(document.getElementById('nav-link-auctions')).toBeInTheDocument();
  });


  it('renders Dashboard page by default', async () => {
    await act(async () => {
      render(<App />);
    });
    expect(screen.getByRole('heading', { name: /British Auction RFQ System/i })).toBeInTheDocument();
    expect(screen.getByText(/Procurement & dynamic bidding platform/i)).toBeInTheDocument();
  });
});
