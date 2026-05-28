import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, interval, of } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';
import { DetectionResult, ActivitySession } from '../models/detection.models';

@Injectable({
  providedIn: 'root',
})
export class DetectionService {
  private apiUrl = 'http://localhost:5278/api/detection';
  private resultsSubject = new BehaviorSubject<DetectionResult[]>([]);
  public results$ = this.resultsSubject.asObservable();

  constructor(private http: HttpClient) {}

  analyzeSession(session: ActivitySession): Observable<DetectionResult> {
    return this.http.post<DetectionResult>(`${this.apiUrl}/analyze`, session);
  }

  analyzeBatch(sessions: ActivitySession[]): Observable<DetectionResult[]> {
    return this.http.post<DetectionResult[]>(`${this.apiUrl}/analyze-batch`, sessions);
  }

  getStatus(): Observable<any> {
    return this.http.get(`${this.apiUrl}/status`);
  }

  /**
   * Generates mock detection results for demo purposes
   * when the backend is not running.
   */
  generateMockResults(): DetectionResult[] {
    const mockResults: DetectionResult[] = [
      {
        sessionId: 'sess-001',
        userId: 'bot-crawler-7x',
        aiProbabilityScore: 0.92,
        isLikelyAiAgent: true,
        totalEventsAnalyzed: 47,
        analyzedAt: new Date(Date.now() - 120000).toISOString(),
        signals: [
          { signalName: 'TimingRegularity', weight: 0.25, score: 0.95, description: 'Coefficient of variation: 0.045. Lower = more robotic.' },
          { signalName: 'ActionSpeed', weight: 0.20, score: 0.88, description: '72.3% actions under 50ms, 94.1% under 200ms.' },
          { signalName: 'MouseBehavior', weight: 0.15, score: 0.91, description: 'Linear movement ratio: 0.89, No-curve ratio: 0.95.' },
          { signalName: 'KeyboardBehavior', weight: 0.15, score: 0.85, description: 'Analyzed 12 keyboard events for consistency and error patterns.' },
          { signalName: 'NavigationPattern', weight: 0.15, score: 0.97, description: 'Navigation efficiency: 1.00, Sequential API ratio: 0.88.' },
          { signalName: 'SessionRhythm', weight: 0.10, score: 0.95, description: 'Pause ratio: 0.00, Idle gaps: 0. No pauses = bot-like.' },
        ],
      },
      {
        sessionId: 'sess-002',
        userId: 'user-sarah-m',
        aiProbabilityScore: 0.18,
        isLikelyAiAgent: false,
        totalEventsAnalyzed: 23,
        analyzedAt: new Date(Date.now() - 300000).toISOString(),
        signals: [
          { signalName: 'TimingRegularity', weight: 0.25, score: 0.1, description: 'Coefficient of variation: 0.820. Lower = more robotic.' },
          { signalName: 'ActionSpeed', weight: 0.20, score: 0.05, description: '0.0% actions under 50ms, 4.3% under 200ms.' },
          { signalName: 'MouseBehavior', weight: 0.15, score: 0.12, description: 'Linear movement ratio: 0.10, No-curve ratio: 0.05.' },
          { signalName: 'KeyboardBehavior', weight: 0.15, score: 0.3, description: 'Analyzed 8 keyboard events for consistency and error patterns.' },
          { signalName: 'NavigationPattern', weight: 0.15, score: 0.25, description: 'Navigation efficiency: 0.55, Sequential API ratio: 0.10.' },
          { signalName: 'SessionRhythm', weight: 0.10, score: 0.1, description: 'Pause ratio: 0.22, Idle gaps: 3. No pauses = bot-like.' },
        ],
      },
      {
        sessionId: 'sess-003',
        userId: 'scraper-agent-v2',
        aiProbabilityScore: 0.87,
        isLikelyAiAgent: true,
        totalEventsAnalyzed: 156,
        analyzedAt: new Date(Date.now() - 60000).toISOString(),
        signals: [
          { signalName: 'TimingRegularity', weight: 0.25, score: 0.88, description: 'Coefficient of variation: 0.078. Lower = more robotic.' },
          { signalName: 'ActionSpeed', weight: 0.20, score: 0.92, description: '65.0% actions under 50ms, 89.7% under 200ms.' },
          { signalName: 'MouseBehavior', weight: 0.15, score: 0.5, description: 'Insufficient mouse data.' },
          { signalName: 'KeyboardBehavior', weight: 0.15, score: 0.5, description: 'Insufficient keyboard data.' },
          { signalName: 'NavigationPattern', weight: 0.15, score: 0.98, description: 'Navigation efficiency: 0.98, Sequential API ratio: 0.92.' },
          { signalName: 'SessionRhythm', weight: 0.10, score: 0.95, description: 'Pause ratio: 0.01, Idle gaps: 0. No pauses = bot-like.' },
        ],
      },
      {
        sessionId: 'sess-004',
        userId: 'user-david-k',
        aiProbabilityScore: 0.31,
        isLikelyAiAgent: false,
        totalEventsAnalyzed: 34,
        analyzedAt: new Date(Date.now() - 540000).toISOString(),
        signals: [
          { signalName: 'TimingRegularity', weight: 0.25, score: 0.3, description: 'Coefficient of variation: 0.410. Lower = more robotic.' },
          { signalName: 'ActionSpeed', weight: 0.20, score: 0.15, description: '2.9% actions under 50ms, 11.8% under 200ms.' },
          { signalName: 'MouseBehavior', weight: 0.15, score: 0.22, description: 'Linear movement ratio: 0.18, No-curve ratio: 0.12.' },
          { signalName: 'KeyboardBehavior', weight: 0.15, score: 0.45, description: 'Analyzed 15 keyboard events for consistency and error patterns.' },
          { signalName: 'NavigationPattern', weight: 0.15, score: 0.35, description: 'Navigation efficiency: 0.62, Sequential API ratio: 0.20.' },
          { signalName: 'SessionRhythm', weight: 0.10, score: 0.2, description: 'Pause ratio: 0.18, Idle gaps: 2. No pauses = bot-like.' },
        ],
      },
      {
        sessionId: 'sess-005',
        userId: 'gpt-automation',
        aiProbabilityScore: 0.96,
        isLikelyAiAgent: true,
        totalEventsAnalyzed: 89,
        analyzedAt: new Date(Date.now() - 30000).toISOString(),
        signals: [
          { signalName: 'TimingRegularity', weight: 0.25, score: 0.99, description: 'Coefficient of variation: 0.012. Lower = more robotic.' },
          { signalName: 'ActionSpeed', weight: 0.20, score: 0.95, description: '81.0% actions under 50ms, 97.8% under 200ms.' },
          { signalName: 'MouseBehavior', weight: 0.15, score: 0.98, description: 'Linear movement ratio: 0.97, No-curve ratio: 1.00.' },
          { signalName: 'KeyboardBehavior', weight: 0.15, score: 0.92, description: 'Analyzed 30 keyboard events for consistency and error patterns.' },
          { signalName: 'NavigationPattern', weight: 0.15, score: 0.99, description: 'Navigation efficiency: 1.00, Sequential API ratio: 0.95.' },
          { signalName: 'SessionRhythm', weight: 0.10, score: 0.95, description: 'Pause ratio: 0.00, Idle gaps: 0. No pauses = bot-like.' },
        ],
      },
      {
        sessionId: 'sess-006',
        userId: 'user-maya-r',
        aiProbabilityScore: 0.12,
        isLikelyAiAgent: false,
        totalEventsAnalyzed: 18,
        analyzedAt: new Date(Date.now() - 900000).toISOString(),
        signals: [
          { signalName: 'TimingRegularity', weight: 0.25, score: 0.1, description: 'Coefficient of variation: 0.950. Lower = more robotic.' },
          { signalName: 'ActionSpeed', weight: 0.20, score: 0.02, description: '0.0% actions under 50ms, 0.0% under 200ms.' },
          { signalName: 'MouseBehavior', weight: 0.15, score: 0.08, description: 'Linear movement ratio: 0.05, No-curve ratio: 0.00.' },
          { signalName: 'KeyboardBehavior', weight: 0.15, score: 0.2, description: 'Analyzed 6 keyboard events for consistency and error patterns.' },
          { signalName: 'NavigationPattern', weight: 0.15, score: 0.15, description: 'Navigation efficiency: 0.40, Sequential API ratio: 0.05.' },
          { signalName: 'SessionRhythm', weight: 0.10, score: 0.1, description: 'Pause ratio: 0.35, Idle gaps: 5. No pauses = bot-like.' },
        ],
      },
      {
        sessionId: 'sess-007',
        userId: 'selenium-test-runner',
        aiProbabilityScore: 0.79,
        isLikelyAiAgent: true,
        totalEventsAnalyzed: 62,
        analyzedAt: new Date(Date.now() - 180000).toISOString(),
        signals: [
          { signalName: 'TimingRegularity', weight: 0.25, score: 0.85, description: 'Coefficient of variation: 0.095. Lower = more robotic.' },
          { signalName: 'ActionSpeed', weight: 0.20, score: 0.7, description: '45.2% actions under 50ms, 72.6% under 200ms.' },
          { signalName: 'MouseBehavior', weight: 0.15, score: 0.75, description: 'Linear movement ratio: 0.72, No-curve ratio: 0.80.' },
          { signalName: 'KeyboardBehavior', weight: 0.15, score: 0.6, description: 'Analyzed 20 keyboard events for consistency and error patterns.' },
          { signalName: 'NavigationPattern', weight: 0.15, score: 0.85, description: 'Navigation efficiency: 0.90, Sequential API ratio: 0.75.' },
          { signalName: 'SessionRhythm', weight: 0.10, score: 0.9, description: 'Pause ratio: 0.02, Idle gaps: 0. No pauses = bot-like.' },
        ],
      },
      {
        sessionId: 'sess-008',
        userId: 'user-amit-l',
        aiProbabilityScore: 0.22,
        isLikelyAiAgent: false,
        totalEventsAnalyzed: 41,
        analyzedAt: new Date(Date.now() - 420000).toISOString(),
        signals: [
          { signalName: 'TimingRegularity', weight: 0.25, score: 0.15, description: 'Coefficient of variation: 0.680. Lower = more robotic.' },
          { signalName: 'ActionSpeed', weight: 0.20, score: 0.1, description: '0.0% actions under 50ms, 7.3% under 200ms.' },
          { signalName: 'MouseBehavior', weight: 0.15, score: 0.18, description: 'Linear movement ratio: 0.12, No-curve ratio: 0.08.' },
          { signalName: 'KeyboardBehavior', weight: 0.15, score: 0.35, description: 'Analyzed 18 keyboard events for consistency and error patterns.' },
          { signalName: 'NavigationPattern', weight: 0.15, score: 0.28, description: 'Navigation efficiency: 0.58, Sequential API ratio: 0.15.' },
          { signalName: 'SessionRhythm', weight: 0.10, score: 0.15, description: 'Pause ratio: 0.25, Idle gaps: 4. No pauses = bot-like.' },
        ],
      },
    ];

    return mockResults;
  }

