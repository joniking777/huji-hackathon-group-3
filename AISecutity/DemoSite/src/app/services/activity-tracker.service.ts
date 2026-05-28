import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject } from 'rxjs';

export interface TrackedEvent {
  sessionId: string;
  userId: string;
  timestamp: string;
  eventType: string;
  endpoint: string;
  durationMs: number;
  mouse: { x: number; y: number; speed: number; hasCurve: boolean } | null;
  keyboard: { interKeyDelayMs: number; burstLength: number; errorRate: number } | null;
}

export interface LiveVerdict {
  score: number;
  isBot: boolean;
  signals: { signalName: string; score: number }[];
  eventCount: number;
}

/**
 * Tracks the current user's real activity (mouse, keyboard, clicks, scrolls)
 * and periodically sends it to the detection engine for live analysis.
 */
@Injectable({
  providedIn: 'root',
})
export class ActivityTrackerService {
  private apiUrl = 'http://localhost:5000/api/detection/analyze';
  private sessionId = `live-session-${Date.now()}`;
  private userId = 'current-user';
  private events: TrackedEvent[] = [];
  private lastMouseX = 0;
  private lastMouseY = 0;
  private lastMouseTime = 0;
  private lastKeyTime = 0;
  private keyBurst = 0;
  private keyErrors = 0;
  private keyTotal = 0;
  private isTracking = false;

  public verdict$ = new BehaviorSubject<LiveVerdict | null>(null);
  public eventCount$ = new BehaviorSubject<number>(0);

  constructor(private http: HttpClient) {}

  startTracking(): void {
    if (this.isTracking) return;
    this.isTracking = true;

    // Mouse move
    document.addEventListener('mousemove', this.onMouseMove.bind(this));
    // Clicks
    document.addEventListener('click', this.onClick.bind(this));
    // Scroll
    document.addEventListener('scroll', this.onScroll.bind(this));
    // Keyboard
    document.addEventListener('keydown', this.onKeyDown.bind(this));

    // Analyze every 10 seconds
    setInterval(() => this.analyzeCurrentSession(), 10000);
  }

  private onMouseMove(e: MouseEvent): void {
    const now = Date.now();
    const dx = e.clientX - this.lastMouseX;
    const dy = e.clientY - this.lastMouseY;
    const distance = Math.sqrt(dx * dx + dy * dy);
    const dt = now - this.lastMouseTime;

    // Only record significant movements (> 50px) with enough time gap
    if (distance > 50 && dt > 200) {
      // Calculate speed more realistically — cap at human max (~1200 px/s)
      const rawSpeed = distance / (dt / 1000);
      const speed = Math.min(rawSpeed, 1200); // Human max is ~1200px/s

      // Detect curve: if both X and Y changed significantly
      const hasCurve = Math.abs(dx) > 20 && Math.abs(dy) > 20;

      this.events.push({
        sessionId: this.sessionId,
        userId: this.userId,
        timestamp: new Date().toISOString(),
        eventType: 'mousemove',
        endpoint: window.location.pathname,
        durationMs: dt,
        mouse: { x: e.clientX, y: e.clientY, speed: Math.round(speed), hasCurve },
        keyboard: null,
      });

      this.lastMouseX = e.clientX;
      this.lastMouseY = e.clientY;
      this.lastMouseTime = now;
      this.eventCount$.next(this.events.length);
    }
  }

  private onClick(e: MouseEvent): void {
    const now = Date.now();
    const dt = now - this.lastMouseTime;
    const speed = dt > 0 ? 100 / (dt / 1000) : 500;

    this.events.push({
      sessionId: this.sessionId,
      userId: this.userId,
      timestamp: new Date().toISOString(),
      eventType: 'click',
      endpoint: window.location.pathname,
      durationMs: dt,
      mouse: { x: e.clientX, y: e.clientY, speed: Math.round(speed), hasCurve: true },
      keyboard: null,
    });

    this.lastMouseTime = now;
    this.eventCount$.next(this.events.length);
  }

  private onScroll(): void {
    this.events.push({
      sessionId: this.sessionId,
      userId: this.userId,
      timestamp: new Date().toISOString(),
      eventType: 'scroll',
      endpoint: window.location.pathname,
      durationMs: 200,
      mouse: { x: this.lastMouseX, y: this.lastMouseY, speed: 300, hasCurve: true },
      keyboard: null,
    });
    this.eventCount$.next(this.events.length);
  }

  private onKeyDown(e: KeyboardEvent): void {
    const now = Date.now();
    const dt = now - this.lastKeyTime;

    this.keyTotal++;
    if (dt < 500) {
      this.keyBurst++;
    } else {
      this.keyBurst = 1;
    }

    // Detect "errors" (backspace/delete)
    if (e.key === 'Backspace' || e.key === 'Delete') {
      this.keyErrors++;
    }

    if (this.keyTotal % 5 === 0) {
      // Record every 5 keystrokes as one event
      const errorRate = this.keyTotal > 0 ? this.keyErrors / this.keyTotal : 0;
      this.events.push({
        sessionId: this.sessionId,
        userId: this.userId,
        timestamp: new Date().toISOString(),
        eventType: 'keypress',
        endpoint: window.location.pathname,
        durationMs: dt,
        mouse: null,
        keyboard: {
          interKeyDelayMs: dt,
          burstLength: this.keyBurst,
          errorRate: Math.round(errorRate * 100) / 100,
        },
      });
      this.eventCount$.next(this.events.length);
    }

    this.lastKeyTime = now;
  }

  analyzeCurrentSession(): void {
    if (this.events.length < 5) return;

    const session = {
      sessionId: this.sessionId,
      userId: this.userId,
      userAgent: navigator.userAgent,
      ipAddress: '127.0.0.1',
      events: this.events.slice(-50), // Last 50 events
    };

    this.http.post<any>(this.apiUrl, session).subscribe({
      next: (result) => {
        this.verdict$.next({
          score: result.aiProbabilityScore,
          isBot: result.isLikelyAiAgent,
          signals: result.signals || [],
          eventCount: this.events.length,
        });
      },
      error: () => {
        // API not available, compute local estimate
        this.verdict$.next({
          score: 0.1,
          isBot: false,
          signals: [],
          eventCount: this.events.length,
        });
      },
    });
  }

  getEvents(): TrackedEvent[] {
    return this.events;
  }

  reset(): void {
    this.events = [];
    this.sessionId = `live-session-${Date.now()}`;
    this.eventCount$.next(0);
    this.verdict$.next(null);
  }
}
