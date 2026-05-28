import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DetectionService } from './services/detection.service';
import { DetectionResult } from './models/detection.models';

@Component({
  selector: 'app-root',
  imports: [CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App implements OnInit {
  results: DetectionResult[] = [];
  featuredResult: DetectionResult | null = null;
  latestThreats: DetectionResult[] = [];
  currentDate = '';
  threatCount = 0;
  safeCount = 0;
  avgScore = '0';
  topSignals: { name: string; avgScore: number }[] = [];

  constructor(private detectionService: DetectionService) {}

  ngOnInit(): void {
    this.currentDate = new Date().toLocaleDateString('he-IL', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });

    this.detectionService.startLiveFeed();
    this.detectionService.results$.subscribe((results) => {
      this.results = results;
      this.updateStats();
    });
  }

  updateStats(): void {
    this.threatCount = this.results.filter((r) => r.isLikelyAiAgent).length;
    this.safeCount = this.results.filter((r) => !r.isLikelyAiAgent).length;

    if (this.results.length > 0) {
      const avg = this.results.reduce((sum, r) => sum + r.aiProbabilityScore, 0) / this.results.length;
      this.avgScore = (avg * 100).toFixed(1);
      this.featuredResult = this.results[0];
      this.latestThreats = this.results.filter((r) => r.isLikelyAiAgent).slice(0, 5);
    }

    this.calculateTopSignals();
  }

  calculateTopSignals(): void {
    const signalMap = new Map<string, { total: number; count: number }>();

    for (const result of this.results) {
      for (const signal of result.signals) {
        const existing = signalMap.get(signal.signalName) || { total: 0, count: 0 };
        existing.total += signal.score;
        existing.count++;
        signalMap.set(signal.signalName, existing);
      }
    }

    this.topSignals = Array.from(signalMap.entries())
      .map(([name, data]) => ({ name, avgScore: data.total / data.count }))
      .sort((a, b) => b.avgScore - a.avgScore);
  }

  selectResult(result: DetectionResult): void {
    this.featuredResult = result;
  }
}
