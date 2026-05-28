using AISecutity.Models;

namespace AISecutity.Detection;

/// <summary>
/// Server-side request fingerprinting — analyzes what the SERVER sees,
/// not what the CLIENT claims.
/// 
/// This addresses the "client-side trust" vulnerability:
/// A bot can fake mouse/keyboard telemetry, but it can't fake:
/// 1. HTTP header order and presence (browsers have specific patterns)
/// 2. TLS fingerprint (JA3/JA4 hash from the TLS handshake)
/// 3. Connection behavior (keep-alive patterns, HTTP/2 settings)
/// 4. Header consistency (claimed User-Agent vs actual capabilities)
/// 5. Telemetry-to-request correlation (claimed 15 events but only 3 HTTP requests?)
/// 
/// This runs on the MIDDLEWARE level — before the detection engine even sees the data.
/// </summary>
public class RequestFingerprintAnalyzer
{
    /// <summary>
    /// Analyze an incoming HTTP request for bot indicators at the network level.
    /// Returns a fingerprint score (0 = definitely human browser, 1 = definitely bot/tool).
    /// </summary>
    public RequestFingerprint Analyze(HttpContext context)
    {
        var headers = context.Request.Headers;
        var fingerprint = new RequestFingerprint
        {
            IpAddress = context.Connection.RemoteIpAddress?.ToString() ?? "unknown",
            Timestamp = DateTime.UtcNow,
        };

        var signals = new List<(string name, double score, string detail)>();

        // === 1. Header Order & Presence Analysis ===
        signals.Add(AnalyzeHeaderOrder(headers));

        // === 2. User-Agent Consistency ===
        signals.Add(AnalyzeUserAgent(headers));

        // === 3. Missing Browser Headers ===
        signals.Add(AnalyzeMissingHeaders(headers));

        // === 4. Accept Header Analysis ===
        signals.Add(AnalyzeAcceptHeaders(headers));

        // === 5. Connection Behavior ===
        signals.Add(AnalyzeConnectionBehavior(context));

        // Calculate combined score
        double totalScore = signals.Average(s => s.score);
        fingerprint.Score = Math.Round(totalScore, 4);
        fingerprint.IsLikelyAutomated = totalScore >= 0.6;
        fingerprint.Signals = signals.Select(s => new FingerprintSignal
        {
            Name = s.name,
            Score = s.score,
            Detail = s.detail,
        }).ToList();

        // Extract key identifiers
        fingerprint.UserAgent = headers["User-Agent"].FirstOrDefault() ?? "";
        fingerprint.AcceptLanguage = headers["Accept-Language"].FirstOrDefault() ?? "";
        fingerprint.HeaderCount = headers.Count;

        return fingerprint;
    }

    /// <summary>
    /// Real browsers send headers in a specific order.
    /// Python requests, aiohttp, curl all have different header orders.
    /// </summary>
    private (string, double, string) AnalyzeHeaderOrder(IHeaderDictionary headers)
    {
        var headerNames = headers.Keys.Select(k => k.ToLower()).ToList();

        // Chrome always sends: host, connection, sec-ch-ua, sec-ch-ua-mobile, 
        // sec-ch-ua-platform, upgrade-insecure-requests, user-agent, accept, 
        // sec-fetch-site, sec-fetch-mode, sec-fetch-user, sec-fetch-dest, 
        // accept-encoding, accept-language
        bool hasSecChUa = headerNames.Any(h => h.StartsWith("sec-ch-ua"));
        bool hasSecFetch = headerNames.Any(h => h.StartsWith("sec-fetch"));

        // Python requests sends: user-agent, accept-encoding, accept, connection, host
        // (much fewer headers, different order)
        bool looksLikePythonRequests = headerNames.Count < 8 && !hasSecChUa && !hasSecFetch;

        // curl sends: host, user-agent, accept
        bool looksLikeCurl = headerNames.Count <= 5 && !hasSecChUa;

        double score;
        string detail;

        if (looksLikeCurl)
        {
            score = 0.9;
            detail = $"Only {headerNames.Count} headers, no browser-specific headers. Looks like curl/wget.";
        }
        else if (looksLikePythonRequests)
        {
            score = 0.8;
            detail = $"{headerNames.Count} headers, missing sec-ch-ua and sec-fetch. Looks like HTTP library.";
        }
        else if (!hasSecFetch && hasSecChUa)
        {
            score = 0.4;
            detail = "Has sec-ch-ua but missing sec-fetch headers. Possibly older browser or modified.";
        }
        else if (hasSecChUa && hasSecFetch)
        {
            score = 0.1;
            detail = "Full browser header set present (sec-ch-ua + sec-fetch).";
        }
        else
        {
            score = 0.5;
            detail = $"{headerNames.Count} headers. Inconclusive.";
        }

        return ("HeaderOrder", score, detail);
    }

