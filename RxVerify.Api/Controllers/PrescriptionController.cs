using Microsoft.AspNetCore.Mvc;
using RxVerify.Api.Models;
using RxVerify.Api.Services;
using Microsoft.Extensions.Logging;
using System.IO;
using System.Threading.Tasks;

namespace RxVerify.Api.Controllers;

[ApiController]
[Route("api/prescription")]
public class PrescriptionController : ControllerBase
{
    private readonly IPrescriptionVerificationService _verificationService;
    private readonly IOcrService _ocrService;
    private readonly IBlockchainService _blockchainService;
    private readonly ILogger<PrescriptionController> _logger;

    public PrescriptionController(IPrescriptionVerificationService verificationService, IOcrService ocrService, IBlockchainService blockchainService, ILogger<PrescriptionController> logger)
    {
        _verificationService = verificationService;
        _ocrService = ocrService;
        _blockchainService = blockchainService;
        _logger = logger;
    }

    [HttpPost("verify")]
    [Consumes("multipart/form-data")]
    public async Task<IActionResult> Verify([FromForm] IFormFile image)
    {
        if (image == null || image.Length == 0)
            return BadRequest(new { error = "No image uploaded" });

        using var ms = new MemoryStream();
        await image.CopyToAsync(ms);
        var bytes = ms.ToArray();

        // Use verification service which internally calls IOcrService
        var result = await _verificationService.VerifyPrescriptionAsync(bytes);
        return Ok(result);
    }

    [HttpPost("register")]
    [Consumes("multipart/form-data")]
    public async Task<IActionResult> Register([FromForm] IFormFile image)
    {
        if (image == null || image.Length == 0)
            return BadRequest(new { error = "No image uploaded" });

        using var ms = new MemoryStream();
        await image.CopyToAsync(ms);
        var bytes = ms.ToArray();

        // Extract prescription using OCR
        var prescription = await _ocrService.ExtractPrescriptionDataAsync(bytes);

        // Register on (mock) blockchain
        var tx = await _blockchainService.RegisterPrescriptionAsync(prescription);
        return Ok(new { txHash = tx, prescription });
    }

    [HttpPost("debug-upload")]
    [Consumes("multipart/form-data")]
    public async Task<IActionResult> DebugUpload([FromForm] IFormFile image)
    {
        if (image == null || image.Length == 0)
            return BadRequest(new { error = "No image uploaded" });

        using var ms = new MemoryStream();
        await image.CopyToAsync(ms);
        var bytes = ms.ToArray();

        try
        {
            var extracted = await _ocrService.ExtractPrescriptionDataAsync(bytes);
            return Ok(new { ok = true, extracted });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "OCR failed");
            return StatusCode(500, new { ok = false, error = ex.Message });
        }
    }
}

[ApiController]
[Route("api")]
public class MiscController : ControllerBase
{
    [HttpGet("health")]
    public IActionResult Health() => Ok(new { status = "ok" });

    [HttpGet("test")]
    public IActionResult Test() => Ok(new { message = "API alive" });
}
