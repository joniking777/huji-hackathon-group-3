export interface DetectionResult {
  sessionId: string;
  userId: string;
  aiProbabilityScore: number;
  isLikelyAiAgent: boolean;
  signals: DetectionSignal[];
  analyzedAt: string;
  totalEventsAnalyzed: number;
}

export interface DetectionSignal {
  signalName: string;
  weight: number;
  score: number;
  description: string;
}

export interface ActivitySession {
  sessionId: string;
  userId: string;
  userAgent: string;
  ipAddress: string;
  events: ActivityEvent[];
}

export interface ActivityEvent {
  sessionId: string;
  userId: string;
  timestamp: string;
  eventType: string;
  endpoint: string;
  durationMs: number | null;
  mouse: MouseData | null;
  keyboard: KeyboardData | null;
}

export interface MouseData {
  x: number;
  y: number;
  speed: number | null;
  hasCurve: boolean | null;
}

export interface KeyboardData {
  interKeyDelayMs: number | null;
  burstLength: number | null;
  errorRate: number | null;
}
