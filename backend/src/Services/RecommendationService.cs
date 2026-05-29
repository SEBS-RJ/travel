// ============================================================
// backend/Services/RecommendationService.cs
// Lógica de negocio — Motor de recomendaciones
// Aplica scoring, ranking y generación de explicaciones
// ============================================================

using TurismoTarija.DTOs;
using TurismoTarija.Models;
using TurismoTarija.Repositories;

namespace TurismoTarija.Services;

public interface IRecommendationService
{
    Task<RecommendationResponseDTO> GetRecommendationsAsync(
        RecommendationRequestDTO request,
        Guid? userId = null);
}

public class RecommendationService : IRecommendationService
{
    private readonly ITouristPlaceRepository _placeRepo;
    private readonly ILogger<RecommendationService> _logger;

    // Pesos del scoring (deben sumar 1.0)
    private const float WeightRating = 0.35f;
    private const float WeightDistance = 0.30f;
    private const float WeightPrice = 0.20f;
    private const float WeightContext = 0.15f;

    // Tarija centro (referencia cuando no hay ubicación)
    private const double DefaultLat = -21.5355;
    private const double DefaultLng = -64.7296;

    public RecommendationService(
        ITouristPlaceRepository placeRepo,
        ILogger<RecommendationService> logger)
    {
        _placeRepo = placeRepo;
        _logger = logger;
    }

    public async Task<RecommendationResponseDTO> GetRecommendationsAsync(
        RecommendationRequestDTO request, Guid? userId = null)
    {
        double lat = request.Latitude ?? DefaultLat;
        double lng = request.Longitude ?? DefaultLng;

        // Ajustar radio según tiempo disponible
        double effectiveRadius = request.AvailableMinutes switch
        {
            < 120 => Math.Min(request.RadiusKm, 2.0),    // < 2h → solo 2 km
            < 240 => Math.Min(request.RadiusKm, 4.0),    // < 4h → solo 4 km
            _ => request.RadiusKm
        };

        // Ajustar filtro de presupuesto
        if (request.TravelParty == "familia" && !request.PreferredCategories?.Any() == true)
        {
            request.PreferredCategories = new List<PlaceCategory>
            {
                PlaceCategory.Park, PlaceCategory.Museum,
                PlaceCategory.TouristSpot, PlaceCategory.Market
            };
        }

        // Recuperar candidatos del repositorio
        var candidates = (await _placeRepo.GetNearbyAsync(
            lat, lng, effectiveRadius, request, request.Limit * 2  // Pedir el doble para re-rankear
        )).ToList();

        if (!candidates.Any())
        {
            _logger.LogWarning("Sin resultados para: lat={Lat}, lng={Lng}, radius={R}km", lat, lng, effectiveRadius);
            return new RecommendationResponseDTO
            {
                Recommendations = new(),
                TotalFound = 0,
                FiltersApplied = BuildFiltersApplied(request, effectiveRadius),
            };
        }

        // Aplicar scoring y ranking
        var scored = candidates
            .Select(p => new RecommendationItemDTO
            {
                Place = p,
                Score = CalculateScore(p, request),
                Reason = GenerateReason(p, request),
                FiltersMatched = GetFiltersMatched(p, request),
            })
            .OrderByDescending(r => r.Score)
            .Take(request.Limit)
            .ToList();

        return new RecommendationResponseDTO
        {
            Recommendations = scored,
            TotalFound = candidates.Count,
            FiltersApplied = BuildFiltersApplied(request, effectiveRadius),
        };
    }

    // ── Scoring ───────────────────────────────────────────────

