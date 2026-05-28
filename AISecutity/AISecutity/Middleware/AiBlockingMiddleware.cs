using System.Collections.Concurrent;
using AISecutity.Detection;
using AISecutity.Models;
using Microsoft.Extensions.Options;

namespace AISecutity.Middleware;

/// <summary>
/// Middleware that monitors incoming requests for AI agent behavior patterns.
/// When a session accumulates enough suspicious signals, further requests are blocked.
/// 
/// How it works:
/// 1. Each request is tracked by session (cookie or IP-based).
/// 2. Behavioral events (timing, speed, patterns) are recorded per session.
/// 3. After a minimum number of events, the detection engine scores the session.
/// 4. If the score exceeds the threshold, the session is blocked with 403.
/// </summary>
public class AiBlockingMiddleware
{
    private readonly RequestDelegate _next;
    private readonly IAiDetectionEngine _engine;
    private readonly AiBlockingOptions _options;
    private readonly ILogger<AiBlockingMiddleware> _logger;

    // In-memory session tracking (use distributed cache in production)
    private static readonly ConcurrentDictionary<string, TrackedSession> _sessions = new();

    public AiBlockingMiddleware(
        RequestDelegate next,
        IAiDetectionEngine engine,
        IOptions<AiBlockingOptions> options,
        ILogger<AiBlockingMiddleware> logger)
    {
        _next = next;
        _engine = engine;
        _options = options.Value;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        // Skip paths that should not be monitored (health checks, the detection API itself, etc.)
        if (ShouldSkip(context.Request.Path))
        {
            await _next(context);
            return;
        }

        var sessionId = GetSessionId(context);
        var tracked = _sessions.GetOrAdd(sessionId, _ => new TrackedSession(sessionId));

        // Check if already blocked
        if (tracked.IsBlocked)
        {
            _logger.LogWarning("Blocked AI agent request from session {SessionId}, IP: {IP}",
                sessionId, context.Connection.RemoteIpAddress);

            context.Response.StatusCode = StatusCodes.Status403Forbidden;
            context.Response.ContentType = "application/json";
            await context.Response.WriteAsync(System.Text.Json.JsonSerializer.Serialize(new
            {
                error = "Access denied",
                reason = "Automated agent behavior detected",
                score = tracked.LastScore,
                sessionId
            }));
            return;
        }

        // Record this request as an activity event
        var activityEvent = BuildActivityEvent(context, tracked, sessionId);
        tracked.Events.Add(activityEvent);
        tracked.LastRequestTime = DateTime.UtcNow;
        tracked.RequestCount++;

        // Run detection once we have enough events
        if (tracked.Events.Count >= _options.MinEventsBeforeAnalysis)
        {
            var session = new ActivitySession
            {
                SessionId = sessionId,
                UserId = sessionId,
                UserAgent = context.Request.Headers.UserAgent.ToString(),
                IpAddress = context.Connection.RemoteIpAddress?.ToString() ?? "unknown",
                Events = tracked.Events.TakeLast(_options.MaxEventsToAnalyze).ToList()
            };

            var result = _engine.Analyze(session);
            tracked.LastScore = result.AiProbabilityScore;

            if (result.IsLikelyAiAgent && result.AiProbabilityScore >= _options.BlockingThreshold)
            {
                tracked.IsBlocked = true;
                tracked.BlockedAt = DateTime.UtcNow;

                _logger.LogWarning(
                    "AI agent detected and blocked. Session: {SessionId}, Score: {Score:F3}, Events: {Events}, IP: {IP}, UA: {UA}",
                    sessionId, result.AiProbabilityScore, tracked.Events.Count,
                    context.Connection.RemoteIpAddress,
                    context.Request.Headers.UserAgent.ToString());

                context.Response.StatusCode = StatusCodes.Status403Forbidden;
                context.Response.ContentType = "application/json";
                await context.Response.WriteAsync(System.Text.Json.JsonSerializer.Serialize(new
                {
                    error = "Access denied",
                    reason = "Automated agent behavior detected",
                    score = result.AiProbabilityScore,
                    signals = result.Signals.Select(s => new { s.SignalName, s.Score }),
                    sessionId
                }));
                return;
            }
        }

        // Not blocked — continue the pipeline
        await _next(context);
    }

