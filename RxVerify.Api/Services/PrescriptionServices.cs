using RxVerify.Api.Models;
using System.Security.Cryptography;
using System.Text;
using System.IO;
using Tesseract;

namespace RxVerify.Api.Services;

public interface IOcrService
{
    Task<PrescriptionModel> ExtractPrescriptionDataAsync(byte[] imageBytes);
}

public interface IBlockchainService
{
    Task<bool> VerifyPrescriptionHashAsync(string hash);
    Task<string> RegisterPrescriptionAsync(PrescriptionModel prescription);
}

public interface IPrescriptionVerificationService
{
    Task<VerificationResult> VerifyPrescriptionAsync(byte[] imageBytes);
}

public class OcrService : IOcrService
{
    private readonly ILogger<OcrService> _logger;

    public OcrService(ILogger<OcrService> logger)
    {
        _logger = logger;
    }

    public async Task<PrescriptionModel> ExtractPrescriptionDataAsync(byte[] imageBytes)
    {
        try
        {
            // Check if we have valid image data
            if (imageBytes == null || imageBytes.Length == 0)
            {
                throw new ArgumentException("No image data provided");
            }

            // Check if it's a valid image format
            if (imageBytes.Length < 100) // Too small to be a real image
            {
                throw new ArgumentException("Image data too small - likely not a real image");
            }

            // Use Tesseract (writes bytes to temp file then processes image)
            string extractedText = string.Empty;
            var tempFilePath = Path.Combine(Path.GetTempPath(), $"{Guid.NewGuid()}.png");
            await File.WriteAllBytesAsync(tempFilePath, imageBytes);
            try
            {
                // tessdata folder is copied to output (see csproj)
                var tessDataPath = Path.Combine(AppContext.BaseDirectory, "tessdata");
                if (!Directory.Exists(tessDataPath))
                {
                    var msg = $"tessdata folder not found at '{tessDataPath}'. Make sure tessdata is copied to output or exists there.";
                    _logger?.LogError(msg);
                    throw new DirectoryNotFoundException(msg);
                }

                try
                {
                    using var engine = new TesseractEngine(tessDataPath, "eng", EngineMode.Default);
                    using var img = Pix.LoadFromFile(tempFilePath);
                    using var page = engine.Process(img);
                    extractedText = page.GetText() ?? string.Empty;

                    // Record confidence and log snippet to help debugging OCR quality
                    double confidence = 0;
                    try
                    {
                        confidence = page.GetMeanConfidence();
                        _logger?.LogInformation("OCR mean confidence: {Confidence}", confidence);
                    }
                    catch { }

                    var snippet = extractedText.Length > 400 ? extractedText.Substring(0, 400) + "..." : extractedText;
                    _logger?.LogInformation("OCR extracted text (snippet): {Snippet}", snippet);

                    // attach confidence to prescription after parsing
                    var prescriptionTemp = ParsePrescriptionText(extractedText);
                    prescriptionTemp.RawText = extractedText;
                    prescriptionTemp.Hash = GenerateHash(extractedText);
                    prescriptionTemp.OcrConfidence = confidence;

                    return prescriptionTemp;
                }
                catch (DllNotFoundException dllEx)
                {
                    // Native Tesseract/Leptonica DLL missing
                    _logger?.LogError(dllEx, "Native Tesseract/Leptonica DLL missing. Ensure native runtime libraries are available.");
                    throw;
                }
            }
            finally
            {
                if (File.Exists(tempFilePath))
                    File.Delete(tempFilePath);
            }
            
            // (Parsing+return handled above after OCR success)
            // Should not reach here because successful OCR returns earlier
            return new PrescriptionModel();
        }
        catch (Exception ex)
        {
            // Fallback to mock data if OCR fails
            return new PrescriptionModel
            {
                DoctorName = "Dr. Sarah Johnson",
                PatientName = "John Doe",
                PrescriptionDate = DateTime.Now.AddDays(-1),
                Medications = new List<string> { "Amoxicillin 500mg", "Ibuprofen 200mg" },
                Dosage = "Take twice daily",
                Instructions = "Take with food",
                RawText = $"OCR Error: {ex.Message}",
                Hash = GenerateHash($"Error prescription data - {ex.Message}")
            };
        }
    }
    
    private PrescriptionModel ParsePrescriptionText(string text)
    {
        var prescription = new PrescriptionModel();
        
        // Simple text parsing - you can enhance this
        var lines = text.Split('\n', StringSplitOptions.RemoveEmptyEntries);
        
        foreach (var line in lines)
        {
            var lowerLine = line.ToLower();
            
            // Look for doctor name patterns
            if (lowerLine.Contains("dr.") || lowerLine.Contains("doctor"))
            {
                prescription.DoctorName = line.Trim();
            }
            
            // Look for patient name patterns
            if (lowerLine.Contains("patient:") || lowerLine.Contains("name:"))
            {
                prescription.PatientName = line.Split(':').LastOrDefault()?.Trim() ?? "";
            }
            
            // Look for date patterns
            if (lowerLine.Contains("date:") || lowerLine.Contains("prescribed"))
            {
                if (DateTime.TryParse(line.Split(':').LastOrDefault()?.Trim(), out var date))
                {
                    prescription.PrescriptionDate = date;
                }
            }
            
            // Look for medication patterns
            if (lowerLine.Contains("mg") || lowerLine.Contains("tablet") || lowerLine.Contains("capsule"))
            {
                prescription.Medications.Add(line.Trim());
            }
        }
        
        // Set defaults if not found
        if (string.IsNullOrEmpty(prescription.DoctorName))
            prescription.DoctorName = "Dr. Unknown";
        if (string.IsNullOrEmpty(prescription.PatientName))
            prescription.PatientName = "Patient Unknown";
        if (prescription.PrescriptionDate == default)
            prescription.PrescriptionDate = DateTime.Now;
        if (!prescription.Medications.Any())
            prescription.Medications.Add("Medication not detected");
            
        return prescription;
    }
    
