using AISecutity.Models;

namespace AISecutity.Detection;

/// <summary>
/// Core AI agent detection algorithm (v2 — hardened against evasion bots).
/// Analyzes behavioral patterns to distinguish AI agents from human users.
/// 
/// Key signals:
/// 1. Timing regularity - AI agents have unnaturally consistent intervals
/// 2. Speed - AI can act faster than humanly possible
/// 3. Mouse linearity - bots move in straight lines, humans curve
/// 4. Mouse speed profile - bots have unnaturally high/consistent mouse speed
/// 5. Keyboard patterns - AI types at constant speed with no typos
/// 6. Navigation patterns - AI targets API endpoints directly
/// 7. API endpoint targeting - any /api/ access from a "browser" session is suspicious
/// 8. Session rhythm - AI doesn't take breaks or hesitate
/// 
/// v2 changes (based on challenge bot analysis):
/// - Added MouseSpeedProfile signal (avg speed + speed variance)
/// - Added ApiTargeting signal (detects /api/ endpoint access)
/// - Improved NavigationPattern to catch browsing-then-targeting behavior
/// - Lowered threshold from 0.65 to 0.55
/// - Rebalanced weights to emphasize new signals
/// </summary>
public class AiDetectionEngine : IAiDetectionEngine
{
    private const double AiThreshold = 0.50; // v2.1: lowered to catch challenge bots (they score 0.33-0.44)

    public DetectionResult Analyze(ActivitySession session)
    {
        var signals = new List<DetectionSignal>();
        var events = session.Events.OrderBy(e => e.Timestamp).ToList();

        if (events.Count < 2)
        {
            return new DetectionResult
            {
                SessionId = session.SessionId,
                UserId = session.UserId,
                AiProbabilityScore = 0,
                IsLikelyAiAgent = false,
                TotalEventsAnalyzed = events.Count,
                Signals = signals
            };
        }

        // Run each detection heuristic
        signals.Add(AnalyzeTimingRegularity(events));
        signals.Add(AnalyzeActionSpeed(events));
        signals.Add(AnalyzeMouseBehavior(events));
        signals.Add(AnalyzeMouseSpeedProfile(events));    // NEW v2
        signals.Add(AnalyzeKeyboardBehavior(events));
        signals.Add(AnalyzeNavigationPattern(events));
        signals.Add(AnalyzeApiTargeting(events));          // NEW v2
        signals.Add(AnalyzeSessionRhythm(events));

        // v2.1: Hybrid scoring — weighted average PLUS "any two strong signals" rule
        // If two or more signals score above 0.6, that's enough to flag as bot
        // This catches sophisticated bots that evade some signals but not all
        double totalWeight = signals.Sum(s => s.Weight);
        double weightedScore = signals.Sum(s => s.Score * s.Weight) / totalWeight;

        // Count how many signals are firing strongly
        int strongSignals = signals.Count(s => s.Score >= 0.6);
        double maxSignal = signals.Max(s => s.Score);
        double secondMaxSignal = signals.OrderByDescending(s => s.Score).Skip(1).First().Score;

        // Boost score if multiple signals agree the session is suspicious
        double combinedScore = weightedScore;
        if (strongSignals >= 3)
            combinedScore = Math.Max(combinedScore, 0.75); // 3+ strong signals = very likely bot
        else if (strongSignals >= 2 && secondMaxSignal >= 0.6)
            combinedScore = Math.Max(combinedScore, 0.60); // 2 strong signals = likely bot

        // If the single strongest signal is very high, boost
        if (maxSignal >= 0.9)
            combinedScore = Math.Max(combinedScore, weightedScore + 0.1);

        combinedScore = Math.Min(1.0, combinedScore);

        return new DetectionResult
        {
            SessionId = session.SessionId,
            UserId = session.UserId,
            AiProbabilityScore = Math.Round(combinedScore, 4),
            IsLikelyAiAgent = combinedScore >= AiThreshold,
            TotalEventsAnalyzed = events.Count,
            Signals = signals
        };
    }

