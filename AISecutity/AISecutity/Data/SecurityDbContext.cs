using AISecutity.Data.Entities;
using Microsoft.EntityFrameworkCore;

namespace AISecutity.Data;

public class SecurityDbContext : DbContext
{
    public SecurityDbContext(DbContextOptions<SecurityDbContext> options) : base(options) { }

    public DbSet<BannedActor> BannedActors => Set<BannedActor>();
    public DbSet<SecurityIncident> SecurityIncidents => Set<SecurityIncident>();
    public DbSet<RequestLog> RequestLogs => Set<RequestLog>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<BannedActor>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.HasIndex(e => e.IpAddress);
            entity.HasIndex(e => e.SessionId);
            entity.HasIndex(e => e.ExpiresAt);
        });

        modelBuilder.Entity<SecurityIncident>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.HasIndex(e => e.IpAddress);
            entity.HasIndex(e => e.DetectedAt);
        });

        modelBuilder.Entity<RequestLog>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.HasIndex(e => e.IpAddress);
            entity.HasIndex(e => e.Timestamp);
        });
    }
}