    private string GenerateHash(string data)
    {
        using var sha256 = SHA256.Create();
        var hashBytes = sha256.ComputeHash(Encoding.UTF8.GetBytes(data));
        return Convert.ToHexString(hashBytes).ToLower();
    }
}

public class BlockchainService : IBlockchainService
{
    private readonly List<BlockchainPrescription> _mockBlockchain = new();
    
    public async Task<bool> VerifyPrescriptionHashAsync(string hash)
    {
        await Task.Delay(50); // Simulate blockchain call
        
        // Mock blockchain verification
        // In Phase 3, this will connect to actual blockchain
        return _mockBlockchain.Any(p => p.Hash == hash && p.IsValid);
    }
    
    public async Task<string> RegisterPrescriptionAsync(PrescriptionModel prescription)
    {
        await Task.Delay(100); // Simulate blockchain transaction
        
        var blockchainPrescription = new BlockchainPrescription
        {
            Hash = prescription.Hash,
            DoctorName = prescription.DoctorName,
            PatientName = prescription.PatientName,
            PrescriptionDate = prescription.PrescriptionDate,
            RegisteredDate = DateTime.Now,
            IsValid = true
        };
        
        _mockBlockchain.Add(blockchainPrescription);
        return prescription.Hash;
    }
}

public class PrescriptionVerificationService : IPrescriptionVerificationService
{
    private readonly IOcrService _ocrService;
    private readonly IBlockchainService _blockchainService;
    
    public PrescriptionVerificationService(IOcrService ocrService, IBlockchainService blockchainService)
    {
        _ocrService = ocrService;
        _blockchainService = blockchainService;
    }
    
    public async Task<VerificationResult> VerifyPrescriptionAsync(byte[] imageBytes)
    {
        try
        {
            // Extract prescription data using OCR
            var prescription = await _ocrService.ExtractPrescriptionDataAsync(imageBytes);
            
            // Verify against blockchain
            var isBlockchainValid = await _blockchainService.VerifyPrescriptionHashAsync(prescription.Hash);
            
            // Perform tampering detection
            var anomalies = DetectAnomalies(prescription);
            
            var result = new VerificationResult
            {
                ExtractedData = prescription,
                IsAuthentic = isBlockchainValid && !anomalies.Any(),
                Status = DetermineStatus(isBlockchainValid, anomalies),
                ConfidenceScore = CalculateConfidenceScore(isBlockchainValid, anomalies),
                Message = GenerateMessage(isBlockchainValid, anomalies),
                Anomalies = anomalies
            };
            
            return result;
        }
        catch (Exception ex)
        {
            return new VerificationResult
            {
                IsAuthentic = false,
                Status = "Error",
                ConfidenceScore = 0,
                Message = $"Error processing prescription: {ex.Message}",
                Anomalies = new List<string> { "Processing error" }
            };
        }
    }
    
    private List<string> DetectAnomalies(PrescriptionModel prescription)
    {
        var anomalies = new List<string>();
        
        // Check for common tampering indicators
        if (string.IsNullOrWhiteSpace(prescription.DoctorName))
            anomalies.Add("Missing doctor name");
            
        if (string.IsNullOrWhiteSpace(prescription.PatientName))
            anomalies.Add("Missing patient name");
            
        if (prescription.PrescriptionDate > DateTime.Now)
            anomalies.Add("Future prescription date");
            
        if (!prescription.Medications.Any())
            anomalies.Add("No medications listed");
            
        // Check for suspicious patterns in raw text
        if (prescription.RawText.Contains("FAKE") || prescription.RawText.Contains("TEST"))
            anomalies.Add("Suspicious text patterns detected");
            
        return anomalies;
    }
    
    private string DetermineStatus(bool isBlockchainValid, List<string> anomalies)
    {
        if (isBlockchainValid && !anomalies.Any())
            return "Authentic";
        else if (anomalies.Any())
            return "Suspicious";
        else
            return "Fake";
    }
    
    private double CalculateConfidenceScore(bool isBlockchainValid, List<string> anomalies)
    {
        double score = isBlockchainValid ? 0.7 : 0.0;
        score -= anomalies.Count * 0.1;
        return Math.Max(0, Math.Min(1, score));
    }
    
    private string GenerateMessage(bool isBlockchainValid, List<string> anomalies)
    {
        if (isBlockchainValid && !anomalies.Any())
            return "✅ Prescription verified as authentic";
        else if (anomalies.Any())
            return $"⚠️ Prescription shows suspicious patterns: {string.Join(", ", anomalies)}";
        else
            return "❌ Prescription not found in blockchain registry";
    }
}