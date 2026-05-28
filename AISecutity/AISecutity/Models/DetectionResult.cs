namespace AISecutity.Models;

/// <summary>
/// The output of the AI detection algorithm.
/// </summary>
public class DetectionResult
{
    public string SessionId { get; set; } = string.Empty;
    public string UserId { get; set; } = string.Empty;
    public double AiProbabilityScore { get; set; } // 0.0 (human) to 1.0 (definitely AI)
    public bool IsLikelyAiAgent { get; set; }
    public string RecommendedAction { get; set; } = "allow"; // "allow", "monitor", "challenge", "block"
    public string ThreatLevel { get; set; } = "none"; // "none", "low", "medium", "high", "critical"
    public bool IsReturningUser { get; set; }
    public List<DetectionSignal> Signals { get; set; } = new();
    public DateTime AnalyzedAt { get; set; } = DateTime.UtcNow;
    public int TotalEventsAnalyzed { get; set; }
}

public class DetectionSignal
{
    public string SignalName { get; set; } = string.Empty;
    public double Weight { get; set; } // how much this contributes to the score
    public double Score { get; set; } // 0.0 to 1.0
    public string Description { get; set; } = string.Empty;
}
