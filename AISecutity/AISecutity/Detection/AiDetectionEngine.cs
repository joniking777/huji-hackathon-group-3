using AISecutity.Models;

namespace AISecutity.Detection;

/// <summary>
/// Core AI agent detection algorithm.
/// Analyzes behavioral patterns to distinguish AI agents from human users.
/// 
/// Key signals:
/// 1. Timing regularity - AI agents have unnaturally consistent intervals
/// 2. Speed - AI can act faster than humanly possible
/// 3. Mouse linearity - bots move in straight lines, humans curve
/// 4. Keyboard patterns - AI types at constant speed with no typos
/// 5. Session patterns - AI follows predictable sequences
/// 6. Navigation patterns - AI doesn't browse, it targets endpoints directly
/// </summary>
public class AiDetectionEngine : IAiDetectionEngine
{
    private const double AiThreshold = 0.65; // above this = likely AI

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
        signals.Add(AnalyzeKeyboardBehavior(events));
        signals.Add(AnalyzeNavigationPattern(events));
        signals.Add(AnalyzeSessionRhythm(events));

        // Weighted score calculation
        double totalWeight = signals.Sum(s => s.Weight);
        double weightedScore = signals.Sum(s => s.Score * s.Weight) / totalWeight;

        return new DetectionResult
        {
            SessionId = session.SessionId,
            UserId = session.UserId,
            AiProbabilityScore = Math.Round(weightedScore, 4),
            IsLikelyAiAgent = weightedScore >= AiThreshold,
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
            return new DetectionSignal { SignalName = "TimingRegularity", Weight = 0.25, Score = 0 };

        double mean = intervals.Average();
        double stdDev = Math.Sqrt(intervals.Sum(x => Math.Pow(x - mean, 2)) / intervals.Count);

        // Coefficient of variation: stdDev / mean
        // Humans typically have CV > 0.5, AI agents < 0.2
        double cv = mean > 0 ? stdDev / mean : 0;

        double score;
        if (cv < 0.1) score = 1.0;       // extremely regular = definitely bot
        else if (cv < 0.2) score = 0.85;
        else if (cv < 0.35) score = 0.6;
        else if (cv < 0.5) score = 0.3;
        else score = 0.1;                  // very irregular = human

        return new DetectionSignal
        {
            SignalName = "TimingRegularity",
            Weight = 0.25,
            Score = score,
            Description = $"Coefficient of variation: {cv:F3}. Lower = more robotic."
        };
    }

    /// <summary>
    /// AI agents can perform actions faster than any human.
    /// Sub-100ms response times for complex actions are suspicious.
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
            return new DetectionSignal { SignalName = "ActionSpeed", Weight = 0.20, Score = 0 };

        // What percentage of actions happen faster than humanly possible?
        int superFastActions = intervals.Count(i => i < 50);   // < 50ms between actions
        int fastActions = intervals.Count(i => i < 200);       // < 200ms

        double superFastRatio = (double)superFastActions / intervals.Count;
        double fastRatio = (double)fastActions / intervals.Count;

        double score = Math.Min(1.0, superFastRatio * 3.0 + fastRatio * 0.5);

        return new DetectionSignal
        {
            SignalName = "ActionSpeed",
            Weight = 0.20,
            Score = Math.Round(score, 4),
            Description = $"{superFastRatio * 100:F1}% actions under 50ms, {fastRatio * 100:F1}% under 200ms."
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
            return new DetectionSignal { SignalName = "MouseBehavior", Weight = 0.15, Score = 0.5, Description = "Insufficient mouse data." };

        int linearMoves = 0;
        int totalMoves = 0;

        for (int i = 2; i < mouseEvents.Count; i++)
        {
            var p1 = mouseEvents[i - 2].Mouse!;
            var p2 = mouseEvents[i - 1].Mouse!;
            var p3 = mouseEvents[i].Mouse!;

            // Check if three consecutive points are collinear (straight line)
            // Using cross product: if ~0, points are on a line
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
            Weight = 0.15,
            Score = Math.Round(score, 4),
            Description = $"Linear movement ratio: {linearRatio:F2}, No-curve ratio: {noCurveRatio:F2}."
        };
    }