    private float CalculateScore(PlaceSummaryDTO place, RecommendationRequestDTO req)
    {
        // Rating normalizado (0–5 → 0–1)
        float ratingScore = (float)(place.Rating / 5.0m);

        // Distancia normalizada inversa (más cerca = mayor score)
        float distanceScore = place.DistanceKm <= 0
            ? 1.0f
            : Math.Max(0f, 1f - (float)(place.DistanceKm / req.RadiusKm));

        // Precio: adecuación al presupuesto
        float priceScore = GetPriceScore(place, req);

        // Contexto: bonus por coincidencia con perfil del usuario
        float contextScore = GetContextScore(place, req);

        return WeightRating * ratingScore
             + WeightDistance * distanceScore
             + WeightPrice * priceScore
             + WeightContext * contextScore;
    }

    private float GetPriceScore(PlaceSummaryDTO place, RecommendationRequestDTO req)
    {
        if (place.PriceRange == "free") return 1.0f;
        if (req.BudgetBob == null) return 0.7f;

        if (place.AvgPriceBob == null) return 0.5f;
        if (place.AvgPriceBob <= req.BudgetBob * 0.5m) return 1.0f;
        if (place.AvgPriceBob <= req.BudgetBob) return 0.7f;
        return 0.1f; // Supera el presupuesto
    }

    private float GetContextScore(PlaceSummaryDTO place, RecommendationRequestDTO req)
    {
        float score = 0f;

        // Bonus por accesibilidad cuando se requiere
        if (req.AccessibilityNeeded && place.IsAccessible) score += 0.5f;

        // Bonus por categoría preferida
        if (req.PreferredCategories?.Any(c =>
            c.ToString().Equals(place.Category, StringComparison.OrdinalIgnoreCase)) == true)
            score += 0.5f;

        return Math.Min(score, 1.0f);
    }

    // ── Explicabilidad ────────────────────────────────────────

    private string GenerateReason(PlaceSummaryDTO place, RecommendationRequestDTO req)
    {
        var reasons = new List<string>();

        if (place.DistanceKm < 1.0)
            reasons.Add($"está a solo {place.DistanceKm:F1} km de tu ubicación");

        if (place.Rating >= 4.5m)
            reasons.Add($"tiene una valoración excelente de {place.Rating:F1}/5");
        else if (place.Rating >= 4.0m)
            reasons.Add($"está muy bien valorado ({place.Rating:F1}/5)");

        if (place.PriceRange == "free")
            reasons.Add("es de entrada gratuita");
        else if (req.BudgetBob.HasValue && place.AvgPriceBob <= req.BudgetBob)
            reasons.Add("se ajusta a tu presupuesto");

        if (place.IsAccessible && req.AccessibilityNeeded)
            reasons.Add("cuenta con acceso para personas con movilidad reducida");

        if (!reasons.Any())
            reasons.Add("es uno de los lugares destacados de Tarija");

        return string.Join(" y ", reasons).UpperFirst() + ".";
    }

    private List<string> GetFiltersMatched(PlaceSummaryDTO place, RecommendationRequestDTO req)
    {
        var matched = new List<string>();

        if (place.PriceRange == "free" || req.OnlyFree) matched.Add("gratuito");
        if (place.IsAccessible && req.AccessibilityNeeded) matched.Add("accesible");
        if (req.PreferredCategories?.Any(c =>
            c.ToString().Equals(place.Category, StringComparison.OrdinalIgnoreCase)) == true)
            matched.Add("categoría preferida");

        return matched;
    }

    private Dictionary<string, object> BuildFiltersApplied(
        RecommendationRequestDTO req, double effectiveRadius) => new()
        {
            ["radius_km"] = effectiveRadius,
            ["budget_bob"] = req.BudgetBob?.ToString() ?? "sin límite",
            ["available_minutes"] = req.AvailableMinutes?.ToString() ?? "sin límite",
            ["only_free"] = req.OnlyFree,
            ["accessibility_needed"] = req.AccessibilityNeeded,
            ["travel_party"] = req.TravelParty,
        };
}

// Extensión para capitalizar la primera letra
internal static class StringExtensions
{
    public static string UpperFirst(this string s) =>
        string.IsNullOrEmpty(s) ? s : char.ToUpper(s[0]) + s[1..];
}