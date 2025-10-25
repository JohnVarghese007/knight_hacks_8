using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using System.IO;
using Tesseract;

namespace RxVerify.Api.Controllers;

[ApiController]
[Route("api/ocr")]
public class OcrDebugController : ControllerBase
{
    private readonly ILogger<OcrDebugController> _logger;

    public OcrDebugController(ILogger<OcrDebugController> logger)
    {
        _logger = logger;
    }

    [HttpGet("info")]
    public IActionResult Info()
    {
        var tessDataPath = Path.Combine(AppContext.BaseDirectory, "tessdata");
        var exists = Directory.Exists(tessDataPath);
        var files = exists ? Directory.GetFiles(tessDataPath).Select(Path.GetFileName).ToArray() : Array.Empty<string>();

        var engineOk = false;
        string engineError = string.Empty;
        try
        {
            if (exists)
            {
                using var engine = new TesseractEngine(tessDataPath, "eng", EngineMode.Default);
                engineOk = true;
            }
        }
        catch (Exception ex)
        {
            engineError = ex.Message;
            _logger.LogError(ex, "Tesseract engine init failed");
        }

        return Ok(new { tessDataPath, exists, files, engineOk, engineError });
    }
}
