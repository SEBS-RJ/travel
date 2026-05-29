// ============================================================
// backend/Models/TouristPlace.cs
// Entidad de dominio — Lugar turístico
// ============================================================

using System.ComponentModel.DataAnnotations;

namespace TurismoTarija.Models;

public class TouristPlace
{
    public Guid Id { get; set; } = Guid.NewGuid();

    [Required, MaxLength(200)]
    public string Name { get; set; } = string.Empty;

    [Required, MaxLength(200)]
    public string Slug { get; set; } = string.Empty;

    public string? Description { get; set; }

    [Required]
    public PlaceCategory Category { get; set; }

    public string? Address { get; set; }

    // PostGIS: almacenado como lat/lng en la entidad
    public double Latitude { get; set; }
    public double Longitude { get; set; }

    public string? Phone { get; set; }
    public string? Website { get; set; }

    // JSON: {"mon": "09:00-18:00", ...}
    public string? OpeningHours { get; set; }

    public string PriceRange { get; set; } = "free"; // free | low | mid | high
    public decimal? AvgPriceBob { get; set; }

    public decimal Rating { get; set; } = 0;
    public int RatingCount { get; set; } = 0;

    public List<string> Images { get; set; } = new();
    public List<string> Tags { get; set; } = new();

    public bool IsAccessible { get; set; } = false;
    public bool IsActive { get; set; } = true;

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
}

public enum PlaceCategory
{
    TouristSpot,
    Restaurant,
    Hotel,
    Museum,
    Market,
    Winery,
    Park,
    TransportHub,
    Other
}