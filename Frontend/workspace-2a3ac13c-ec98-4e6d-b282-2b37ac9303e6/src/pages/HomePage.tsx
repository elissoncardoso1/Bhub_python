'use client';

import React, { useEffect } from 'react';
import { Header } from '@/components/Layout/Header';
import { Footer } from '@/components/Layout/Footer';
import { MainLayout } from '@/components/Layout/MainLayout';
import { FeaturedArticleCard } from '@/components/ArticleCard/FeaturedArticleCard';
import { ArticleCardList } from '@/components/ArticleCard/ArticleCardList';
import { FilterSidebar } from '@/components/Sidebar/FilterSidebar';
import { TrendingSidebar } from '@/components/Sidebar/TrendingSidebar';
import { NewsletterCard } from '@/components/Sidebar/NewsletterCard';
import { LandingIntroBanner } from '@/components/Landing/LandingIntroBanner';
import { HowItWorksInline } from '@/components/Landing/HowItWorksInline';
import { SourcesPreview } from '@/components/Landing/SourcesPreview';
import { TransparencyNotice } from '@/components/Landing/TransparencyNotice';
import { cn } from '@/lib/utils';
import { useArticleStore } from '@/store/articleStore';
import { articleToCardProps, articleToFeaturedProps } from '@/types/article';

