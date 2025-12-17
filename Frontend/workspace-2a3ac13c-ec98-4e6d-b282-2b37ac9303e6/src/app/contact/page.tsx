'use client';

import React, { useState } from 'react';
import { Header } from '@/components/Layout/Header';
import { Footer } from '@/components/Layout/Footer';
import { MainLayout } from '@/components/Layout/MainLayout';
import { Button } from '@/components/Button/Button';
import { Icon } from '@/components/Icon/Icon';

export default function Contact() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: '',
    message: ''
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Form submitted:', formData);
    // Aqui você implementaria o envio do formulário
  };

  return (
    <MainLayout>
      <Header />
      
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="max-w-2xl mx-auto">
          <div className="text-center mb-12">
            <h1 className="font-display font-bold text-4xl text-bhub-navy-dark dark:text-white mb-4">
              Entre em Contato
            </h1>
            <p className="font-body font-light text-lg text-gray-600 dark:text-gray-400">
              Tem alguma dúvida, sugestão ou gostaria de colaborar conosco? 
              Adoraríamos ouvir de você!
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <h2 className="font-display font-bold text-xl text-bhub-navy-dark dark:text-white mb-6">
                Informações de Contato
              </h2>
              
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-bhub-teal-primary rounded-lg flex items-center justify-center">
                    <Icon name="mail" className="text-white" />
                  </div>
                  <div>
                    <p className="font-body font-medium text-gray-900 dark:text-white">
                      E-mail
                    </p>
                    <p className="font-body font-light text-sm text-gray-600 dark:text-gray-400">
                      contato@bhub.com.br
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-bhub-navy-dark rounded-lg flex items-center justify-center">
                    <Icon name="phone" className="text-white" />
                  </div>
                  <div>
                    <p className="font-body font-medium text-gray-900 dark:text-white">
                      Telefone
                    </p>
                    <p className="font-body font-light text-sm text-gray-600 dark:text-gray-400">
                      +55 (11) 3456-7890
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-bhub-red-accent rounded-lg flex items-center justify-center">
                    <Icon name="map-pin" className="text-white" />
                  </div>
                  <div>
                    <p className="font-body font-medium text-gray-900 dark:text-white">
                      Endereço
                    </p>
                    <p className="font-body font-light text-sm text-gray-600 dark:text-gray-400">
                      Av. Professor Lineu Prestes, 1234
                      <br />
                      São Paulo - SP, 05508-000
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <h2 className="font-display font-bold text-xl text-bhub-navy-dark dark:text-white mb-6">
                Envie uma Mensagem
              </h2>
              
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label htmlFor="name" className="block font-body font-medium text-gray-900 dark:text-white mb-2">
                    Nome Completo
                  </label>
                  <input
                    type="text"
                    id="name"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    required
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bhub-teal-primary focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    placeholder="Seu nome completo"
                  />
                </div>

                <div>
                  <label htmlFor="email" className="block font-body font-medium text-gray-900 dark:text-white mb-2">
                    E-mail
                  </label>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bhub-teal-primary focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    placeholder="seu@email.com"
                  />
                </div>

                <div>
                  <label htmlFor="subject" className="block font-body font-medium text-gray-900 dark:text-white mb-2">
                    Assunto
                  </label>
                  <input
                    type="text"
                    id="subject"
                    name="subject"
                    value={formData.subject}
                    onChange={handleChange}
                    required
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bhub-teal-primary focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    placeholder="Assunto da mensagem"
                  />
                </div>

                <div>
                  <label htmlFor="message" className="block font-body font-medium text-gray-900 dark:text-white mb-2">
                    Mensagem
                  </label>
                  <textarea
                    id="message"
                    name="message"
                    value={formData.message}
                    onChange={handleChange}
                    required
                    rows={5}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bhub-teal-primary focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
                    placeholder="Digite sua mensagem aqui..."
                  />
                </div>

                <Button
                  type="submit"
                  variant="default"
                  className="w-full bg-bhub-teal-primary hover:bg-bhub-teal-primary/90"
                >
                  Enviar Mensagem
                  <Icon name="send" />
                </Button>
              </form>
            </div>
          </div>
        </div>
      </main>
      
      <Footer />
    </MainLayout>
  );
}