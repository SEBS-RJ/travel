// ============================================================
// backend/DTOs/RecommendationDTOs.cs
// Objetos de transferencia para el módulo de recomendaciones
// ============================================================

using System.ComponentModel.DataAnnotations;
using TurismoTarija.Models;

namespace TurismoTarija.DTOs;

// ── Request ──────────────────────────────────────────────────

public class RecommendationRequestDTO
{
    /// <summary>Latitud del usuario. Requerida para recomendaciones cercanas.</summary>
    [Range(-90, 90)]
    public double? Latitude { get; set; }

    [Range(-180, 180)]
    public double? Longitude { get; set; }

    /// <summary>Presupuesto máximo en bolivianos.</summary>
    [Range(0, 10000)]
    public decimal? BudgetBob { get; set; }

    /// <summary>Tiempo disponible en minutos.</summary>
    [Range(0, 1440)]
    public int? AvailableMinutes { get; set; }

    /// <summary>Categorías preferidas.</summary>
    public List<PlaceCategory>? PreferredCategories { get; set; }

    /// <summary>Tipo de grupo viajero.</summary>
    [RegularExpression("^(solo|pareja|familia|grupo)$")]
    public string TravelParty { get; set; } = "solo";

    public bool AccessibilityNeeded { get; set; } = false;
    public bool OnlyFree { get; set; } = false;

    /// <summary>Radio de búsqueda en km (default 5 km).</summary>
    [Range(0.5, 50)]
    public double RadiusKm { get; set; } = 5.0;

    /// <summary>Número máximo de resultados (default 5).</summary>
    [Range(1, 10)]
    public int Limit { get; set; } = 5;
}

// ── Response ─────────────────────────────────────────────────

public class PlaceSummaryDTO
{
    public Guid Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
    public string Category { get; set; } = string.Empty;
    public string? Address { get; set; }
    public double Latitude { get; set; }
    public double Longitude { get; set; }
    public double DistanceKm { get; set; }
    public string PriceRange { get; set; } = string.Empty;
    public decimal? AvgPriceBob { get; set; }
    public decimal Rating { get; set; }
    public List<string> Images { get; set; } = new();
    public List<string> Tags { get; set; } = new();
    public bool IsAccessible { get; set; }
    public string? OpeningHours { get; set; }
}

public class RecommendationItemDTO
{
    public PlaceSummaryDTO Place { get; set; } = null!;
    public float Score { get; set; }
    public string Reason { get; set; } = string.Empty;
    public List<string> FiltersMatched { get; set; } = new();
}

public class RecommendationResponseDTO
{
    public List<RecommendationItemDTO> Recommendations { get; set; } = new();
    public Dictionary<string, object> FiltersApplied { get; set; } = new();
    public int TotalFound { get; set; }
    public string GeneratedAt { get; set; } = DateTime.UtcNow.ToString("o");
}