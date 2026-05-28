namespace AISecutity.Models;

/// <summary>
/// A batch of activity events for a single session, as provided by the data team's JSON.
/// </summary>
public class ActivitySession
{
    public string SessionId { get; set; } = string.Empty;
    public string UserId { get; set; } = string.Empty;
    public string UserAgent { get; set; } = string.Empty;
    public string IpAddress { get; set; } = string.Empty;
    public List<ActivityEvent> Events { get; set; } = new();
}
