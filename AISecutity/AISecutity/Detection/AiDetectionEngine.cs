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
    // Tiered thresholds — separate "monitor", "challenge", and "block" levels
    private const double MonitorThreshold = 0.40;   // Log it, watch closely
    private const double ChallengeThreshold = 0.60; // Show CAPTCHA
    private const double BlockThreshold = 0.75;     // Hard block

    // Threshold adjustments based on user history
    private const double FirstVisitBonus = 0.10;    // First-timers get +0.10 threshold (more lenient)
    private const double CleanHistoryBonus = 0.15;  // Users with clean history get +0.15
    private const double VerifiedUserBonus = 0.20;  // Verified users get +0.20

    public DetectionResult Analyze(ActivitySession session)
    {
        return Analyze(session, null);
    }

    public DetectionResult Analyze(ActivitySession session, SessionContext? context)
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
                RecommendedAction = "allow",
                ThreatLevel = "none",
                TotalEventsAnalyzed = events.Count,
                Signals = signals
            };
        }

        // Run each detection heuristic
        signals.Add(AnalyzeTimingRegularity(events));
        signals.Add(AnalyzeTimingJitter(events));
        signals.Add(AnalyzeActionSpeed(events));
        signals.Add(AnalyzeMouseBehavior(events));
        signals.Add(AnalyzeMouseSpeedProfile(events));
        signals.Add(AnalyzeKeyboardBehavior(events));
        signals.Add(AnalyzeNavigationPattern(events));
        signals.Add(AnalyzeNavigationBehavior(events));
        signals.Add(AnalyzeApiTargeting(events));
        signals.Add(AnalyzeSessionRhythm(events));

        // Weighted score calculation
        double totalWeight = signals.Sum(s => s.Weight);
        double weightedScore = signals.Sum(s => s.Score * s.Weight) / totalWeight;

        // Hybrid boost: multiple strong signals firing together
        int strongSignals = signals.Count(s => s.Score >= 0.6);
        double maxSignal = signals.Max(s => s.Score);
        double secondMaxSignal = signals.OrderByDescending(s => s.Score).Skip(1).First().Score;

        double combinedScore = weightedScore;
        if (strongSignals >= 3)
            combinedScore = Math.Max(combinedScore, 0.75);
        else if (strongSignals >= 2 && secondMaxSignal >= 0.6)
            combinedScore = Math.Max(combinedScore, 0.60);

        if (maxSignal >= 0.9)
            combinedScore = Math.Max(combinedScore, weightedScore + 0.1);

        combinedScore = Math.Min(1.0, combinedScore);

        // === SESSION HISTORY ADJUSTMENT ===
        // Adjust effective thresholds based on user history
        double effectiveBlockThreshold = BlockThreshold;
        double effectiveChallengeThreshold = ChallengeThreshold;
        double effectiveMonitorThreshold = MonitorThreshold;
        bool isReturning = false;

        if (context != null)
        {
            isReturning = !context.IsFirstVisit;

            if (context.IsVerifiedUser)
            {
                // Verified users (logged in, passed CAPTCHA before) get maximum leeway
                effectiveBlockThreshold += VerifiedUserBonus;
                effectiveChallengeThreshold += VerifiedUserBonus;
                effectiveMonitorThreshold += VerifiedUserBonus;
            }
            else if (context.HasCleanHistory)
            {
                // Users with 3+ clean sessions get significant leeway
                effectiveBlockThreshold += CleanHistoryBonus;
                effectiveChallengeThreshold += CleanHistoryBonus;
                effectiveMonitorThreshold += CleanHistoryBonus;
            }
            else if (context.IsFirstVisit)
            {
                // First-time visitors get slight leeway (benefit of the doubt)
                effectiveBlockThreshold += FirstVisitBonus;
                effectiveChallengeThreshold += FirstVisitBonus;
            }

            // If user has previous bot flags, LOWER the threshold (stricter)
            if (context.PreviousBotFlags > 0)
            {
                double penalty = Math.Min(0.15, context.PreviousBotFlags * 0.05);
                effectiveBlockThreshold -= penalty;
                effectiveChallengeThreshold -= penalty;
            }
        }

        // === DETERMINE ACTION TIER ===
        string action;
        string threatLevel;
        bool isLikelyBot;

        if (combinedScore >= effectiveBlockThreshold)
        {
            action = "block";
            threatLevel = "critical";
            isLikelyBot = true;
        }
        else if (combinedScore >= effectiveChallengeThreshold)
        {
            action = "challenge";
            threatLevel = "high";
            isLikelyBot = true;
        }
        else if (combinedScore >= effectiveMonitorThreshold)
        {
            action = "monitor";
            threatLevel = "medium";
            isLikelyBot = false; // Don't flag as bot yet, just watch
        }
        else
        {
            action = "allow";
            threatLevel = combinedScore > 0.20 ? "low" : "none";
            isLikelyBot = false;
        }

        return new DetectionResult
        {
            SessionId = session.SessionId,
            UserId = session.UserId,
            AiProbabilityScore = Math.Round(combinedScore, 4),
            IsLikelyAiAgent = isLikelyBot,
            RecommendedAction = action,
            ThreatLevel = threatLevel,
            IsReturningUser = isReturning,
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
    /// NEW v3: Timing Jitter Analysis — specifically catches DrissionPage and similar tools.
    /// 
    /// DrissionPage signature: page loads take ~6000ms ± 200ms (very tight cluster).
    /// The "jitter" between consecutive intervals is suspiciously low.
    /// 
    /// Real humans have HIGH jitter — the difference between one action and the next
    /// varies wildly (sometimes 1s, sometimes 8s, sometimes 20s).
    /// 
    /// Bots (especially browser automation) have LOW jitter because:
    /// - Page load times are consistent (network + render = fixed cost)
    /// - Sleep/wait commands produce uniform delays
    /// - No human hesitation, distraction, or reading time
    /// 
    /// We measure:
    /// 1. Inter-interval jitter (difference between consecutive intervals)
    /// 2. Clustering (do intervals cluster around a single value?)
    /// 3. Absence of outliers (humans always have some very long/short gaps)
    /// </summary>
    private DetectionSignal AnalyzeTimingJitter(List<ActivityEvent> events)
    {
        var intervals = new List<double>();
        for (int i = 1; i < events.Count; i++)
        {
            var gap = (events[i].Timestamp - events[i - 1].Timestamp).TotalMilliseconds;
            intervals.Add(gap);
        }

        if (intervals.Count < 4)
            return new DetectionSignal { SignalName = "TimingJitter", Weight = 0.15, Score = 0.5, Description = "Insufficient data for jitter analysis." };

        // 1. Inter-interval jitter: how much does each gap differ from the previous gap?
        // Low jitter = bot (each action takes roughly the same time as the last)
        var jitters = new List<double>();
        for (int i = 1; i < intervals.Count; i++)
        {
            jitters.Add(Math.Abs(intervals[i] - intervals[i - 1]));
        }

        double meanInterval = intervals.Average();
        double meanJitter = jitters.Average();

        // Normalize jitter relative to mean interval
        // Humans: jitter/mean > 0.5 (highly variable)
        // DrissionPage: jitter/mean < 0.1 (almost identical intervals)
        double jitterRatio = meanInterval > 0 ? meanJitter / meanInterval : 0;

        // 2. Clustering: what % of intervals fall within ±15% of the median?
        double median = intervals.OrderBy(x => x).ElementAt(intervals.Count / 2);
        double clusterBand = median * 0.15; // ±15%
        int clustered = intervals.Count(i => Math.Abs(i - median) < clusterBand);
        double clusterRatio = (double)clustered / intervals.Count;

        // 3. Outlier absence: humans always have at least some intervals that are
        // 3x longer or 3x shorter than the median
        int outliers = intervals.Count(i => i > median * 3 || i < median / 3);
        double outlierRatio = (double)outliers / intervals.Count;
        bool hasNoOutliers = outlierRatio < 0.05;

        // Score calculation
        double jitterScore;
        if (jitterRatio < 0.05) jitterScore = 1.0;       // Almost zero jitter = definitely bot
        else if (jitterRatio < 0.10) jitterScore = 0.9;   // DrissionPage lands here
        else if (jitterRatio < 0.20) jitterScore = 0.7;
        else if (jitterRatio < 0.35) jitterScore = 0.5;
        else if (jitterRatio < 0.50) jitterScore = 0.3;
        else jitterScore = 0.1;                            // High jitter = human

        double clusterScore;
        if (clusterRatio > 0.85) clusterScore = 0.95;     // >85% of intervals in tight cluster
        else if (clusterRatio > 0.70) clusterScore = 0.75;
        else if (clusterRatio > 0.50) clusterScore = 0.5;
        else clusterScore = 0.1;

        double outlierScore = hasNoOutliers ? 0.7 : 0.1;

        double score = jitterScore * 0.50 + clusterScore * 0.30 + outlierScore * 0.20;

        return new DetectionSignal
        {
            SignalName = "TimingJitter",
            Weight = 0.15,
            Score = Math.Round(score, 4),
            Description = $"Jitter ratio: {jitterRatio:F3} (lower=bot), Cluster: {clusterRatio:F2}, Outliers: {outlierRatio:F2}."
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
    /// NEW v3: Navigation Behavior — catches Stealth Crawlers.
    /// 
    /// Stealth crawlers visit pages in sequential/systematic order and never revisit.
    /// Real humans:
    /// - Revisit pages (back button, re-reading)
    /// - Skip around randomly (not sequential)
    /// - Have "favorite" pages they return to
    /// 
    /// Signals:
    /// 1. Revisit ratio: humans revisit ~15% of pages, bots 0%
    /// 2. Sequential pattern: visiting /products/1, /2, /3... in order
    /// 3. Coverage efficiency: bots visit many unique pages with zero waste
    /// </summary>
    private DetectionSignal AnalyzeNavigationBehavior(List<ActivityEvent> events)
    {
        var endpoints = events
            .Select(e => e.Endpoint)
            .Where(e => !string.IsNullOrEmpty(e))
            .ToList();

        if (endpoints.Count < 5)
            return new DetectionSignal { SignalName = "NavigationBehavior", Weight = 0.12, Score = 0.5, Description = "Insufficient navigation data." };

        // 1. Revisit ratio: how often does the user go back to a previously visited page?
        int revisits = 0;
        var visited = new HashSet<string>();
        for (int i = 0; i < endpoints.Count; i++)
        {
            if (visited.Contains(endpoints[i]))
                revisits++;
            visited.Add(endpoints[i]);
        }
        double revisitRatio = (double)revisits / endpoints.Count;

        // Humans revisit 10-30% of pages. Bots almost never revisit (0-5%).
        double revisitScore;
        if (revisitRatio < 0.02) revisitScore = 0.9;       // Never revisits = bot
        else if (revisitRatio < 0.05) revisitScore = 0.7;
        else if (revisitRatio < 0.10) revisitScore = 0.5;
        else if (revisitRatio < 0.20) revisitScore = 0.3;
        else revisitScore = 0.1;                            // Lots of revisits = human

        // 2. Sequential pattern detection: are numbered pages visited in order?
        // e.g., /products/1, /products/2, /products/3...
        int sequentialPairs = 0;
        int totalPairs = 0;
        for (int i = 1; i < endpoints.Count; i++)
        {
            // Extract trailing numbers from paths
            var num1 = ExtractTrailingNumber(endpoints[i - 1]);
            var num2 = ExtractTrailingNumber(endpoints[i]);

            if (num1.HasValue && num2.HasValue)
            {
                totalPairs++;
                if (num2.Value == num1.Value + 1) // Sequential: 1→2, 2→3, etc.
                    sequentialPairs++;
            }
        }
        double seqRatio = totalPairs > 0 ? (double)sequentialPairs / totalPairs : 0;

        double seqScore;
        if (seqRatio > 0.6) seqScore = 0.95;    // Clearly sequential crawling
        else if (seqRatio > 0.4) seqScore = 0.7;
        else if (seqRatio > 0.2) seqScore = 0.4;
        else seqScore = 0.1;                      // Random order = human

        // 3. Consecutive same-page ratio: humans often stay on a page (scroll, click within)
        // Bots move to a new page every action
        int samePage = 0;
        for (int i = 1; i < endpoints.Count; i++)
        {
            if (endpoints[i] == endpoints[i - 1])
                samePage++;
        }
        double samePageRatio = (double)samePage / (endpoints.Count - 1);

        // Humans stay on same page ~30-50% of actions (scrolling, clicking within page)
        // Bots change page almost every action (samePageRatio < 10%)
        double stayScore;
        if (samePageRatio < 0.05) stayScore = 0.85;   // Never stays = bot
        else if (samePageRatio < 0.15) stayScore = 0.6;
        else if (samePageRatio < 0.25) stayScore = 0.3;
        else stayScore = 0.1;                           // Stays often = human

        double score = revisitScore * 0.40 + seqScore * 0.30 + stayScore * 0.30;

        return new DetectionSignal
        {
            SignalName = "NavigationBehavior",
            Weight = 0.12,
            Score = Math.Round(score, 4),
            Description = $"Revisit ratio: {revisitRatio:F2} (low=bot), Sequential: {seqRatio:F2}, Same-page: {samePageRatio:F2}."
        };
    }

    private int? ExtractTrailingNumber(string path)
    {
        if (string.IsNullOrEmpty(path)) return null;
        var parts = path.TrimEnd('/').Split('/');
        var last = parts.LastOrDefault();
        if (int.TryParse(last, out int num)) return num;
        return null;
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
