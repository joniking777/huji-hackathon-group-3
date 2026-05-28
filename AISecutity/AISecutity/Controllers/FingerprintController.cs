using AISecutity.Detection;
using AISecutity.Middleware;
using Microsoft.AspNetCore.Mvc;

namespace AISecutity.Controllers;

[ApiController]
[Route("api/[controller]")]
public class FingerprintController : ControllerBase
{
    /// <summary>
    /// Analyze the current request's fingerprint.
    /// Shows what the server sees at the network level.
    /// GET api/fingerprint/me
    /// </summary>
    [HttpGet("me")]
    public ActionResult GetMyFingerprint()
    {
        var fingerprint = HttpContext.Items["RequestFingerprint"] as RequestFingerprint;
        var history = HttpContext.Items["RequestHistory"] as RequestHistory;

        if (fingerprint == null)
            return Ok(new { error = "Fingerprint not available" });

        return Ok(new
        {
            yourFingerprint = new
            {
                fingerprint.Score,
                fingerprint.IsLikelyAutomated,
                fingerprint.UserAgent,
                fingerprint.AcceptLanguage,
                fingerprint.HeaderCount,
                fingerprint.Signals,
            },
            requestHistory = new
            {
                requestsInLast5Min = history?.GetRequestCount() ?? 0,
                averageScore = history?.GetAverageScore() ?? 0,
            },
            verdict = fingerprint.Score switch
            {
                >= 0.85 => "BLOCKED — Obvious automation tool",
                >= 0.6 => "SUSPICIOUS — Likely automated, will be challenged",
                >= 0.4 => "UNCERTAIN — Monitoring closely",
                _ => "CLEAN — Looks like a real browser"
            },
        });
    }

    /// <summary>
    /// Test endpoint: send a request with custom headers to see how it scores.
    /// POST api/fingerprint/test
    /// </summary>
    [HttpPost("test")]
    public ActionResult TestFingerprint()
    {
        var fingerprint = HttpContext.Items["RequestFingerprint"] as RequestFingerprint;

        return Ok(new
        {
            fingerprint?.Score,
            fingerprint?.IsLikelyAutomated,
            fingerprint?.Signals,
            headers = Request.Headers.ToDictionary(h => h.Key, h => h.Value.ToString()),
        });
    }
}
