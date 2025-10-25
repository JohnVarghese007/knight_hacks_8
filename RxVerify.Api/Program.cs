using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using RxVerify.Api.Services;
using Tesseract;
using System.Text;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// Register application services (OCR, blockchain, verification)
builder.Services.AddSingleton<IOcrService, OcrService>();
builder.Services.AddSingleton<IBlockchainService, BlockchainService>();
builder.Services.AddSingleton<IPrescriptionVerificationService, PrescriptionVerificationService>();

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseRouting();
app.UseAuthorization();

app.MapControllers();

app.MapGet("/", () => Results.Text("RxVerify.Api running"));

app.Run();

// The following classes are legacy/local OCR helper implementations kept in a separate namespace
// to avoid type name collisions with the main services implementation.
namespace RxVerify.Api.OcrLegacy
{
    public interface IOcrService
    {
        Task<PrescriptionData> ExtractPrescriptionDataAsync(byte[] imageBytes);
    }

    public class OcrService : IOcrService
    {
        private readonly ILogger<OcrService> _logger;
        private const string TesseractDataPath = "./tessdata"; // Store tessdata folder here

        public OcrService(ILogger<OcrService> logger)
        {
            _logger = logger;
        }

        public async Task<PrescriptionData> ExtractPrescriptionDataAsync(byte[] imageBytes)
        {
            try
            {
                // Save image temporarily
                var tempFilePath = Path.Combine(Path.GetTempPath(), $"{Guid.NewGuid()}.png");
                await File.WriteAllBytesAsync(tempFilePath, imageBytes);

                string extractedText;
                
                try
                {
                    // Use Tesseract OCR
                    using (var engine = new TesseractEngine(TesseractDataPath, "eng", EngineMode.Default))
                    {
                        using (var img = Pix.LoadFromFile(tempFilePath))
                        {
                            using (var page = engine.Process(img))
                            {
                                extractedText = page.GetText();
                                _logger.LogInformation("OCR Confidence: {Confidence}%", page.GetMeanConfidence() * 100);
                            }
                        }
                    }
                }
                finally
                {
                    // Clean up temp file
                    if (File.Exists(tempFilePath))
                        File.Delete(tempFilePath);
                }

                _logger.LogInformation("Extracted text length: {Length}", extractedText?.Length ?? 0);

                // Parse the extracted text
                return ParsePrescriptionData(extractedText);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error during OCR processing");
                
                // Return mock data on error for testing
                return new PrescriptionData
                {
                    DoctorName = "Dr. Sarah Johnson",
                    PatientName = "John Doe",
                    PrescriptionDate = DateTime.Now,
                    Medications = new List<string> { "Amoxicillin 500mg", "Ibuprofen 200mg" },
                    Dosage = "Take twice daily",
                    Instructions = "Take with food",
                    RawText = $"OCR Error: {ex.Message}"
                };
            }
        }

        private PrescriptionData ParsePrescriptionData(string text)
        {
            var data = new PrescriptionData
            {
                RawText = text,
                PrescriptionDate = DateTime.Now
            };

            if (string.IsNullOrWhiteSpace(text))
            {
                return data;
            }

            var lines = text.Split('\n', StringSplitOptions.RemoveEmptyEntries);
            var medications = new List<string>();

            foreach (var line in lines)
            {
                var lowerLine = line.ToLower().Trim();

                // Extract doctor name
                if (lowerLine.Contains("dr.") || lowerLine.Contains("doctor"))
                {
                    data.DoctorName = ExtractName(line, "dr.");
                }

                // Extract patient name
                if (lowerLine.Contains("patient:") || lowerLine.Contains("name:"))
                {
                    data.PatientName = ExtractName(line, "patient:", "name:");
                }

                // Extract date
                if (TryExtractDate(line, out var date))
                {
                    data.PrescriptionDate = date;
                }

                // Extract medications (lines with common drug indicators)
                if (ContainsMedicationIndicators(lowerLine))
                {
                    medications.Add(line.Trim());
                }

                // Extract dosage
                if (lowerLine.Contains("dosage") || lowerLine.Contains("dose"))
                {
                    data.Dosage = line.Split(':', 2).LastOrDefault()?.Trim() ?? line.Trim();
                }

                // Extract instructions
                if (lowerLine.Contains("instructions") || lowerLine.Contains("directions"))
                {
                    data.Instructions = line.Split(':', 2).LastOrDefault()?.Trim() ?? line.Trim();
                }
            }

            data.Medications = medications.Any() ? medications : new List<string> { "No medications detected" };

            return data;
        }

        private string ExtractName(string line, params string[] prefixes)
        {
            foreach (var prefix in prefixes)
            {
                var index = line.IndexOf(prefix, StringComparison.OrdinalIgnoreCase);
                if (index >= 0)
                {
                    return line.Substring(index + prefix.Length).Trim().Split(',')[0].Trim();
                }
            }
            return line.Trim();
        }

        private bool TryExtractDate(string line, out DateTime date)
        {
            // Try common date formats
            var dateFormats = new[]
            {
                "MM/dd/yyyy", "dd/MM/yyyy", "yyyy-MM-dd",
                "MMM dd, yyyy", "dd MMM yyyy", "MMMM dd, yyyy"
            };

            foreach (var format in dateFormats)
            {
                if (DateTime.TryParseExact(line.Trim(), format, null, 
                    System.Globalization.DateTimeStyles.None, out date))
                {
                    return true;
                }
            }

            // Try general parsing
            return DateTime.TryParse(line, out date);
        }

        private bool ContainsMedicationIndicators(string line)
        {
            var indicators = new[] { "mg", "ml", "tablet", "capsule", "syrup", "injection", "cream", "ointment" };
            return indicators.Any(indicator => line.Contains(indicator));
        }
    }

    public class PrescriptionData
    {
        public string DoctorName { get; set; } = string.Empty;
        public string PatientName { get; set; } = string.Empty;
        public DateTime PrescriptionDate { get; set; }
        public List<string> Medications { get; set; } = new();
        public string Dosage { get; set; } = string.Empty;
        public string Instructions { get; set; } = string.Empty;
        public string RawText { get; set; } = string.Empty;
        public string Hash => ComputeHash();

        private string ComputeHash()
        {
            using var sha256 = System.Security.Cryptography.SHA256.Create();
            var data = $"{DoctorName}|{PatientName}|{PrescriptionDate:yyyy-MM-dd}|{string.Join(",", Medications)}";
            var hashBytes = sha256.ComputeHash(Encoding.UTF8.GetBytes(data));
            return BitConverter.ToString(hashBytes).Replace("-", "").ToLowerInvariant();
        }
    }
}