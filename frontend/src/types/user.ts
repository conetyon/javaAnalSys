/**
 * User-related types for history and favorites
 */

// ============== History ==============

export interface HistoryItem {
  id: number;
  kp_ids: number[];
  kp_names: string[];
  params: Record<string, unknown>;
  mode: 'list' | 'matrix';
  created_at: string;
}

export interface HistoryResponse {
  items: HistoryItem[];
  total: number;
  page: number;
  page_size: number;
}

// ============== Favorites ==============

export interface FavoriteItem {
  id: number;
  snippet_id: number;
  content: string;
  file_path?: string;
  created_at: string;
}

export interface FavoritesResponse {
  items: FavoriteItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface FavoriteIdsResponse {
  snippet_ids: number[];
}
