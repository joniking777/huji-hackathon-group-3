namespace AISecutity.Data.Entities;

/// <summary>
/// Logs every request for velocity tracking and pattern analysis.
/// Used by the rate limiter to calculate request velocity per IP/session.
/// </summary>
public class RequestLog
{
    public int Id { get; set; }
    public string IpAddress { get; set; } = string.Empty;
    public string? SessionId { get; set; }
    public string Endpoint { get; set; } = string.Empty;
    public string HttpMethod { get; set; } = "GET";
    public int StatusCode { get; set; }
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;
    public int ResponseTimeMs { get; set; }
}
