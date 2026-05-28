using System.Text.Json;
using AISecutity.Models;

namespace AISecutity.Detection;

/// <summary>
/// Client that calls the Python ML microservice for a second opinion.
/// Used when the rule engine score is in the "uncertain" zone (0.30-0.60).
/// </summary>
public class MlDetectionClient
{
    private readonly HttpClient _http;
    private readonly ILogger<MlDetectionClient> _logger;
    private const string MlServiceUrl = "http://localhost:5050/predict";

    public MlDetectionClient(HttpClient http, ILogger<MlDetectionClient> logger)
    {
        _http = http;
        _logger = logger;
        _http.Timeout = TimeSpan.FromSeconds(5);
    }

    /// <summary>
    /// Ask the ML model if this session is a bot.
    /// Returns null if the ML service is unavailable.
    /// </summary>
    public async Task<MlPrediction?> PredictAsync(ActivitySession session)
    {
        try
        {
            var json = JsonSerializer.Serialize(session, new JsonSerializerOptions
            {
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            });

            var content = new StringContent(json, System.Text.Encoding.UTF8, "application/json");
            var response = await _http.PostAsync(MlServiceUrl, content);

            if (response.IsSuccessStatusCode)
            {
                var body = await response.Content.ReadAsStringAsync();
                var result = JsonSerializer.Deserialize<MlPrediction>(body, new JsonSerializerOptions
                {
                    PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
                });
                return result;
            }

            _logger.LogWarning("[ML] Service returned {Status}", response.StatusCode);
            return null;
        }
        catch (Exception ex)
        {
            _logger.LogDebug("[ML] Service unavailable: {Error}", ex.Message);
            return null;
        }
    }
}

public class MlPrediction
{
    public string Prediction { get; set; } = "human";
    public double BotProbability { get; set; }
    public double Confidence { get; set; }
    public string ModelVersion { get; set; } = "";
    public int FeaturesUsed { get; set; }
}
