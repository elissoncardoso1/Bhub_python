'use client';

import React from 'react';

export default function SimpleTest() {
  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Teste Simples
        </h1>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            Card Teste
          </h2>
          <p className="text-gray-600">
            Este é um teste simples para verificar se os elementos básicos estão renderizando.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-blue-500 text-white p-4 rounded">Azul</div>
          <div className="bg-green-500 text-white p-4 rounded">Verde</div>
          <div className="bg-red-500 text-white p-4 rounded">Vermelho</div>
        </div>
      </div>
    </div>
  );
}