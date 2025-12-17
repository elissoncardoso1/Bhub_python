'use client';

import React from 'react';

export default function BHubTest() {
  return (
    <div className="min-h-screen bg-bhub-light-gray p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <h1 className="font-display font-bold text-3xl text-bhub-navy-dark">
          Teste de Cores BHub
        </h1>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-bhub-dark-gray text-white p-4 rounded">Dark Gray</div>
          <div className="bg-bhub-teal-primary text-white p-4 rounded">Teal Primary</div>
          <div className="bg-bhub-navy-dark text-white p-4 rounded">Navy Dark</div>
          <div className="bg-bhub-red-accent text-white p-4 rounded">Red Accent</div>
          <div className="bg-bhub-light-gray text-bhub-navy-dark p-4 rounded">Light Gray</div>
          <div className="bg-bhub-teal-light text-bhub-navy-dark p-4 rounded">Teal Light</div>
          <div className="bg-bhub-navy-light text-bhub-navy-dark p-4 rounded">Navy Light</div>
          <div className="bg-bhub-yellow-primary text-bhub-navy-dark p-4 rounded">Yellow Primary</div>
        </div>
      </div>
    </div>
  );
}