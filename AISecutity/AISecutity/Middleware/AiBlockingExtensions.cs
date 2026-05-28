namespace AISecutity.Middleware;

/// <summary>
/// Extension methods for registering the AI blocking middleware.
/// </summary>
public static class AiBlockingExtensions
{
    /// <summary>
    /// Adds AI blocking middleware configuration to the service collection.
    /// </summary>
    public static IServiceCollection AddAiBlocking(this IServiceCollection services, Action<AiBlockingOptions>? configure = null)
    {
        if (configure != null)
        {
            services.Configure(configure);
        }
        else
        {
            services.Configure<AiBlockingOptions>(_ => { });
        }

        return services;
    }

    /// <summary>
    /// Adds the AI agent blocking middleware to the request pipeline.
    /// Place this before UseAuthorization and MapControllers.
    /// </summary>
    public static IApplicationBuilder UseAiBlocking(this IApplicationBuilder app)
    {
        return app.UseMiddleware<AiBlockingMiddleware>();
    }
}
