// ============================================================
// backend/Repositories/TouristPlaceRepository.cs
// Acceso a datos — Lugares turísticos con PostGIS
// ============================================================

using Dapper;
using Npgsql;
using TurismoTarija.DTOs;
using TurismoTarija.Models;

namespace TurismoTarija.Repositories;

public interface ITouristPlaceRepository
{
    Task<IEnumerable<PlaceSummaryDTO>> GetNearbyAsync(
        double lat, double lng, double radiusKm,
        RecommendationRequestDTO filters, int limit);

    Task<PlaceSummaryDTO?> GetByIdAsync(Guid id);
    Task<IEnumerable<PlaceSummaryDTO>> GetByCategoryAsync(PlaceCategory category);
}

public class TouristPlaceRepository : ITouristPlaceRepository
{
    private readonly string _connectionString;
    private readonly ILogger<TouristPlaceRepository> _logger;

    public TouristPlaceRepository(IConfiguration config, ILogger<TouristPlaceRepository> logger)
    {
        _connectionString = config.GetConnectionString("DefaultConnection")
            ?? throw new InvalidOperationException("Connection string no configurada");
        _logger = logger;
    }

    /// <summary>
    /// Recupera lugares cercanos al usuario usando PostGIS ST_DWithin.
    /// Aplica filtros de presupuesto, accesibilidad y categoría.
    /// Ordena por distancia y rating combinado.
    /// </summary>
    public async Task<IEnumerable<PlaceSummaryDTO>> GetNearbyAsync(
        double lat, double lng, double radiusKm,
        RecommendationRequestDTO filters, int limit)
    {
        await using var conn = new NpgsqlConnection(_connectionString);

        var sql = """
            SELECT
                tp.id,
                tp.name,
                tp.description,
                tp.category::text,
                tp.address,
                ST_Y(tp.location::geometry)   AS latitude,
                ST_X(tp.location::geometry)   AS longitude,
                ST_Distance(
                    tp.location,
                    ST_SetSRID(ST_MakePoint(@lng, @lat), 4326)::geography
                ) / 1000.0                    AS distance_km,
                tp.price_range,
                tp.avg_price_bob,
                tp.rating,
                tp.images,
                tp.tags,
                tp.is_accessible,
                tp.opening_hours
            FROM tourist_places tp
            WHERE
                tp.is_active = TRUE
                AND ST_DWithin(
                    tp.location,
                    ST_SetSRID(ST_MakePoint(@lng, @lat), 4326)::geography,
                    @radiusMeters
                )
                AND (@onlyFree = FALSE OR tp.price_range = 'free')
                AND (@accessibilityNeeded = FALSE OR tp.is_accessible = TRUE)
                AND (@maxPriceBob IS NULL OR tp.avg_price_bob <= @maxPriceBob OR tp.price_range = 'free')
                AND (@categories IS NULL OR tp.category::text = ANY(@categories))
            ORDER BY
                (tp.rating * 0.4 + (1.0 - LEAST(distance_km / @radiusKm, 1.0)) * 0.6) DESC
            LIMIT @limit
            """;

        var parameters = new
        {
            lat,
            lng,
            radiusMeters = radiusKm * 1000,
            radiusKm,
            onlyFree = filters.OnlyFree,
            accessibilityNeeded = filters.AccessibilityNeeded,
            maxPriceBob = filters.BudgetBob,
            categories = filters.PreferredCategories?
                .Select(c => c.ToString().ToLowerInvariant()).ToArray(),
            limit,
        };

        try
        {
            var results = await conn.QueryAsync<PlaceSummaryDTO>(sql, parameters);
            return results;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error consultando lugares cercanos: lat={Lat}, lng={Lng}", lat, lng);
            throw;
        }
    }

    public async Task<PlaceSummaryDTO?> GetByIdAsync(Guid id)
    {
        await using var conn = new NpgsqlConnection(_connectionString);
        const string sql = """
            SELECT
                id, name, description, category::text,
                address,
                ST_Y(location::geometry) AS latitude,
                ST_X(location::geometry) AS longitude,
                0.0 AS distance_km,
                price_range, avg_price_bob, rating,
                images, tags, is_accessible, opening_hours
            FROM tourist_places
            WHERE id = @id AND is_active = TRUE
            """;

        return await conn.QueryFirstOrDefaultAsync<PlaceSummaryDTO>(sql, new { id });
    }

    public async Task<IEnumerable<PlaceSummaryDTO>> GetByCategoryAsync(PlaceCategory category)
    {
        await using var conn = new NpgsqlConnection(_connectionString);
        const string sql = """
            SELECT
                id, name, description, category::text,
                address,
                ST_Y(location::geometry) AS latitude,
                ST_X(location::geometry) AS longitude,
                0.0 AS distance_km,
                price_range, avg_price_bob, rating,
                images, tags, is_accessible, opening_hours
            FROM tourist_places
            WHERE category = @category::place_category AND is_active = TRUE
            ORDER BY rating DESC
            LIMIT 20
            """;

        return await conn.QueryAsync<PlaceSummaryDTO>(sql, new { category = category.ToString().ToLowerInvariant() });
    }
}