    /// <summary>
    /// AI agents tend to have very regular intervals between actions.
    /// Humans are erratic - sometimes fast, sometimes slow.
    /// Low standard deviation in timing = suspicious.
    /// </summary>
    private DetectionSignal AnalyzeTimingRegularity(List<ActivityEvent> events)
    {
        var intervals = new List<double>();
        for (int i = 1; i < events.Count; i++)
        {
            var gap = (events[i].Timestamp - events[i - 1].Timestamp).TotalMilliseconds;
            intervals.Add(gap);
        }

        if (intervals.Count == 0)
            return new DetectionSignal { SignalName = "TimingRegularity", Weight = 0.15, Score = 0 };

        double mean = intervals.Average();
        double stdDev = Math.Sqrt(intervals.Sum(x => Math.Pow(x - mean, 2)) / intervals.Count);

        // Coefficient of variation: stdDev / mean
        // Humans typically have CV > 0.7, sophisticated bots 0.3-0.5, obvious bots < 0.2
        double cv = mean > 0 ? stdDev / mean : 0;

        double score;
        if (cv < 0.1) score = 1.0;        // extremely regular = definitely bot
        else if (cv < 0.2) score = 0.9;
        else if (cv < 0.35) score = 0.75;
        else if (cv < 0.5) score = 0.6;   // suspicious zone — challenge bots land here
        else if (cv < 0.7) score = 0.4;   // borderline
        else if (cv < 1.0) score = 0.2;
        else score = 0.1;                  // very irregular = human

        return new DetectionSignal
        {
            SignalName = "TimingRegularity",
            Weight = 0.15,
            Score = score,
            Description = $"Coefficient of variation: {cv:F3}. Lower = more robotic."
        };
    }

    /// <summary>
    /// AI agents can perform actions faster than any human.
    /// Sub-100ms response times for complex actions are suspicious.
    /// Also flags sessions where ALL actions are suspiciously fast (< 500ms).
    /// </summary>
    private DetectionSignal AnalyzeActionSpeed(List<ActivityEvent> events)
    {
        var intervals = new List<double>();
        for (int i = 1; i < events.Count; i++)
        {
            var gap = (events[i].Timestamp - events[i - 1].Timestamp).TotalMilliseconds;
            intervals.Add(gap);
        }

        if (intervals.Count == 0)
            return new DetectionSignal { SignalName = "ActionSpeed", Weight = 0.15, Score = 0 };

        // What percentage of actions happen faster than humanly possible?
        int superFastActions = intervals.Count(i => i < 50);   // < 50ms between actions
        int fastActions = intervals.Count(i => i < 200);       // < 200ms
        int quickActions = intervals.Count(i => i < 500);      // < 500ms — still suspicious in bulk

        double superFastRatio = (double)superFastActions / intervals.Count;
        double fastRatio = (double)fastActions / intervals.Count;
        double quickRatio = (double)quickActions / intervals.Count;

        // v2: Also check if average interval is suspiciously low
        double avgInterval = intervals.Average();
        double avgPenalty = avgInterval < 800 ? 0.3 : avgInterval < 1500 ? 0.1 : 0;

        double score = Math.Min(1.0, superFastRatio * 3.0 + fastRatio * 0.5 + quickRatio * 0.2 + avgPenalty);

        return new DetectionSignal
        {
            SignalName = "ActionSpeed",
            Weight = 0.15,
            Score = Math.Round(score, 4),
            Description = $"{superFastRatio * 100:F1}% under 50ms, {fastRatio * 100:F1}% under 200ms, {quickRatio * 100:F1}% under 500ms. Avg interval: {avgInterval:F0}ms."
        };
    }

    /// <summary>
    /// Human mouse movements have natural curves and acceleration.
    /// Bot movements are linear (straight lines) with constant speed.
    /// </summary>
    private DetectionSignal AnalyzeMouseBehavior(List<ActivityEvent> events)
    {
        var mouseEvents = events.Where(e => e.Mouse != null).ToList();

        if (mouseEvents.Count < 3)
            return new DetectionSignal { SignalName = "MouseBehavior", Weight = 0.10, Score = 0.5, Description = "Insufficient mouse data." };

        int linearMoves = 0;
        int totalMoves = 0;

        for (int i = 2; i < mouseEvents.Count; i++)
        {
            var p1 = mouseEvents[i - 2].Mouse!;
            var p2 = mouseEvents[i - 1].Mouse!;
            var p3 = mouseEvents[i].Mouse!;

            // Check if three consecutive points are collinear (straight line)
            double cross = Math.Abs(
                (p2.X - p1.X) * (p3.Y - p1.Y) - (p3.X - p1.X) * (p2.Y - p1.Y)
            );

            totalMoves++;
            if (cross < 10) // nearly collinear
                linearMoves++;
        }

        // Also check for lack of curves explicitly
        int noCurveCount = mouseEvents.Count(e => e.Mouse!.HasCurve == false);
        double noCurveRatio = (double)noCurveCount / mouseEvents.Count;

        double linearRatio = totalMoves > 0 ? (double)linearMoves / totalMoves : 0;
        double score = Math.Min(1.0, linearRatio * 0.6 + noCurveRatio * 0.4);

        return new DetectionSignal
        {
            SignalName = "MouseBehavior",
            Weight = 0.10,
            Score = Math.Round(score, 4),
            Description = $"Linear movement ratio: {linearRatio:F2}, No-curve ratio: {noCurveRatio:F2}."
        };
    }

