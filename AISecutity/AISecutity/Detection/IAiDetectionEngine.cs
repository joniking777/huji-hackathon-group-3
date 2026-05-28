using AISecutity.Models;

namespace AISecutity.Detection;

public interface IAiDetectionEngine
{
    DetectionResult Analyze(ActivitySession session);
    DetectionResult Analyze(ActivitySession session, SessionContext? context);
}

/// <summary>
/// Context about the user's history — used to adjust thresholds.
/// Returning users who've been human before get more leeway.
/// </summary>
public class SessionContext
{
    /// <summary>How many previous sessions this user/IP has had.</summary>
    public int PreviousSessionCount { get; set; }

    /// <summary>How many of those were flagged as bot.</summary>
    public int PreviousBotFlags { get; set; }

    /// <summary>Average score across previous sessions.</summary>
    public double AverageHistoricalScore { get; set; }

    /// <summary>Whether this user has ever been verified (CAPTCHA, login, etc.).</summary>
    public bool IsVerifiedUser { get; set; }

    /// <summary>Is this a first-time visitor?</summary>
    public bool IsFirstVisit => PreviousSessionCount == 0;

    /// <summary>Has this user been consistently human?</summary>
    public bool HasCleanHistory => PreviousSessionCount >= 3 && PreviousBotFlags == 0 && AverageHistoricalScore < 0.3;
}
