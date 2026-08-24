/**
 * Shared API Client for WeatherGPT Frontend.
 * Interacts with Python FastAPI backend via NEXT_PUBLIC_API_URL.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface LocationItem {
  id?: string;
  name: string;
  latitude: number;
  longitude: number;
  country?: string;
  admin1?: string;
  display_name?: string;
}

export interface CurrentWeather {
  time: string;
  temperature_2m: number;
  relative_humidity_2m: number;
  apparent_temperature: number;
  precipitation: number;
  weather_code: number;
  cloud_cover: number;
  wind_speed_10m: number;
  wind_gusts_10m: number;
  wind_direction_10m: number;
}

export interface HourlyForecast {
  time: string[];
  temperature_2m: number[];
  relative_humidity_2m: number[];
  apparent_temperature: number[];
  precipitation: number[];
  precipitation_probability: number[];
  weather_code: number[];
  cloud_cover: number[];
  wind_speed_10m: number[];
  wind_gusts_10m: number[];
}

export interface DailyForecast {
  time: string[];
  temperature_2m_max: number[];
  temperature_2m_min: number[];
  apparent_temperature_max: number[];
  apparent_temperature_min: number[];
  precipitation_sum: number[];
  precipitation_probability_max: number[];
  weather_code: number[];
  wind_speed_10m_max: number[];
  wind_gusts_10m_max: number[];
  sunrise: string[];
  sunset: string[];
}

export interface WeatherResponse {
  latitude: number;
  longitude: number;
  timezone: string;
  elevation: number;
  current: CurrentWeather;
  hourly: HourlyForecast;
  daily: DailyForecast;
  cached: boolean;
}

export interface Alert {
  id: string;
  alert_type: string;
  severity: string;
  affected_location: string;
  affected_lat?: number;
  affected_lon?: number;
  affected_radius_km?: number;
  issue_time: string;
  expiry_time: string;
  source: string;
  instructions: string;
  is_mock?: boolean;
}

export interface AlertStoreResponse {
  active_count: number;
  alerts: Alert[];
}

export interface ToolCall {
  tool_name: string;
  arguments: Record<string, any>;
  result_summary: string;
}

export interface ChatResponse {
  answer: string;
  data_used: Record<string, any>;
  tool_calls_made: ToolCall[];
  model?: string;
  session_id?: string;
  language?: string;
}


export interface AdvisoryItem {
  category: string;
  use_case: string;
  title: string;
  description: string;
  priority: string;
}

export interface AdvisorySet {
  summary: string;
  items: AdvisoryItem[];
}

export interface RiskResult {
  score: number;
  level: "low" | "moderate" | "high" | "critical" | string;
  reasons: string[];
  sub_scores: Record<string, number>;
  advisory: AdvisorySet;
}

export async function searchLocation(query: string, count = 10): Promise<LocationItem[]> {
  if (!query.trim()) return [];
  const res = await fetch(`${API_BASE_URL}/api/location/search?q=${encodeURIComponent(query)}&count=${count}`);
  if (!res.ok) {
    throw new Error(`Location search failed: ${res.statusText}`);
  }
  const data = await res.json();
  return data.results || [];
}

export async function getWeather(lat: number, lon: number): Promise<WeatherResponse> {
  const res = await fetch(`${API_BASE_URL}/api/weather?lat=${lat}&lon=${lon}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch weather: ${res.statusText}`);
  }
  return res.json();
}

export async function getAlerts(lat?: number, lon?: number): Promise<AlertStoreResponse> {
  let url = `${API_BASE_URL}/api/alerts`;
  if (lat !== undefined && lon !== undefined) {
    url += `?lat=${lat}&lon=${lon}`;
  }
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch alerts: ${res.statusText}`);
  }
  return res.json();
}

export async function sendChat(message: string, sessionId?: string, language: string = "en"): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId, language }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Chat request failed with status ${res.status}`);
  }
  return res.json();
}

export async function getRisk(lat: number, lon: number): Promise<RiskResult> {
  const res = await fetch(`${API_BASE_URL}/api/risk?lat=${lat}&lon=${lon}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch risk assessment: ${res.statusText}`);
  }
  return res.json();
}

export function getAlertWebSocketUrl(): string {
  const url = new URL(API_BASE_URL);
  const wsProtocol = url.protocol === "https:" ? "wss:" : "ws:";
  return `${wsProtocol}//${url.host}/ws/alerts`;
}