    /// <summary>
    /// NEW v2: Analyzes mouse speed characteristics.
    /// Challenge bots have:
    /// - High average speed (>900 px/s vs human avg 697 px/s)
    /// - Low speed variance (CV < 0.25 vs human CV 0.37)
    /// - Speed clustered near the max of human range (1000-1200 px/s)
    /// </summary>
    private DetectionSignal AnalyzeMouseSpeedProfile(List<ActivityEvent> events)
    {
        var mouseEvents = events.Where(e => e.Mouse?.Speed != null).ToList();

        if (mouseEvents.Count < 3)
            return new DetectionSignal { SignalName = "MouseSpeedProfile", Weight = 0.20, Score = 0.5, Description = "Insufficient mouse speed data." };

        var speeds = mouseEvents.Select(e => e.Mouse!.Speed!.Value).ToList();

        double avgSpeed = speeds.Average();
        double stdDev = Math.Sqrt(speeds.Sum(x => Math.Pow(x - avgSpeed, 2)) / speeds.Count);
        double speedCv = avgSpeed > 0 ? stdDev / avgSpeed : 0;

        // Signal 1: Average speed too high (humans avg ~700, bots avg ~1050)
        double speedScore;
        if (avgSpeed > 1100) speedScore = 0.9;
        else if (avgSpeed > 950) speedScore = 0.75;
        else if (avgSpeed > 850) speedScore = 0.6;
        else if (avgSpeed > 750) speedScore = 0.3;
        else speedScore = 0.1;

        // Signal 2: Speed too consistent (low CV = robotic)
        // Humans have CV ~0.37, bots ~0.24
        double consistencyScore;
        if (speedCv < 0.10) consistencyScore = 0.95;
        else if (speedCv < 0.20) consistencyScore = 0.8;
        else if (speedCv < 0.28) consistencyScore = 0.65;  // Challenge bots land here
        else if (speedCv < 0.35) consistencyScore = 0.4;
        else consistencyScore = 0.1;

        // Signal 3: Too many movements at max human speed (>1000 px/s)
        int highSpeedCount = speeds.Count(s => s > 1000);
        double highSpeedRatio = (double)highSpeedCount / speeds.Count;
        double highSpeedScore = highSpeedRatio > 0.7 ? 0.9 : highSpeedRatio > 0.5 ? 0.7 : highSpeedRatio > 0.3 ? 0.4 : 0.1;

        double score = speedScore * 0.4 + consistencyScore * 0.35 + highSpeedScore * 0.25;

        return new DetectionSignal
        {
            SignalName = "MouseSpeedProfile",
            Weight = 0.20,
            Score = Math.Round(score, 4),
            Description = $"Avg speed: {avgSpeed:F0}px/s, Speed CV: {speedCv:F3}, High-speed ratio: {highSpeedRatio:F2}."
        };
    }

    /// <summary>
    /// AI typing is perfectly consistent with zero errors.
    /// Humans have variable inter-key delays and make typos.
    /// </summary>
    private DetectionSignal AnalyzeKeyboardBehavior(List<ActivityEvent> events)
    {
        var keyEvents = events.Where(e => e.Keyboard != null).ToList();

        if (keyEvents.Count < 2)
            return new DetectionSignal { SignalName = "KeyboardBehavior", Weight = 0.10, Score = 0.5, Description = "Insufficient keyboard data." };

        var delays = keyEvents
            .Where(e => e.Keyboard!.InterKeyDelayMs.HasValue)
            .Select(e => e.Keyboard!.InterKeyDelayMs!.Value)
            .ToList();

        double score = 0.5;

        if (delays.Count >= 2)
        {
            double mean = delays.Average();
            double stdDev = Math.Sqrt(delays.Sum(x => Math.Pow(x - mean, 2)) / delays.Count);
            double cv = mean > 0 ? stdDev / mean : 0;

            // Very consistent typing = bot
            double typingScore = cv < 0.1 ? 1.0 : cv < 0.2 ? 0.7 : cv < 0.4 ? 0.3 : 0.1;

            // Zero or near-zero error rate = suspicious
            var errorRates = keyEvents
                .Where(e => e.Keyboard!.ErrorRate.HasValue)
                .Select(e => e.Keyboard!.ErrorRate!.Value)
                .ToList();

            double errorScore = 0.5;
            if (errorRates.Count > 0)
            {
                double avgError = errorRates.Average();
                errorScore = avgError < 0.01 ? 0.9 : avgError < 0.03 ? 0.6 : avgError < 0.05 ? 0.3 : 0.1;
            }

            // v2: Also check if typing speed is superhuman (< 50ms between keys)
            double speedPenalty = mean < 30 ? 0.4 : mean < 60 ? 0.2 : mean < 100 ? 0.1 : 0;

            score = Math.Min(1.0, typingScore * 0.5 + errorScore * 0.3 + speedPenalty + 0.2 * (mean < 100 ? 1.0 : 0.0));
        }

        return new DetectionSignal
        {
            SignalName = "KeyboardBehavior",
            Weight = 0.10,
            Score = Math.Round(score, 4),
            Description = $"Analyzed {keyEvents.Count} keyboard events for consistency and error patterns."
        };
    }

