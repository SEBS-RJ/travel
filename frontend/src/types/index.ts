// ============================================================
// frontend/src/types/index.ts
// Tipos TypeScript compartidos en toda la aplicación
// ============================================================

// ── Chat ──────────────────────────────────────────────────────

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  intent?: string;
  sources?: string[];
  safetyWarnings?: string[];
  quickReplies?: string[];
  isLoading?: boolean;
  fallbackUsed?: boolean;
}

export interface UserContext {
  hour?: number;
  budgetBob?: number;
  availableMinutes?: number;
  zoneRisk?: 'low' | 'moderate' | 'high';
  isForeign?: boolean;
  prefersWalking?: boolean;
  accessibilityNeeded?: boolean;
  travelParty?: 'solo' | 'pareja' | 'familia' | 'grupo';
}

export interface ChatRequest {
  sessionId: string;
  message: string;
  history: { role: 'user' | 'assistant'; content: string }[];
  userContext?: UserContext;
  language?: 'es' | 'en';
}

export interface ChatResponse {
  sessionId: string;
  answer: string;
  intent: string;
  sources: string[];
  confidence: number;
  safetyWarnings: string[];
  quickReplies: string[];
  fallbackUsed: boolean;
  timestamp: string;
}

// ── Recomendaciones ───────────────────────────────────────────

export interface PlaceSummary {
  id: string;
  name: string;
  description?: string;
  category: string;
  address?: string;
  latitude: number;
  longitude: number;
  distanceKm: number;
  priceRange: 'free' | 'low' | 'mid' | 'high';
  avgPriceBob?: number;
  rating: number;
  images: string[];
  tags: string[];
  isAccessible: boolean;
  openingHours?: string;
}

export interface RecommendationItem {
  place: PlaceSummary;
  score: number;
  reason: string;
  filtersMatched: string[];
}