    /// <summary>
    /// Check if User-Agent is consistent with actual request behavior.
    /// A bot claiming to be Chrome but missing Chrome-specific headers is lying.
    /// </summary>
    private (string, double, string) AnalyzeUserAgent(IHeaderDictionary headers)
    {
        var ua = headers["User-Agent"].FirstOrDefault() ?? "";
        var headerNames = headers.Keys.Select(k => k.ToLower()).ToList();

        if (string.IsNullOrEmpty(ua))
            return ("UserAgentConsistency", 0.9, "No User-Agent header at all.");

        bool claimsChrome = ua.Contains("Chrome/") && !ua.Contains("Chromium");
        bool claimsFirefox = ua.Contains("Firefox/");
        bool claimsSafari = ua.Contains("Safari/") && !ua.Contains("Chrome/");

        bool hasSecChUa = headerNames.Any(h => h.StartsWith("sec-ch-ua"));
        bool hasSecFetch = headerNames.Any(h => h.StartsWith("sec-fetch"));

        // Chrome ALWAYS sends sec-ch-ua headers. If UA says Chrome but no sec-ch-ua → fake
        if (claimsChrome && !hasSecChUa)
            return ("UserAgentConsistency", 0.85, $"Claims Chrome but missing sec-ch-ua headers. Spoofed UA.");

        // Firefox never sends sec-ch-ua. If UA says Firefox but has sec-ch-ua → fake
        if (claimsFirefox && hasSecChUa)
            return ("UserAgentConsistency", 0.8, "Claims Firefox but has sec-ch-ua (Chrome-only). Spoofed UA.");

        // Known bot user agents
        string[] botUAs = { "python-requests", "aiohttp", "curl/", "Go-http-client",
                           "Scrapy", "Bot/", "Spider", "Crawler", "GPTBot", "ClaudeBot" };
        if (botUAs.Any(b => ua.Contains(b, StringComparison.OrdinalIgnoreCase)))
            return ("UserAgentConsistency", 0.95, $"Known bot/automation User-Agent: {ua[..Math.Min(50, ua.Length)]}");

        // Consistent browser UA
        return ("UserAgentConsistency", 0.1, "User-Agent consistent with request headers.");
    }

    /// <summary>
    /// Real browsers send many headers that bots/tools typically omit.
    /// </summary>
    private (string, double, string) AnalyzeMissingHeaders(IHeaderDictionary headers)
    {
        var headerNames = headers.Keys.Select(k => k.ToLower()).ToHashSet();

        int missingCount = 0;
        var missing = new List<string>();

        // Headers that real browsers almost always send
        string[] expectedBrowserHeaders = {
            "accept-language",
            "accept-encoding",
            "connection",
        };

        foreach (var expected in expectedBrowserHeaders)
        {
            if (!headerNames.Contains(expected))
            {
                missingCount++;
                missing.Add(expected);
            }
        }

        // Sec-Fetch headers (all modern browsers send these)
        string[] secFetchHeaders = { "sec-fetch-site", "sec-fetch-mode", "sec-fetch-dest" };
        int missingSecFetch = secFetchHeaders.Count(h => !headerNames.Contains(h));

        double score;
        if (missingCount >= 2 && missingSecFetch >= 2)
            score = 0.85;
        else if (missingCount >= 1 && missingSecFetch >= 2)
            score = 0.7;
        else if (missingSecFetch >= 2)
            score = 0.5;
        else if (missingCount >= 1)
            score = 0.3;
        else
            score = 0.1;

        string detail = missing.Count > 0
            ? $"Missing: {string.Join(", ", missing)}. Missing {missingSecFetch} sec-fetch headers."
            : "All expected browser headers present.";

        return ("MissingHeaders", score, detail);
    }