    /// <summary>
    /// AI agents navigate directly to target endpoints without browsing.
    /// v2: Also detects the "browse then target" pattern where bots
    /// pretend to browse before hitting API endpoints.
    /// </summary>
    private DetectionSignal AnalyzeNavigationPattern(List<ActivityEvent> events)
    {
        var allEndpoints = events.Select(e => e.Endpoint).Where(e => !string.IsNullOrEmpty(e)).ToList();

        if (allEndpoints.Count < 2)
            return new DetectionSignal { SignalName = "NavigationPattern", Weight = 0.15, Score = 0.5, Description = "Insufficient navigation data." };

        // Check for API endpoint access (regardless of event type)
        int apiEndpoints = allEndpoints.Count(e => e.StartsWith("/api/"));
        double apiRatio = (double)apiEndpoints / allEndpoints.Count;

        // Navigation efficiency (unique / total)
        int uniqueEndpoints = allEndpoints.Distinct().Count();
        double efficiencyRatio = (double)uniqueEndpoints / allEndpoints.Count;

        // v2: Check for "browse then target" pattern
        // If session starts with browsing pages then switches to API calls
        bool hasBrowseThenTarget = false;
        if (apiEndpoints > 0)
        {
            int firstApiIndex = allEndpoints.FindIndex(e => e.StartsWith("/api/"));
            int browseBeforeApi = allEndpoints.Take(firstApiIndex).Count(e => !e.StartsWith("/api/"));
            if (browseBeforeApi >= 2 && firstApiIndex > allEndpoints.Count * 0.3)
            {
                hasBrowseThenTarget = true; // Suspicious: browsed first, then targeted APIs
            }
        }

        // Sequential rapid navigation (any event type)
        var navEvents = events.Where(e => e.EventType == "navigation" || e.EventType == "api_call").ToList();
        int sequentialApiCalls = 0;
        for (int i = 1; i < navEvents.Count; i++)
        {
            var gap = (navEvents[i].Timestamp - navEvents[i - 1].Timestamp).TotalMilliseconds;
            if (gap < 2000 && navEvents[i].Endpoint.StartsWith("/api/"))
                sequentialApiCalls++;
        }
        double seqRatio = navEvents.Count > 1 ? (double)sequentialApiCalls / (navEvents.Count - 1) : 0;

        // Combined score
        double apiScore = apiRatio > 0.3 ? 0.9 : apiRatio > 0.15 ? 0.7 : apiRatio > 0.05 ? 0.5 : apiRatio > 0 ? 0.3 : 0;
        double browseThenTargetScore = hasBrowseThenTarget ? 0.7 : 0;
        double seqScore = seqRatio > 0.3 ? 0.8 : seqRatio > 0.1 ? 0.5 : 0;

        double score = Math.Min(1.0, apiScore * 0.4 + browseThenTargetScore * 0.3 + seqScore * 0.2 + efficiencyRatio * 0.1);

        return new DetectionSignal
        {
            SignalName = "NavigationPattern",
            Weight = 0.15,
            Score = Math.Round(score, 4),
            Description = $"API ratio: {apiRatio:F2}, Efficiency: {efficiencyRatio:F2}, Browse-then-target: {hasBrowseThenTarget}, Seq API ratio: {seqRatio:F2}."
        };
    }

