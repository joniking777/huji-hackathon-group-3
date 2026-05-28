namespace AISecutity.Models;

/// <summary>
/// Represents a single user activity event from the JSON data.
/// Your other team produces these as JSON arrays.
/// </summary>
public class ActivityEvent
{
    public string SessionId { get; set; } = string.Empty;
    public string UserId { get; set; } = string.Empty;
    public DateTime Timestamp { get; set; }
    public string EventType { get; set; } = string.Empty; // click, scroll, keypress, navigation, api_call, form_submit
    public string Endpoint { get; set; } = string.Empty;
    public int? DurationMs { get; set; } // time spent on action
    public MouseData? Mouse { get; set; }
    public KeyboardData? Keyboard { get; set; }
    public Dictionary<string, object>? Metadata { get; set; }
}

public class MouseData
{
    public int X { get; set; }
    public int Y { get; set; }
    public double? Speed { get; set; } // pixels per second
    public bool? HasCurve { get; set; } // human mouse movements curve, bots go straight
}

public class KeyboardData
{
    public double? InterKeyDelayMs { get; set; } // time between keystrokes
    public int? BurstLength { get; set; } // how many keys in rapid succession
    public double? ErrorRate { get; set; } // typos / corrections
}