    private ActivityEvent BuildActivityEvent(HttpContext context, TrackedSession tracked, string sessionId)
    {
        var now = DateTime.UtcNow;
        var timeSinceLast = tracked.LastRequestTime.HasValue
            ? (now - tracked.LastRequestTime.Value).TotalMilliseconds
            : 1000;

        // Determine event type from HTTP method and path
        var eventType = context.Request.Method switch
        {
            "GET" => "navigation",
            "POST" => "api_call",
            "PUT" => "api_call",
            "DELETE" => "api_call",
            _ => "navigation"
        };

        // Build mouse-like data from request patterns (simulated from timing)
        // In a real scenario, the frontend would send these via headers or a tracking endpoint
        MouseData? mouseData = null;
        if (context.Request.Headers.TryGetValue("X-Mouse-X", out var mx) &&
            context.Request.Headers.TryGetValue("X-Mouse-Y", out var my))
        {
            mouseData = new MouseData
            {
                X = int.TryParse(mx, out var x) ? x : 0,
                Y = int.TryParse(my, out var y) ? y : 0,
                Speed = context.Request.Headers.TryGetValue("X-Mouse-Speed", out var ms)
                    ? double.TryParse(ms, out var speed) ? speed : null
                    : null,
                HasCurve = context.Request.Headers.TryGetValue("X-Mouse-Curve", out var mc)
                    ? mc == "true"
                    : null
            };
        }

        // Build keyboard data if provided
        KeyboardData? keyboardData = null;
        if (context.Request.Headers.TryGetValue("X-Key-Delay", out var kd))
        {
            keyboardData = new KeyboardData
            {
                InterKeyDelayMs = double.TryParse(kd, out var delay) ? delay : null,
                BurstLength = context.Request.Headers.TryGetValue("X-Key-Burst", out var kb)
                    ? int.TryParse(kb, out var burst) ? burst : null
                    : null,
                ErrorRate = context.Request.Headers.TryGetValue("X-Key-Errors", out var ke)
                    ? double.TryParse(ke, out var errors) ? errors : null
                    : null
            };
        }

        return new ActivityEvent
        {
            SessionId = sessionId,
            UserId = sessionId,
            Timestamp = now,
            EventType = eventType,
            Endpoint = context.Request.Path.ToString(),
            DurationMs = (int)timeSinceLast,
            Mouse = mouseData,
            Keyboard = keyboardData
        };
    }

    private string GetSessionId(HttpContext context)
    {
        // Try cookie-based session first
        const string cookieName = "aisec_sid";
        if (context.Request.Cookies.TryGetValue(cookieName, out var existingId))
        {
            return existingId;
        }

        // Generate new session ID and set cookie
        var newId = $"sid-{Guid.NewGuid():N}";
        context.Response.Cookies.Append(cookieName, newId, new CookieOptions
        {
            HttpOnly = true,
            SameSite = SameSiteMode.Strict,
            MaxAge = TimeSpan.FromHours(1)
        });

        return newId;
    }

    private bool ShouldSkip(PathString path)
    {
        foreach (var excluded in _options.ExcludedPaths)
        {
            if (path.StartsWithSegments(excluded, StringComparison.OrdinalIgnoreCase))
                return true;
        }
        return false;
    }

    /// <summary>
    /// Cleanup old sessions periodically (call from a background service or timer).
    /// </summary>
    public static void CleanupExpiredSessions(TimeSpan maxAge)
    {
        var cutoff = DateTime.UtcNow - maxAge;
        var expired = _sessions.Where(kvp => kvp.Value.LastRequestTime < cutoff).ToList();
        foreach (var kvp in expired)
        {
            _sessions.TryRemove(kvp.Key, out _);
        }
    }
}

/// <summary>
/// Tracks a single session's activity for AI detection.
/// </summary>
internal class TrackedSession
{
    public string SessionId { get; }
    public List<ActivityEvent> Events { get; } = new();
    public DateTime? LastRequestTime { get; set; }
    public int RequestCount { get; set; }
    public double LastScore { get; set; }
    public bool IsBlocked { get; set; }
    public DateTime? BlockedAt { get; set; }

    public TrackedSession(string sessionId)
    {
        SessionId = sessionId;
    }
}
