namespace AISecutity.Data.Entities;

/// <summary>
/// Records a security incident when anomalous behavior is detected.
/// Covers all four data categories: Identity, Request Anatomy, Behavioral Patterns, Security Telemetry.
/// </summary>
public class SecurityIncident
{
    public int Id { get; set; }

    // === Identity & Fingerprint ===
    public string IpAddress { get; set; } = string.Empty;
    public string? SessionId { get; set; }
    public string? UserId { get; set; }
    public string? UserAgent { get; set; }
    public string? DeviceFingerprint { get; set; }

    // === Request Anatomy ===
    public string? TargetUrl { get; set; }
    public string? HttpMethod { get; set; }
    public string? RawHeaders { get; set; } // JSON serialized
    public string? PayloadSnippet { get; set; } // first 500 chars of body

    // === Behavioral Patterns ===
    public double RequestVelocity { get; set; } // requests per minute
    public double ErrorRate { get; set; } // 4xx/5xx ratio
    public string? NavigationPath { get; set; } // JSON array of visited endpoints
    public int LoginFailures { get; set; }
    public int TotalEventsInSession { get; set; }

    // === Security Telemetry ===
    public double RiskScore { get; set; } // 0.0 to 1.0 from detection engine
    public string? TriggeredSignals { get; set; } // JSON array of signal names + scores
    public string? ReputationFlag { get; set; } // "known_bot", "suspicious", "clean"
    public string AppliedPenalty { get; set; } = "none"; // "block", "tarpit", "captcha", "mfa", "none"

    // Timing
    public DateTime DetectedAt { get; set; } = DateTime.UtcNow;
    public string IncidentType { get; set; } = "bot_detected"; // "bot_detected", "brute_force", "scraping", "rate_limit"
}
