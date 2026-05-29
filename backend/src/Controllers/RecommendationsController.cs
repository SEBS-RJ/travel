// ============================================================
// backend/Controllers/RecommendationsController.cs
// Endpoint REST — Recomendaciones turísticas
// ============================================================

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using TurismoTarija.DTOs;
using TurismoTarija.Services;

namespace TurismoTarija.Controllers;

[ApiController]
[Route("api/v1/[controller]")]
[Produces("application/json")]
public class RecommendationsController : ControllerBase
{
    private readonly IRecommendationService _service;
    private readonly ILogger<RecommendationsController> _logger;

    public RecommendationsController(
        IRecommendationService service,
        ILogger<RecommendationsController> logger)
    {
        _service = service;
        _logger = logger;
    }

    /// <summary>
    /// Obtiene recomendaciones turísticas personalizadas.
    /// </summary>
    /// <remarks>
    /// Si no se provee ubicación, se usa el centro de Tarija como referencia.
    ///
    /// Ejemplo de request:
    ///
    ///     POST /api/v1/recommendations
    ///     {
    ///         "latitude": -21.5355,
    ///         "longitude": -64.7296,
    ///         "budgetBob": 100,
    ///         "availableMinutes": 180,
    ///         "travelParty": "pareja",
    ///         "limit": 5
    ///     }
    ///
    /// </remarks>
    [HttpPost]
    [AllowAnonymous]
    [EnableRateLimiting("fixed")]
    [ProducesResponseType(typeof(RecommendationResponseDTO), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status429TooManyRequests)]
    [ProducesResponseType(StatusCodes.Status500InternalServerError)]
    public async Task<IActionResult> GetRecommendations(
        [FromBody] RecommendationRequestDTO request)
    {
        if (!ModelState.IsValid)
            return BadRequest(ModelState);

        try
        {
            // Extraer userId si está autenticado (opcional)
            var userId = User.Identity?.IsAuthenticated == true
                ? Guid.Parse(User.FindFirst("sub")!.Value)
                : (Guid?)null;

            var result = await _service.GetRecommendationsAsync(request, userId);

            _logger.LogInformation(
                "Recomendaciones generadas: {Count} resultados | party={Party} | budget={Budget}",
                result.TotalFound, request.TravelParty, request.BudgetBob);

            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error generando recomendaciones");
            return StatusCode(500, new { error = "Error interno del servidor" });
        }
    }

    /// <summary>
    /// Obtiene el detalle de un lugar turístico por ID.
    /// </summary>
    [HttpGet("places/{id:guid}")]
    [AllowAnonymous]
    [ProducesResponseType(typeof(PlaceSummaryDTO), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetPlace(Guid id)
    {
        // Importado desde repositorio vía servicio (simplificado aquí)
        return Ok(new { id, message = "Endpoint disponible — implementar GetByIdAsync" });
    }
}