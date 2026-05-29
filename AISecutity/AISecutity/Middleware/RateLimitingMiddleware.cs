using System.Collections.Concurrent;

namespace AISecutity.Middleware;

/// <summary>
/// In-memory rate limiting middleware.
/// Tracks request velocity per IP using a sliding window.
/// If an IP exceeds the threshold, applies a temporary block.
/// </summary>
public class RateLimitingMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<RateLimitingMiddleware> _logger;
    private static readonly ConcurrentDictionary<string, SlidingWindow> _windows = new();

    private const int MaxRequestsPerMinute = 60;
    private const int BlockDurationSeconds = 300; // 5 minutes
    private static readonly ConcurrentDictionary<string, DateTime> _blocked = new();

    public RateLimitingMiddleware(RequestDelegate next, ILogger<RateLimitingMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        var ip = context.Connection.RemoteIpAddress?.ToString() ?? "unknown";
        var path = context.Request.Path.Value ?? "";

        // Skip rate limiting for SDK/dashboard endpoints (they handle their own throttling)
        if (path.StartsWith("/api/sdk/") || path.StartsWith("/sdk/"))
        {
            await _next(context);
            return;
        }

        // Skip rate limiting for localhost/loopback (development)
        if (ip == "127.0.0.1" || ip == "::1" || ip == "localhost")
        {
            await _next(context);
            return;
        }

        // Check if IP is currently rate-limited
        if (_blocked.TryGetValue(ip, out var blockedUntil))
        {
            if (DateTime.UtcNow < blockedUntil)
            {
                _logger.LogWarning("[RATE-LIMIT] Blocked request from {IP} (blocked until {Until})", ip, blockedUntil);
                context.Response.StatusCode = 429;
                context.Response.Headers["Retry-After"] = ((int)(blockedUntil - DateTime.UtcNow).TotalSeconds).ToString();
                await context.Response.WriteAsJsonAsync(new
                {
                    error = "Too Many Requests",
                    message = $"Rate limited. Try again in {(int)(blockedUntil - DateTime.UtcNow).TotalSeconds} seconds.",
                    ip,
                });
                return;
            }
            _blocked.TryRemove(ip, out _);
        }

        // Track request in sliding window
        var window = _windows.GetOrAdd(ip, _ => new SlidingWindow());
        window.AddRequest();

        int requestCount = window.GetCount();

        if (requestCount > MaxRequestsPerMinute)
        {
            // Block this IP
            var until = DateTime.UtcNow.AddSeconds(BlockDurationSeconds);
            _blocked[ip] = until;
            _logger.LogWarning("[RATE-LIMIT] IP {IP} exceeded {Max} req/min ({Actual}). Blocked for {Duration}s.",
                ip, MaxRequestsPerMinute, requestCount, BlockDurationSeconds);

            context.Response.StatusCode = 429;
            context.Response.Headers["Retry-After"] = BlockDurationSeconds.ToString();
            await context.Response.WriteAsJsonAsync(new
            {
                error = "Too Many Requests",
                message = $"You sent {requestCount} requests in the last minute. Blocked for {BlockDurationSeconds} seconds.",
                ip,
            });
            return;
        }

        // Add rate limit headers
        context.Response.Headers["X-RateLimit-Limit"] = MaxRequestsPerMinute.ToString();
        context.Response.Headers["X-RateLimit-Remaining"] = Math.Max(0, MaxRequestsPerMinute - requestCount).ToString();

        await _next(context);
    }
}

/// <summary>
/// Sliding window counter — tracks requests in the last 60 seconds.
/// </summary>
public class SlidingWindow
{
    private readonly ConcurrentQueue<DateTime> _timestamps = new();
    private readonly TimeSpan _windowSize = TimeSpan.FromSeconds(60);

    public void AddRequest()
    {
        _timestamps.Enqueue(DateTime.UtcNow);
        Cleanup();
    }

    public int GetCount()
    {
        Cleanup();
        return _timestamps.Count;
    }

    private void Cleanup()
    {
        var cutoff = DateTime.UtcNow - _windowSize;
        while (_timestamps.TryPeek(out var oldest) && oldest < cutoff)
        {
            _timestamps.TryDequeue(out _);
        }
    }
}

public static class RateLimitingExtensions
{
    public static IApplicationBuilder UseRateLimiting(this IApplicationBuilder app)
    {
        return app.UseMiddleware<RateLimitingMiddleware>();
    }
}