  /**
   * Simulates a live feed by adding new events periodically.
   */
  startLiveFeed(): void {
    const baseResults = this.generateMockResults();
    this.resultsSubject.next(baseResults);

    // Every 15 seconds, add a new "event" to simulate live monitoring
    interval(15000).subscribe((tick) => {
      const current = this.resultsSubject.value;
      const newResult = this.generateRandomResult(tick);
      this.resultsSubject.next([newResult, ...current].slice(0, 50));
    });
  }

  private generateRandomResult(seed: number): DetectionResult {
    const isBot = Math.random() > 0.5;
    const score = isBot ? 0.65 + Math.random() * 0.35 : Math.random() * 0.45;
    const botNames = ['api-scraper', 'gpt-agent', 'selenium-bot', 'puppeteer-crawl', 'auto-tester'];
    const humanNames = ['user-noa', 'user-idan', 'user-shira', 'user-yossi', 'user-tal'];
    const names = isBot ? botNames : humanNames;

    return {
      sessionId: `sess-live-${Date.now()}-${seed}`,
      userId: names[Math.floor(Math.random() * names.length)],
      aiProbabilityScore: Math.round(score * 100) / 100,
      isLikelyAiAgent: score >= 0.65,
      totalEventsAnalyzed: Math.floor(Math.random() * 150) + 10,
      analyzedAt: new Date().toISOString(),
      signals: [
        { signalName: 'TimingRegularity', weight: 0.25, score: isBot ? 0.8 + Math.random() * 0.2 : Math.random() * 0.3, description: '' },
        { signalName: 'ActionSpeed', weight: 0.20, score: isBot ? 0.7 + Math.random() * 0.3 : Math.random() * 0.2, description: '' },
        { signalName: 'MouseBehavior', weight: 0.15, score: isBot ? 0.6 + Math.random() * 0.4 : Math.random() * 0.25, description: '' },
        { signalName: 'KeyboardBehavior', weight: 0.15, score: 0.5, description: '' },
        { signalName: 'NavigationPattern', weight: 0.15, score: isBot ? 0.75 + Math.random() * 0.25 : Math.random() * 0.3, description: '' },
        { signalName: 'SessionRhythm', weight: 0.10, score: isBot ? 0.85 + Math.random() * 0.15 : Math.random() * 0.2, description: '' },
      ],
    };
  }
}