    /// <summary>
    /// AI typing is perfectly consistent with zero errors.
    /// Humans have variable inter-key delays and make typos.
    /// </summary>
    private DetectionSignal AnalyzeKeyboardBehavior(List<ActivityEvent> events)
    {
        var keyEvents = events.Where(e => e.Keyboard != null).ToList();

        if (keyEvents.Count < 3)
            return new DetectionSignal { SignalName = "KeyboardBehavior", Weight = 0.15, Score = 0.5, Description = "Insufficient keyboard data." };

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

            // Zero error rate = suspicious
            var errorRates = keyEvents
                .Where(e => e.Keyboard!.ErrorRate.HasValue)
                .Select(e => e.Keyboard!.ErrorRate!.Value)
                .ToList();

            double errorScore = 0.5;
            if (errorRates.Count > 0)
            {
                double avgError = errorRates.Average();
                errorScore = avgError < 0.01 ? 0.9 : avgError < 0.03 ? 0.5 : 0.1;
            }

            score = typingScore * 0.6 + errorScore * 0.4;
        }

        return new DetectionSignal
        {
            SignalName = "KeyboardBehavior",
            Weight = 0.15,
            Score = Math.Round(score, 4),
            Description = $"Analyzed {keyEvents.Count} keyboard events for consistency and error patterns."
        };
    }

    /// <summary>
    /// AI agents navigate directly to target endpoints without browsing.
    /// Humans explore, go back, visit unrelated pages.
    /// </summary>
    private DetectionSignal AnalyzeNavigationPattern(List<ActivityEvent> events)
    {
        var navEvents = events.Where(e => e.EventType == "navigation" || e.EventType == "api_call").ToList();

        if (navEvents.Count < 2)
            return new DetectionSignal { SignalName = "NavigationPattern", Weight = 0.15, Score = 0.5, Description = "Insufficient navigation data." };

        // Check for sequential endpoint access (no backtracking)
        var endpoints = navEvents.Select(e => e.Endpoint).ToList();
        int uniqueEndpoints = endpoints.Distinct().Count();
        int totalNavigations = endpoints.Count;

        // AI agents rarely revisit pages (efficiency ratio close to 1.0)
        double efficiencyRatio = (double)uniqueEndpoints / totalNavigations;

        // Check if endpoints follow a logical API sequence (e.g., list -> get -> update)
        int sequentialApiCalls = 0;
        for (int i = 1; i < navEvents.Count; i++)
        {
            var gap = (navEvents[i].Timestamp - navEvents[i - 1].Timestamp).TotalMilliseconds;
            if (gap < 500 && navEvents[i].EventType == "api_call")
                sequentialApiCalls++;
        }

        double seqRatio = (double)sequentialApiCalls / Math.Max(1, navEvents.Count - 1);

        // High efficiency + rapid sequential API calls = bot
        double score = Math.Min(1.0, efficiencyRatio * 0.4 + seqRatio * 0.6);

        return new DetectionSignal
        {
            SignalName = "NavigationPattern",
            Weight = 0.15,
            Score = Math.Round(score, 4),
            Description = $"Navigation efficiency: {efficiencyRatio:F2}, Sequential API ratio: {seqRatio:F2}."
        };
    }

    /// <summary>
    /// Looks at the overall session rhythm.
    /// AI agents don't take breaks, don't hesitate, and maintain constant activity.
    /// Humans have bursts of activity followed by idle periods.
    /// </summary>
    private DetectionSignal AnalyzeSessionRhythm(List<ActivityEvent> events)
    {
        var intervals = new List<double>();
        for (int i = 1; i < events.Count; i++)
        {
            intervals.Add((events[i].Timestamp - events[i - 1].Timestamp).TotalMilliseconds);
        }

        if (intervals.Count < 5)
            return new DetectionSignal { SignalName = "SessionRhythm", Weight = 0.10, Score = 0.5, Description = "Insufficient data for rhythm analysis." };

        // Count "pauses" (gaps > 3 seconds) - humans pause to think
        int pauses = intervals.Count(i => i > 3000);
        double pauseRatio = (double)pauses / intervals.Count;

        // Count "idle gaps" (gaps > 10 seconds) - humans get distracted
        int idleGaps = intervals.Count(i => i > 10000);

        // AI agents have zero or near-zero pauses
        double score;
        if (pauseRatio < 0.02 && idleGaps == 0) score = 0.95;
        else if (pauseRatio < 0.05) score = 0.7;
        else if (pauseRatio < 0.15) score = 0.4;
        else score = 0.1; // lots of pauses = human

        return new DetectionSignal
        {
            SignalName = "SessionRhythm",
            Weight = 0.10,
            Score = Math.Round(score, 4),
            Description = $"Pause ratio: {pauseRatio:F2}, Idle gaps: {idleGaps}. No pauses = bot-like."
        };
    }
}
