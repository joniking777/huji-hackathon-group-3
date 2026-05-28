using AISecutity.Data;
using AISecutity.Data.Entities;
using AISecutity.Detection;
using AISecutity.Models;
using Microsoft.AspNetCore.Mvc;

namespace AISecutity.Controllers;

[ApiController]
[Route("api/[controller]")]
public class BanController : ControllerBase
{
    private readonly BanService _banService;
    private readonly IAiDetectionEngine _engine;

    public BanController(BanService banService, IAiDetectionEngine engine)
    {
        _banService = banService;
        _engine = engine;
    }

    /// <summary>
    /// Analyze a session and ban the actor if detected as bot.
    /// POST api/ban/analyze-and-ban
    /// </summary>
    [HttpPost("analyze-and-ban")]
    public async Task<ActionResult> AnalyzeAndBan([FromBody] ActivitySession session, [FromQuery] string ipAddress = "unknown")
    {
        var result = _engine.Analyze(session);

        // Record the incident regardless
        await _banService.RecordIncident(result, ipAddress, session.UserAgent);

        if (result.IsLikelyAiAgent)
        {
            var ban = await _banService.BanActor(result, ipAddress, session.UserAgent);
            return Ok(new
            {
                detected = true,
                result.AiProbabilityScore,
                ban = new
                {
                    ban.Id,
                    ban.BanType,
                    ban.Penalty,
                    ban.ExpiresAt,
                    ban.Reason,
                    ban.TriggeredRule,
                },
                result.Signals,
            });
        }

        return Ok(new
        {
            detected = false,
            result.AiProbabilityScore,
            message = "Session appears human. No ban applied.",
            result.Signals,
        });
    }

    /// <summary>
    /// Check if an IP is currently banned.
    /// GET api/ban/check?ip=10.0.0.1
    /// </summary>
    [HttpGet("check")]
    public async Task<ActionResult> CheckBan([FromQuery] string ip, [FromQuery] string? sessionId = null)
    {
        var ban = await _banService.GetActiveBan(ip, sessionId);
        if (ban == null)
            return Ok(new { banned = false, ip });

        return Ok(new
        {
            banned = true,
            ip,
            ban.BanType,
            ban.Penalty,
            ban.TarpitDelayMs,
            ban.Reason,
            ban.ExpiresAt,
            ban.TotalIncidents,
        });
    }

    /// <summary>
    /// Get all currently active bans.
    /// GET api/ban/active
    /// </summary>
    [HttpGet("active")]
    public async Task<ActionResult<List<BannedActor>>> GetActiveBans()
    {
        var bans = await _banService.GetActiveBans();
        return Ok(bans);
    }

    /// <summary>
    /// Get incident history for an IP.
    /// GET api/ban/incidents?ip=10.0.0.1
    /// </summary>
    [HttpGet("incidents")]
    public async Task<ActionResult<List<SecurityIncident>>> GetIncidents([FromQuery] string ip)
    {
        var incidents = await _banService.GetIncidentsByIp(ip);
        return Ok(incidents);
    }

    /// <summary>
    /// Manually lift a ban.
    /// DELETE api/ban/{id}
    /// </summary>
    [HttpDelete("{id}")]
    public async Task<ActionResult> LiftBan(int id)
    {
        var success = await _banService.LiftBan(id);
        if (!success) return NotFound();
        return Ok(new { message = "Ban lifted.", id });
    }
}
