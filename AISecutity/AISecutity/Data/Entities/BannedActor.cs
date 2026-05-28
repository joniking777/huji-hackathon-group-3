namespace AISecutity.Data.Entities;

/// <summary>
/// Represents a banned actor (IP, session, or fingerprint).
/// Supports both temporary bans (rate limiting) and permanent bans.
/// </summary>
public class BannedActor
{
    public int Id { get; set; }

    // Identity & Fingerprint
    public string IpAddress { get; set; } = string.Empty;
    public string? SessionId { get; set; }
    public string? UserId { get; set; }
    public string? DeviceFingerprint { get; set; }
    public string? UserAgent { get; set; }

    // Ban details
    public string BanType { get; set; } = "temporary"; // "temporary", "permanent", "tarpit"
    public string Reason { get; set; } = string.Empty;
    public double RiskScore { get; set; }
    public string? TriggeredRule { get; set; } // which detection signal triggered the ban

    // Timing
    public DateTime BannedAt { get; set; } = DateTime.UtcNow;
    public DateTime? ExpiresAt { get; set; } // null = permanent
    public DateTime? LiftedAt { get; set; }  // when ban was manually lifted

    // Penalty applied
    public string Penalty { get; set; } = "block"; // "block", "tarpit", "captcha", "mfa"
    public int? TarpitDelayMs { get; set; } // if penalty is tarpit, how much delay

    // Audit
    public int TotalIncidents { get; set; } = 1;
    public DateTime LastSeenAt { get; set; } = DateTime.UtcNow;

    public bool IsActive => LiftedAt == null && (ExpiresAt == null || ExpiresAt > DateTime.UtcNow);
}
