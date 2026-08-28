import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import Dashboard from '../pages/Dashboard';
import CreateRfq from '../pages/CreateRfq';

describe('Core Application Route Pages', () => {
  const routerFuture = {
    v7_startTransition: true,
    v7_relativeSplatPath: true,
  };

  it('renders Dashboard overview page', () => {
    render(
      <MemoryRouter initialEntries={['/']} future={routerFuture}>
        <Dashboard />
      </MemoryRouter>
    );
    expect(screen.getByRole('heading', { name: /British Auction RFQ System/i })).toBeInTheDocument();
  });

  it('renders Create RFQ page', () => {
    render(
      <MemoryRouter initialEntries={['/rfqs/create']} future={routerFuture}>
        <CreateRfq />
      </MemoryRouter>
    );
    expect(screen.getByRole('heading', { name: /Create RFQ/i })).toBeInTheDocument();
    expect(screen.getByText(/1\. Buyer Information/i)).toBeInTheDocument();
  });
});
