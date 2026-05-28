using AISecutity.Detection;
using AISecutity.Models;
using Microsoft.AspNetCore.Mvc;

namespace AISecutity.Controllers;

[ApiController]
[Route("api/[controller]")]
public class DetectionController : ControllerBase
{
    private readonly IAiDetectionEngine _engine;

    public DetectionController(IAiDetectionEngine engine)
    {
        _engine = engine;
    }

    /// <summary>
    /// Analyze a single session's activity data to detect AI agent behavior.
    /// POST api/detection/analyze
    /// </summary>
    [HttpPost("analyze")]
    public ActionResult<DetectionResult> Analyze([FromBody] ActivitySession session)
    {
        if (session.Events == null || session.Events.Count == 0)
            return BadRequest("No events provided.");

        var result = _engine.Analyze(session);
        return Ok(result);
    }

    /// <summary>
    /// Analyze multiple sessions in batch (for processing the JSON files your team produces).
    /// POST api/detection/analyze-batch
    /// </summary>
    [HttpPost("analyze-batch")]
    public ActionResult<List<DetectionResult>> AnalyzeBatch([FromBody] List<ActivitySession> sessions)
    {
        if (sessions == null || sessions.Count == 0)
            return BadRequest("No sessions provided.");

        var results = sessions.Select(s => _engine.Analyze(s)).ToList();
        return Ok(results);
    }

    /// <summary>
    /// Quick health check / summary endpoint.
    /// GET api/detection/status
    /// </summary>
    [HttpGet("status")]
    public ActionResult GetStatus()
    {
        return Ok(new { status = "running", algorithm = "v1", threshold = 0.65 });
    }
}
