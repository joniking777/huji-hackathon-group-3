namespace AISecutity.Middleware;

/// <summary>
/// Configuration options for the AI blocking middleware.
/// </summary>
public class AiBlockingOptions
{
    /// <summary>
    /// Minimum number of events to collect before running detection.
    /// Too few events = unreliable results. Default: 5.
    /// </summary>
    public int MinEventsBeforeAnalysis { get; set; } = 5;

    /// <summary>
    /// Maximum number of recent events to feed into the detection engine.
    /// Keeps memory bounded. Default: 100.
    /// </summary>
    public int MaxEventsToAnalyze { get; set; } = 100;

    /// <summary>
    /// AI probability score at which to block the session.
    /// Must be between 0.0 and 1.0. Default: 0.75 (stricter than detection threshold).
    /// </summary>
    public double BlockingThreshold { get; set; } = 0.75;

    /// <summary>
    /// Paths that should not be monitored or blocked.
    /// Typically health checks, the detection API itself, static files, etc.
    /// </summary>
    public List<string> ExcludedPaths { get; set; } = new()
    {
        "/api/detection",
        "/health",
        "/swagger",
        "/openapi"
    };

    /// <summary>
    /// Whether to add the AI score as a response header (useful for debugging).
    /// </summary>
    public bool IncludeScoreHeader { get; set; } = true;
}
