export interface User {
  id: number;
  username: string;
  role: 'admin' | 'user';
  is_active: boolean;
  nama_lengkap?: string;
  created_at?: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface DashboardSummary {
  total_accounts: number;
  active_accounts: number;

  total_followers: number;
  total_following: number;
  avg_followers: number;
  accounts_with_followers: number;

  total_posts: number;
  new_posts: number;
  failed_posts: number;
  partial_posts: number;

  total_likes: number;
  total_comments: number;
  total_engagement: number;
  total_views: number;  // Only for reels/video posts

  media_image: number;
  media_carousel: number;
  media_reels: number;
  media_video: number;
  media_unclassified: number;
}

export interface PostItem {
  id: number;
  username: string;
  nama_unit?: string;
  post_url: string;
  shortcode: string;
  caption?: string;
  timestamp?: string;
  media_type: string;
  media_type_normalized: string;
  like_count?: number;
  comment_count?: number;
  total_engagement?: number;
  view_count?: number;  // NULL = not available, not 0
  play_count?: number;
  share_count?: number;
  save_count?: number;
  view_parse_status?: string;  // AVAILABLE, NOT_EXPOSED, PARSE_FAILED, NOT_REELS
  status_scraping: string;
  status_periode?: string;
  is_new_post: boolean;
}

export interface PostsResponse {
  posts: PostItem[];
  total: number;
  period_start: string;
  period_end: string;
}

export interface EngagementData {
  username: string;
  nama_unit: string;
  total_engagement: number;
  like_count: number;
  comment_count: number;
  post_count: number;
  followers_count?: number;
  engagement_rate?: number;  // (like + comment) / followers * 100
}

export interface MediaTypeData {
  media_type: string;
  count: number;
  percentage: number;
}

export interface FollowerData {
  username: string;
  nama_unit: string;
  followers_count?: number;
  following_count?: number;
  profile_posts_count?: number;
  is_active: boolean;
}

export interface ChartData {
  engagement_by_account: EngagementData[];
  posts_by_account: { username: string; nama_unit: string; count: number }[];
  media_type_breakdown: MediaTypeData[];
  interaction_tiers: { high: number; medium: number; low: number };
  followers_by_account: FollowerData[];
}

export interface AccountOption {
  username: string;
  nama_unit: string;
  kategori_unit?: string;
  wilayah?: string;
}

export interface JobItem {
  id: number;
  job_id: string;
  job_type: string;
  trigger_type: string;
  status: string;
  period_start?: string;
  period_end?: string;
  started_at?: string;
  finished_at?: string;
  worker_heartbeat_at?: string;
  total_accounts: number;
  total_posts_found: number;
  total_posts_inserted: number;
  total_posts_updated: number;
  total_success: number;
  total_partial: number;
  total_failed: number;
  error_message?: string;
  created_at: string;
}

export interface FailedItem {
  id: number;
  job_id: string;
  username?: string;
  post_url?: string;
  reason?: string;
  error_type?: string;
  created_at: string;
}

export interface NodeFlowItem {
  id: string;
  name: string;
  status: 'idle' | 'running' | 'success' | 'warning' | 'failed' | 'stuck';
  description?: string;
  last_updated?: string;
  details?: Record<string, unknown>;
}

export interface AlertItem {
  id: number;
  alert_type: string;
  title: string;
  message: string;
  severity: 'info' | 'warning' | 'danger';
  is_read: boolean;
  created_at: string;
  metadata?: Record<string, unknown>;
}

export interface NodeFlowResponse {
  nodes: NodeFlowItem[];
  current_job?: JobItem;
  worker_status: 'alive' | 'dead' | 'unknown';
  worker_last_heartbeat?: string;
}

export interface WorkerStatus {
  is_alive: boolean;
  last_heartbeat?: string;
  current_job_id?: string;
  current_job_status?: string;
  pid?: number;
}

export const MEDIA_TYPE_LABELS: Record<string, string> = {
  'IMAGE': 'Gambar',
  'CAROUSEL': 'Carousel',
  'REELS': 'Reels',
  'VIDEO': 'Video',
  'UNCLASSIFIED_REVIEW': 'Perlu Review',
};

export const MEDIA_TYPE_COLORS: Record<string, string> = {
  'IMAGE': '#102A43',
  'CAROUSEL': '#D4A017',
  'REELS': '#16A34A',
  'VIDEO': '#7C3AED',
  'UNCLASSIFIED_REVIEW': '#94A3B8',
};
