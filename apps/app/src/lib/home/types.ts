export interface ActivityItem {
  id: string;
  niche: string;
  city: string;
  created_at: string;
}

export interface RecommendedItem {
  id: string;
  niche: string;
  city: string;
  score: number | null;
}

export interface StatCard {
  label: string;
  value: string;
  delta?: string;
}
