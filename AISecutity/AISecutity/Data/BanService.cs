using AISecutity.Data.Entities;
using AISecutity.Models;
using Microsoft.EntityFrameworkCore;

namespace AISecutity.Data;

/// <summary>
/// Service for managing bans, recording incidents, and checking if actors are blocked.
/// Implements both in-memory rate limiting and persistent bans.
/// </summary>
public class BanService
{
    private readonly SecurityDbContext _db;
    private readonly ILogger<BanService> _logger;

    public BanService(SecurityDbContext db, ILogger<BanService> logger)
    {
        _db = db;
        _logger = logger;
    }

    /// <summary>
    /// Check if an IP or session is currently banned.
    /// </summary>
    public async Task<BannedActor?> GetActiveBan(string ipAddress, string? sessionId = null)
    {
        var now = DateTime.UtcNow;

        var ban = await _db.BannedActors
            .Where(b => b.LiftedAt == null)
            .Where(b => b.ExpiresAt == null || b.ExpiresAt > now)
            .Where(b => b.IpAddress == ipAddress || (sessionId != null && b.SessionId == sessionId))
            .OrderByDescending(b => b.RiskScore)
            .FirstOrDefaultAsync();

        return ban;
    }

    /// <summary>
    /// Ban an actor based on detection results.
    /// Uses progressive penalties: first offense = 15min, repeat = 1hr, persistent = permanent.
    /// </summary>
    public async Task<BannedActor> BanActor(DetectionResult detection, string ipAddress, string? userAgent = null)
    {
        // Check how many previous incidents this IP has
        int previousIncidents = await _db.SecurityIncidents
            .CountAsync(i => i.IpAddress == ipAddress);

        // Progressive ban duration
        var (banType, penalty, duration, tarpitDelay) = previousIncidents switch
        {
            0 => ("temporary", "block", TimeSpan.FromMinutes(15), (int?)null),
            1 => ("temporary", "block", TimeSpan.FromHours(1), (int?)null),
            2 => ("temporary", "tarpit", TimeSpan.FromHours(6), 5000),
            3 => ("temporary", "tarpit", TimeSpan.FromHours(24), 10000),
            _ => ("permanent", "block", TimeSpan.Zero, (int?)null),
        };

        var ban = new BannedActor
        {
            IpAddress = ipAddress,
            SessionId = detection.SessionId,
            UserId = detection.UserId,
            UserAgent = userAgent,
            BanType = banType,
            Reason = $"AI bot detected with score {detection.AiProbabilityScore:F3}",
            RiskScore = detection.AiProbabilityScore,
            TriggeredRule = string.Join(", ", detection.Signals
                .Where(s => s.Score >= 0.6)
                .Select(s => $"{s.SignalName}={s.Score:F2}")),
            BannedAt = DateTime.UtcNow,
            ExpiresAt = banType == "permanent" ? null : DateTime.UtcNow.Add(duration),
            Penalty = penalty,
            TarpitDelayMs = tarpitDelay,
            TotalIncidents = previousIncidents + 1,
        };

        _db.BannedActors.Add(ban);
        await _db.SaveChangesAsync();

        _logger.LogWarning("[BAN] {IP} banned ({BanType}, {Penalty}) for {Duration}. Score: {Score:F3}. Signals: {Signals}",
            ipAddress, banType, penalty,
            banType == "permanent" ? "forever" : duration.ToString(),
            detection.AiProbabilityScore, ban.TriggeredRule);

        return ban;
    }

    /// <summary>
    /// Record a security incident with full telemetry data.
    /// </summary>
    public async Task RecordIncident(DetectionResult detection, string ipAddress, string? userAgent = null, string? targetUrl = null)
    {
        var incident = new SecurityIncident
        {
            IpAddress = ipAddress,
            SessionId = detection.SessionId,
            UserId = detection.UserId,
            UserAgent = userAgent,
            TargetUrl = targetUrl,
            RiskScore = detection.AiProbabilityScore,
            TriggeredSignals = System.Text.Json.JsonSerializer.Serialize(
                detection.Signals.Select(s => new { s.SignalName, s.Score })),
            TotalEventsInSession = detection.TotalEventsAnalyzed,
            ReputationFlag = detection.AiProbabilityScore >= 0.75 ? "known_bot" : "suspicious",
            AppliedPenalty = detection.AiProbabilityScore >= 0.50 ? "block" : "monitor",
            IncidentType = "bot_detected",
        };

        _db.SecurityIncidents.Add(incident);
        await _db.SaveChangesAsync();
    }

    /// <summary>
    /// Lift a ban manually (admin action).
    /// </summary>
    public async Task<bool> LiftBan(int banId)
    {
        var ban = await _db.BannedActors.FindAsync(banId);
        if (ban == null) return false;

        ban.LiftedAt = DateTime.UtcNow;
        await _db.SaveChangesAsync();
        return true;
    }

    /// <summary>
    /// Get all currently active bans.
    /// </summary>
    public async Task<List<BannedActor>> GetActiveBans()
    {
        var now = DateTime.UtcNow;
        return await _db.BannedActors
            .Where(b => b.LiftedAt == null)
            .Where(b => b.ExpiresAt == null || b.ExpiresAt > now)
            .OrderByDescending(b => b.BannedAt)
            .ToListAsync();
    }

    /// <summary>
    /// Get incident history for an IP.
    /// </summary>
    public async Task<List<SecurityIncident>> GetIncidentsByIp(string ipAddress)
    {
        return await _db.SecurityIncidents
            .Where(i => i.IpAddress == ipAddress)
            .OrderByDescending(i => i.DetectedAt)
            .ToListAsync();
    }
}
