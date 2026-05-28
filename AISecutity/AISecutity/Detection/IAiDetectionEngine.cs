using AISecutity.Models;

namespace AISecutity.Detection;

public interface IAiDetectionEngine
{
    DetectionResult Analyze(ActivitySession session);
}
