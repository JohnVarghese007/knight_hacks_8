namespace RxVerify.Api.Models;

public class PrescriptionModel
{
    public string DoctorName { get; set; } = string.Empty;
    public string PatientName { get; set; } = string.Empty;
    public DateTime PrescriptionDate { get; set; }
    public List<string> Medications { get; set; } = new();
    public string Dosage { get; set; } = string.Empty;
    public string Instructions { get; set; } = string.Empty;
    public string RawText { get; set; } = string.Empty;
    public string Hash { get; set; } = string.Empty;
    // Mean OCR confidence reported by Tesseract (0..1)
    public double? OcrConfidence { get; set; }
}

public class VerificationResult
{
    public bool IsAuthentic { get; set; }
    public string Status { get; set; } = string.Empty;
    public double ConfidenceScore { get; set; }
    public string Message { get; set; } = string.Empty;
    public PrescriptionModel? ExtractedData { get; set; }
    public List<string> Anomalies { get; set; } = new();
}

public class UploadRequest
{
    public IFormFile Image { get; set; } = null!;
}

public class BlockchainPrescription
{
    public string Hash { get; set; } = string.Empty;
    public string DoctorName { get; set; } = string.Empty;
    public string PatientName { get; set; } = string.Empty;
    public DateTime PrescriptionDate { get; set; }
    public DateTime RegisteredDate { get; set; }
    public bool IsValid { get; set; }
}

