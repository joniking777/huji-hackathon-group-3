using AISecutity;
using AISecutity.Detection;
using AISecutity.Middleware;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddControllers();
builder.Services.AddOpenApi();

// Register AI detection services
builder.Services.AddSingleton<IAiDetectionEngine, AiDetectionEngine>();
builder.Services.AddSingleton<ActivityManager>();

// Register AI blocking middleware with options
builder.Services.AddAiBlocking(options =>
{
    options.MinEventsBeforeAnalysis = 5;
    options.BlockingThreshold = 0.75;
    options.ExcludedPaths = new List<string>
    {
        "/api/detection",
        "/health",
        "/swagger",
        "/openapi"
    };
});

// CORS for Angular demo site
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowDemoSite", policy =>
    {
        policy.WithOrigins("http://localhost:4200")
              .AllowAnyHeader()
              .AllowAnyMethod();
    });
});

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseCors("AllowDemoSite");

// AI agent blocking — place before auth and controllers
app.UseAiBlocking();

app.UseHttpsRedirection();
app.UseAuthorization();
app.MapControllers();

app.Run();