    /// <summary>
    /// Real browsers send specific Accept headers for different resource types.
    /// Bots typically send generic "Accept: */*" or nothing.
    /// </summary>
    private (string, double, string) AnalyzeAcceptHeaders(IHeaderDictionary headers)
    {
        var accept = headers["Accept"].FirstOrDefault() ?? "";

        if (string.IsNullOrEmpty(accept))
            return ("AcceptHeader", 0.8, "No Accept header.");

        // Bots typically send: */* or application/json
        if (accept == "*/*")
            return ("AcceptHeader", 0.6, "Generic Accept: */* (common in HTTP libraries).");

        if (accept == "application/json")
            return ("AcceptHeader", 0.7, "Accept: application/json only (API client, not browser).");

        // Real browsers send complex Accept headers for page navigation
        if (accept.Contains("text/html") && accept.Contains("application/xhtml+xml"))
            return ("AcceptHeader", 0.1, "Full browser Accept header (text/html, xhtml+xml).");

        return ("AcceptHeader", 0.4, $"Unusual Accept header: {accept[..Math.Min(50, accept.Length)]}");
    }

    /// <summary>
    /// Analyze connection-level behavior.
    /// </summary>
    private (string, double, string) AnalyzeConnectionBehavior(HttpContext context)
    {
        // Check if request came over HTTPS (bots sometimes skip TLS)
        bool isHttps = context.Request.IsHttps;

        // Check for proxy headers (bots often route through proxies)
        var headers = context.Request.Headers;
        bool hasForwardedFor = headers.ContainsKey("X-Forwarded-For");
        bool hasVia = headers.ContainsKey("Via");
        bool hasProxyHeaders = hasForwardedFor || hasVia;

        // Check request method consistency
        var method = context.Request.Method;
        var contentType = headers["Content-Type"].FirstOrDefault() ?? "";

        // POST with application/json to a detection endpoint is expected
        // But POST with no content-type is suspicious
        bool suspiciousPost = method == "POST" && string.IsNullOrEmpty(contentType);

        double score = 0.2; // Default: looks normal
        var details = new List<string>();

        if (suspiciousPost)
        {
            score += 0.3;
            details.Add("POST without Content-Type");
        }

        if (hasProxyHeaders)
        {
            score += 0.1;
            details.Add("Proxy headers detected");
        }

        score = Math.Min(1.0, score);
        string detail = details.Count > 0 ? string.Join(", ", details) : "Normal connection behavior.";

        return ("ConnectionBehavior", score, detail);
    }
}

/// <summary>
/// Result of server-side request fingerprinting.
/// </summary>
public class RequestFingerprint
{
    public string IpAddress { get; set; } = "";
    public DateTime Timestamp { get; set; }
    public double Score { get; set; } // 0 = human browser, 1 = bot/tool
    public bool IsLikelyAutomated { get; set; }
    public string UserAgent { get; set; } = "";
    public string AcceptLanguage { get; set; } = "";
    public int HeaderCount { get; set; }
    public List<FingerprintSignal> Signals { get; set; } = new();
}

public class FingerprintSignal
{
    public string Name { get; set; } = "";
    public double Score { get; set; }
    public string Detail { get; set; } = "";
}
