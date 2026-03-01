/**
 * User API endpoints for history and favorites
 */

import client from './client';
import type {
  HistoryResponse,
  FavoritesResponse,
  FavoriteIdsResponse,
} from '../types/user';

// ============== History ==============

/**
 * Get user's match history
 */
export async function getHistory(page = 1, pageSize = 10): Promise<HistoryResponse> {
  const response = await client.get('/user/history', {
    params: { page, page_size: pageSize },
  });
  return response.data.data;
}

// ============== Favorites ==============

/**
 * Get user's favorite snippets
 */
export async function getFavorites(page = 1, pageSize = 10): Promise<FavoritesResponse> {
  const response = await client.get('/user/favorites', {
    params: { page, page_size: pageSize },
  });
  return response.data.data;
}

/**
 * Get list of favorite snippet IDs (for quick lookup)
 */
export async function getFavoriteIds(): Promise<FavoriteIdsResponse> {
  const response = await client.get('/user/favorites/ids');
  return response.data.data;
}

/**
 * Add a snippet to favorites
 */
export async function addFavorite(snippetId: number): Promise<void> {
  await client.post('/user/favorites', { snippet_id: snippetId });
}

/**
 * Remove a snippet from favorites
 */
export async function removeFavorite(snippetId: number): Promise<void> {
  await client.delete('/user/favorites', { data: { snippet_id: snippetId } });
}