    /// <summary>
    /// NEW v2: Dedicated signal for API endpoint targeting.
    /// Real humans browsing a website almost NEVER hit /api/ endpoints directly.
    /// Any /api/ access from a browser session is a strong bot indicator.
    /// </summary>
    private DetectionSignal AnalyzeApiTargeting(List<ActivityEvent> events)
    {
        var allEndpoints = events.Select(e => e.Endpoint).Where(e => !string.IsNullOrEmpty(e)).ToList();

        if (allEndpoints.Count == 0)
            return new DetectionSignal { SignalName = "ApiTargeting", Weight = 0.15, Score = 0, Description = "No endpoints to analyze." };

        int apiHits = allEndpoints.Count(e => e.StartsWith("/api/"));
        double apiRatio = (double)apiHits / allEndpoints.Count;

        // Any API access at all is suspicious for a "browser" session
        double score;
        if (apiHits == 0) score = 0.0;          // No API access = normal human
        else if (apiRatio < 0.05) score = 0.3;  // Minimal API access
        else if (apiRatio < 0.10) score = 0.5;
        else if (apiRatio < 0.20) score = 0.7;  // Challenge bots land here (~13%)
        else if (apiRatio < 0.40) score = 0.85;
        else score = 1.0;                        // Heavy API usage = definitely bot

        // Bonus: check for data-extraction patterns (search, list, detail)
        bool hasSearch = allEndpoints.Any(e => e.Contains("search") || e.Contains("q="));
        bool hasList = allEndpoints.Any(e => e.EndsWith("/products") || e.EndsWith("/reviews"));
        bool hasDetail = allEndpoints.Any(e => e.Contains("/products/") && e.Split('/').Length > 3);

        if (hasSearch && hasList && apiHits > 0)
            score = Math.Min(1.0, score + 0.15);

        return new DetectionSignal
        {
            SignalName = "ApiTargeting",
            Weight = 0.15,
            Score = Math.Round(score, 4),
            Description = $"API hits: {apiHits}/{allEndpoints.Count} ({apiRatio * 100:F1}%). Search pattern: {hasSearch && hasList}."
        };
    }

    /// <summary>
    /// Looks at the overall session rhythm.
    /// AI agents don't take breaks, don't hesitate, and maintain constant activity.
    /// Humans have bursts of activity followed by idle periods.
    /// v2: Also checks for "fake pauses" that are too evenly distributed.
    /// </summary>
    private DetectionSignal AnalyzeSessionRhythm(List<ActivityEvent> events)
    {
        var intervals = new List<double>();
        for (int i = 1; i < events.Count; i++)
        {
            intervals.Add((events[i].Timestamp - events[i - 1].Timestamp).TotalMilliseconds);
        }

        if (intervals.Count < 5)
            return new DetectionSignal { SignalName = "SessionRhythm", Weight = 0.05, Score = 0.5, Description = "Insufficient data for rhythm analysis." };

        // Count "pauses" (gaps > 3 seconds) - humans pause to think
        int pauses = intervals.Count(i => i > 3000);
        double pauseRatio = (double)pauses / intervals.Count;

        // Count "idle gaps" (gaps > 10 seconds) - humans get distracted
        int idleGaps = intervals.Count(i => i > 10000);

        // v2: Check if pauses are too evenly spaced (bots add fake pauses at regular intervals)
        double pauseRegularity = 0;
        if (pauses >= 2)
        {
            var pauseIndices = new List<int>();
            for (int i = 0; i < intervals.Count; i++)
            {
                if (intervals[i] > 3000) pauseIndices.Add(i);
            }

            if (pauseIndices.Count >= 2)
            {
                var pauseGaps = new List<int>();
                for (int i = 1; i < pauseIndices.Count; i++)
                {
                    pauseGaps.Add(pauseIndices[i] - pauseIndices[i - 1]);
                }

                if (pauseGaps.Count > 0)
                {
                    double pauseMean = pauseGaps.Average();
                    double pauseStd = Math.Sqrt(pauseGaps.Sum(x => Math.Pow(x - pauseMean, 2)) / pauseGaps.Count);
                    pauseRegularity = pauseMean > 0 ? pauseStd / pauseMean : 0;
                    // If pauses are very regularly spaced (low CV), they might be fake
                }
            }
        }

        // AI agents have zero or near-zero pauses
        double score;
        if (pauseRatio < 0.02 && idleGaps == 0) score = 0.95;
        else if (pauseRatio < 0.05) score = 0.7;
        else if (pauseRatio < 0.10) score = 0.5;
        else if (pauseRatio < 0.15) score = 0.35;
        else score = 0.1; // lots of pauses = human

        // v2: Penalize if pauses are too regularly spaced
        if (pauseRegularity < 0.3 && pauses >= 2)
            score = Math.Min(1.0, score + 0.2); // Fake pauses detected

        return new DetectionSignal
        {
            SignalName = "SessionRhythm",
            Weight = 0.05,
            Score = Math.Round(score, 4),
            Description = $"Pause ratio: {pauseRatio:F2}, Idle gaps: {idleGaps}, Pause regularity CV: {pauseRegularity:F2}."
        };
    }
}