export function HomePage() {
  const { 
    articlesJournal, 
    articlesPortal, 
    featured, 
    loading, 
    error, 
    fetchJournalArticles, 
    fetchPortalArticles, 
    fetchFeatured 
  } = useArticleStore();

  useEffect(() => {
    // Fetch featured articles (highlighted)
    fetchFeatured(5);
    // Fetch columns
    fetchJournalArticles(6);
    fetchPortalArticles(6);
  }, [fetchFeatured, fetchJournalArticles, fetchPortalArticles]);

  // Get the first featured article for the hero section
  const featuredArticle = featured[0];

  // Transform articles for the card list
  const journalCards = articlesJournal.map(article => articleToCardProps(article));
  const portalCards = articlesPortal.map(article => articleToCardProps(article));

  // Build featured article props
  const featuredProps = featuredArticle ? {
    ...articleToFeaturedProps(featuredArticle),
    onRead: () => console.log('Read featured article', featuredArticle.id),
    onLike: () => console.log('Like featured article', featuredArticle.id),
    isLiked: false,
  } : null;

  return (
    <MainLayout>
      <Header />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Desktop Layout */}
        <div className="hidden lg:grid grid-cols-[240px_1fr_280px] gap-6">
          {/* Sidebar Left */}
          <div className="space-y-6">
            <FilterSidebar />
          </div>
          
          {/* Main Content */}
          <div className="space-y-8">
            {/* Landing Components */}
            <LandingIntroBanner />
            <HowItWorksInline />
            
            {/* Featured Article */}
            {featuredProps && <FeaturedArticleCard {...featuredProps} />}
            
            {/* Recent Articles Section */}
            {/* Recent Articles Section - 2 Columns */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Scientific Journals Column */}
              <section>
                <div className="flex items-center justify-between mb-6">
                  <h2 className="font-display font-bold text-xl text-bhub-navy-dark dark:text-white flex items-center gap-2">
                    <span className="p-1 bg-bhub-teal-primary/10 rounded-md">
                      <svg className="w-5 h-5 text-bhub-teal-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                      </svg>
                    </span>
                    Periódicos
                  </h2>
                </div>
                
                <ArticleCardList 
                  articles={journalCards} 
                  columns={1}
                />
              </section>

              {/* Portals/Blogs Column */}
              <section>
                <div className="flex items-center justify-between mb-6">
                  <h2 className="font-display font-bold text-xl text-bhub-navy-dark dark:text-white flex items-center gap-2">
                   <span className="p-1 bg-orange-100 rounded-md">
                      <svg className="w-5 h-5 text-orange-500" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 5c7.18 0 13 5.82 13 13M6 11a7 7 0 017 7m-6 0a1 1 0 11-2 0 1 1 0 012 0z" />
                      </svg>
                    </span>
                    Portais & Blogs
                  </h2>
                </div>
                
                <ArticleCardList 
                  articles={portalCards} 
                  columns={1}
                />
              </section>
            </div>
            
            {/* Sources and Transparency */}
            <SourcesPreview />
            <TransparencyNotice />
          </div>
          
          {/* Sidebar Right */}
          <div className="space-y-6">
            <TrendingSidebar />
            <NewsletterCard />
          </div>
        </div>

        {/* Tablet Layout */}
        <div className="hidden md:grid lg:hidden grid-cols-[1fr_280px] gap-6">
          {/* Main Content */}
          <div className="space-y-8">
            {/* Featured Article */}
            {featuredProps && <FeaturedArticleCard {...featuredProps} />}
            
            {/* Recent Articles Section - Stacked for Tablet */}
            <div className="space-y-8">
              <section>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-display font-bold text-xl text-bhub-navy-dark dark:text-white flex items-center gap-2">
                    <span className="p-1 bg-bhub-teal-primary/10 rounded-md">
                      <svg className="w-5 h-5 text-bhub-teal-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                      </svg>
                    </span>
                    Periódicos
                  </h2>
                </div>
                <ArticleCardList articles={journalCards} columns={1} />
              </section>

              <section>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-display font-bold text-xl text-bhub-navy-dark dark:text-white flex items-center gap-2">
                   <span className="p-1 bg-orange-100 rounded-md">
                      <svg className="w-5 h-5 text-orange-500" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 5c7.18 0 13 5.82 13 13M6 11a7 7 0 017 7m-6 0a1 1 0 11-2 0 1 1 0 012 0z" />
                      </svg>
                    </span>
                    Portais & Blogs
                  </h2>
                </div>
                <ArticleCardList articles={portalCards} columns={1} />
              </section>
            </div>
            
            {/* Sources and Transparency */}
            <SourcesPreview />
            <TransparencyNotice />
          </div>
          
          {/* Sidebar Right */}
          <div className="space-y-6">
            <TrendingSidebar />
            <NewsletterCard />
          </div>
        </div>

        {/* Mobile Layout */}
        <div className="md:hidden space-y-6">
          {/* Landing Components */}
          <LandingIntroBanner />
          <HowItWorksInline />
          
          {/* Featured Article */}
          {featuredProps && <FeaturedArticleCard {...featuredProps} />}
          
          {/* Trending Sidebar */}
          <TrendingSidebar />
          
          {/* Recent Articles Section */}
          {/* Recent Articles Section - Stacked for Mobile */}
          <div className="space-y-8">
            <section>
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-display font-bold text-lg text-bhub-navy-dark dark:text-white flex items-center gap-2">
                  <span className="p-1 bg-bhub-teal-primary/10 rounded-md">
                    <svg className="w-4 h-4 text-bhub-teal-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                    </svg>
                  </span>
                  Periódicos
                </h2>
              </div>
              <ArticleCardList articles={journalCards} columns={1} />
            </section>

            <section>
              <div className="flex items-center justify-between mb-4">
                  <h2 className="font-display font-bold text-lg text-bhub-navy-dark dark:text-white flex items-center gap-2">
                   <span className="p-1 bg-orange-100 rounded-md">
                      <svg className="w-4 h-4 text-orange-500" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 5c7.18 0 13 5.82 13 13M6 11a7 7 0 017 7m-6 0a1 1 0 11-2 0 1 1 0 012 0z" />
                      </svg>
                    </span>
                    Portais & Blogs
                  </h2>
              </div>
              <ArticleCardList articles={portalCards} columns={1} />
            </section>
          </div>
          
          {/* Sources and Transparency */}
          <SourcesPreview />
          <TransparencyNotice />
          
          {/* Newsletter Card */}
          <NewsletterCard />
          
          {/* Filter Sidebar (Mobile) */}
          <FilterSidebar />
        </div>
      </main>
      
      <Footer />
    </MainLayout>
  );
}