export interface TrafficStats {
  total_sessions: number;
  unique_visitors: number;
  total_page_views: number;
  avg_session_duration: number;
}

export interface ContentStats {
  article_views: number;
  article_downloads: number;
  searches: number;
}

export interface EventsStats {
  total_events: number;
  events_by_type: Record<string, number>;
}

export interface TimeSeriesDataPoint {
  period: string;
  count: number;
}

export interface TopPage {
  path: string;
  views: number;
}

export interface AnalyticsOverview {
  traffic: TrafficStats;
  content: ContentStats;
  events: EventsStats;
  time_series: TimeSeriesDataPoint[];
  top_pages: TopPage[];
  period_days: number;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL 
  ? `${process.env.NEXT_PUBLIC_API_URL}/api/v1` 
  : '/api/v1';

export const AnalyticsService = {
  async getOverview(token: string, days: number = 30): Promise<AnalyticsOverview> {
    const response = await fetch(`${API_BASE_URL}/admin/analytics/overview?days=${days}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error('Failed to fetch analytics overview');
    return response.json();
  },

  async getTrafficStats(token: string, days: number = 30): Promise<TrafficStats> {
    const response = await fetch(`${API_BASE_URL}/admin/analytics/traffic?days=${days}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error('Failed to fetch traffic stats');
    return response.json();
  },

  async getContentStats(token: string, days: number = 30): Promise<ContentStats> {
    const response = await fetch(`${API_BASE_URL}/admin/analytics/content?days=${days}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error('Failed to fetch content stats');
    return response.json();
  },

  async getEventsStats(
    token: string,
    startDate?: string,
    endDate?: string,
    eventType?: string
  ): Promise<EventsStats> {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (eventType) params.append('event_type', eventType);

    const response = await fetch(
      `${API_BASE_URL}/admin/analytics/events?${params.toString()}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    if (!response.ok) throw new Error('Failed to fetch events stats');
    return response.json();
  },

  async getTimeSeries(
    token: string,
    days: number = 30,
    period: 'hour' | 'day' | 'week' | 'month' = 'day'
  ): Promise<TimeSeriesDataPoint[]> {
    const response = await fetch(
      `${API_BASE_URL}/admin/analytics/time-series?days=${days}&period=${period}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    if (!response.ok) throw new Error('Failed to fetch time series');
    return response.json();
  },

  async getTopPages(token: string, days: number = 30, limit: number = 10): Promise<TopPage[]> {
    const response = await fetch(
      `${API_BASE_URL}/admin/analytics/top-pages?days=${days}&limit=${limit}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    if (!response.ok) throw new Error('Failed to fetch top pages');
    return response.json();
  },

  // Métodos públicos para tracking (não requerem autenticação)
  async trackEvent(
    eventType: string,
    eventName: string,
    properties?: Record<string, any>,
    pagePath?: string,
    referrer?: string
  ): Promise<void> {
    try {
      const sessionId = this.getOrCreateSessionId();
      
      await fetch(`${API_BASE_URL}/analytics/track`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId,
        },
        body: JSON.stringify({
          event_type: eventType,
          event_name: eventName,
          properties,
          page_path: pagePath || window.location.pathname,
          referrer: referrer || document.referrer,
        }),
      });

      // Salvar session_id no cookie
      this.setSessionId(sessionId);
    } catch (error) {
      // Não falhar silenciosamente em produção, mas não bloquear a aplicação
      console.warn('Analytics tracking failed:', error);
    }
  },

  async trackPageView(pagePath?: string, referrer?: string): Promise<void> {
    try {
      const sessionId = this.getOrCreateSessionId();
      
      await fetch(`${API_BASE_URL}/analytics/pageview`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId,
        },
        body: JSON.stringify({
          page_path: pagePath || window.location.pathname,
          referrer: referrer || document.referrer,
        }),
      });

      this.setSessionId(sessionId);
    } catch (error) {
      console.warn('Page view tracking failed:', error);
    }
  },

  getOrCreateSessionId(): string {
    if (typeof window === 'undefined') return '';
    
    // Tentar obter do cookie
    const cookies = document.cookie.split(';');
    const sessionCookie = cookies.find(c => c.trim().startsWith('analytics_session_id='));
    if (sessionCookie) {
      return sessionCookie.split('=')[1];
    }

    // Gerar novo session_id
    const sessionId = this.generateSessionId();
    this.setSessionId(sessionId);
    return sessionId;
  },

  generateSessionId(): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 15);
    return `${timestamp}-${random}`.substring(0, 32);
  },

  setSessionId(sessionId: string): void {
    if (typeof document !== 'undefined') {
      // Cookie válido por 30 dias
      const expiryDate = new Date();
      expiryDate.setDate(expiryDate.getDate() + 30);
      document.cookie = `analytics_session_id=${sessionId}; expires=${expiryDate.toUTCString()}; path=/; SameSite=Lax`;
    }
  },
};

