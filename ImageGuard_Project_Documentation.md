# ImageGuard: Image-Based Prompt Injection Detection System

## Project Specification Document

**Version:** 0.1  
**Status:** Draft  
**Last Updated:** 17 December 2025

---

## 1. Executive Summary

ImageGuard is a lightweight, LLM-free guardrail system designed to detect and flag prompt injection attempts embedded within images before they reach Large Language Models. As multimodal AI systems become increasingly prevalent, attackers have begun exploiting the image input channel to bypass traditional text-based security measures. This project addresses that vulnerability using classical image processing, computer vision, and pattern recognition techniques—without relying on neural language models for detection.

The system provides a binary classification (safe/unsafe) along with a confidence score and detailed analysis report, enabling organizations to implement defense-in-depth strategies for their AI deployments.

---

## 2. Problem Statement

### 2.1 Background

Modern Large Language Models with vision capabilities (GPT-4V, Claude with vision, Gemini, etc.) process images alongside text inputs. This creates a new attack surface where malicious instructions can be embedded within images through various means:

- Visible text containing injection phrases
- Hidden text using low-contrast colors or small fonts
- Steganographic encoding of instructions
- Adversarial perturbations designed to influence model behavior
- QR codes or barcodes containing malicious payloads
- Screenshots of chat interfaces with manipulated context

### 2.2 Current Gap

Most existing prompt injection defenses focus on text-based inputs, leaving image-based vectors largely unaddressed. Organizations deploying multimodal AI systems need a pre-processing layer that can flag potentially malicious images before they reach the LLM.

### 2.3 Why Not Use LLMs for Detection?

While LLMs could theoretically detect prompt injections in images, this approach has critical flaws:

- **Circular vulnerability**: Using an LLM to detect injections means the detection system itself is vulnerable to the same attacks
- **Latency and cost**: Adding another LLM call increases response time and operational costs
- **Reliability**: LLMs can be manipulated into ignoring or misclassifying injection attempts
- **Determinism**: Classical methods provide consistent, reproducible results

---

## 3. Project Goals and Objectives

### 3.1 Primary Goals

1. **Detect visible text-based injections** with >95% recall on common injection patterns
2. **Identify hidden or obfuscated text** using contrast analysis and edge detection
3. **Flag steganographic content** through frequency domain analysis
4. **Provide actionable risk scores** with detailed explanations
5. **Maintain low latency** (<500ms per image on standard hardware)

### 3.2 Secondary Goals

1. Support batch processing for high-throughput applications
2. Provide an extensible architecture for adding new detection methods
3. Generate audit logs for security compliance
4. Offer both API and CLI interfaces

### 3.3 Non-Goals

- Real-time video processing (future consideration)
- Detection of non-injection malicious content (NSFW, violence, etc.)
- Replacing existing content moderation systems

---

## 4. System Architecture

### 4.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              IMAGE INPUT                                     │
│                    (PNG, JPEG, WebP, GIF, BMP, TIFF)                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PREPROCESSING LAYER                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ Format          │  │ Resolution      │  │ Metadata                    │  │
│  │ Normalization   │  │ Standardization │  │ Extraction                  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PARALLEL ANALYSIS PIPELINE                           │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      MODULE 1: TEXT EXTRACTION & ANALYSIS              │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐    │  │
│  │  │ Text Region │ -> │ OCR Engine  │ -> │ Pattern Matching       │    │  │
│  │  │ Detection   │    │ (Tesseract) │    │ (Regex + Keywords)     │    │  │
│  │  └─────────────┘    └─────────────┘    └─────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      MODULE 2: HIDDEN TEXT DETECTION                   │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐    │  │
│  │  │ Contrast    │ -> │ Edge        │ -> │ Multi-threshold        │    │  │
│  │  │ Enhancement │    │ Detection   │    │ Binarization           │    │  │
│  │  └─────────────┘    └─────────────┘    └─────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      MODULE 3: FREQUENCY ANALYSIS                      │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐    │  │
│  │  │ FFT/DCT     │ -> │ Spectral    │ -> │ Anomaly                │    │  │
│  │  │ Transform   │    │ Analysis    │    │ Detection              │    │  │
│  │  └─────────────┘    └─────────────┘    └─────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      MODULE 4: STEGANOGRAPHY DETECTION                 │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐    │  │
│  │  │ LSB         │ -> │ Chi-Square  │ -> │ Histogram              │    │  │
│  │  │ Analysis    │    │ Test        │    │ Analysis               │    │  │
│  │  └─────────────┘    └─────────────┘    └─────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      MODULE 5: STRUCTURAL ANALYSIS                     │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐    │  │
│  │  │ QR/Barcode  │ -> │ Screenshot  │ -> │ Synthetic Text         │    │  │
│  │  │ Detection   │    │ Detection   │    │ Overlay Detection      │    │  │
│  │  └─────────────┘    └─────────────┘    └─────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ENSEMBLE COMBINER                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Weighted Score Aggregation + Confidence Calibration + Threshold    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OUTPUT LAYER                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐   │
│  │ Risk Score   │  │ Binary       │  │ Detailed     │  │ Marked Image   │   │
│  │ (0.0 - 1.0)  │  │ Classification│ │ Report       │  │ (Optional)     │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Component Descriptions

#### 4.2.1 Preprocessing Layer

Normalizes input images to ensure consistent analysis across the pipeline:

- **Format Normalization**: Converts all inputs to a standard internal format (RGB numpy array)
- **Resolution Standardization**: Scales images to optimal processing resolution while preserving aspect ratio
- **Metadata Extraction**: Extracts EXIF data, color profiles, and embedded information for analysis

#### 4.2.2 Analysis Modules

Each module operates independently and produces a module-specific risk score (0.0-1.0):

| Module | Primary Function | Key Techniques |
|--------|-----------------|----------------|
| Text Extraction | Detect visible injection text | OCR, regex, keyword matching |
| Hidden Text | Find obfuscated/low-contrast text | Contrast enhancement, multi-threshold |
| Frequency Analysis | Detect spectral anomalies | FFT, DCT, wavelet analysis |
| Steganography | Find hidden data | LSB analysis, chi-square, RS analysis |
| Structural | Identify suspicious elements | QR detection, screenshot classification |

#### 4.2.3 Ensemble Combiner

Aggregates individual module scores using configurable weights:

```
Final_Score = Σ(weight_i × score_i) / Σ(weight_i)
```

Default weights prioritize text-based detection (highest threat probability) while maintaining sensitivity to other vectors.

---

## 5. Detailed Module Specifications

### 5.1 Module 1: Text Extraction and Analysis

#### 5.1.1 Purpose

Detect and analyze visible text within images to identify prompt injection patterns.

#### 5.1.2 Processing Pipeline

```
Input Image
     │
     ▼
┌─────────────────────────────────────┐
│ Text Region Detection               │
│ - EAST text detector                │
│ - CRAFT character detection         │
│ - Contour-based fallback            │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│ Region Preprocessing                │
│ - Deskewing                         │
│ - Contrast normalization            │
│ - Noise reduction                   │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│ OCR Engine (Tesseract)              │
│ - Multiple PSM modes                │
│ - Confidence scoring                │
│ - Multi-language support            │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│ Pattern Analysis                    │
│ - Regex injection patterns          │
│ - Keyword dictionary matching       │
│ - N-gram analysis                   │
│ - Semantic structure detection      │
└─────────────────────────────────────┘
     │
     ▼
Module Score + Matched Patterns
```

#### 5.1.3 Injection Pattern Database

The system maintains a curated database of known injection patterns:

**Category: Direct Instructions**
```
- "ignore previous instructions"
- "ignore all prior instructions"
- "disregard your instructions"
- "forget your system prompt"
- "override your programming"
```

**Category: Role Manipulation**
```
- "you are now"
- "pretend you are"
- "act as if you are"
- "from now on you will"
- "your new role is"
```

**Category: Jailbreak Attempts**
```
- "DAN mode"
- "developer mode"
- "no restrictions"
- "bypass filters"
- "unlock capabilities"
```

**Category: Context Manipulation**
```
- "end of system prompt"
- "user input begins"
- "assistant response"
- "[INST]", "[/INST]"
- "<|system|>", "<|user|>"
```

**Category: Encoded Instructions**
```
- Base64 encoded text patterns
- ROT13 encoded content
- Unicode homoglyph substitutions
- Leetspeak variations
```

#### 5.1.4 Scoring Algorithm

```python
def calculate_text_score(extracted_text, matched_patterns):
    base_score = 0.0
    
    # Direct pattern matches
    for pattern in matched_patterns:
        base_score += pattern.severity_weight
    
    # Text density factor (high text-to-image ratio is suspicious)
    text_density = len(extracted_text) / image_area
    if text_density > DENSITY_THRESHOLD:
        base_score += 0.1 * (text_density / DENSITY_THRESHOLD)
    
    # Instruction-like structure detection
    if contains_imperative_structure(extracted_text):
        base_score += 0.15
    
    # Normalize to [0, 1]
    return min(1.0, base_score)
```

### 5.2 Module 2: Hidden Text Detection

#### 5.2.1 Purpose

Detect text that has been deliberately obscured through low contrast, small size, or strategic placement.

#### 5.2.2 Techniques

**Multi-threshold Binarization**

Apply multiple binarization thresholds to reveal text at different contrast levels:

```python
thresholds = [50, 100, 150, 200, 250]
for threshold in thresholds:
    binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    # Run OCR on each binary version
    # Compare results to find hidden text
```

**Contrast Enhancement Pipeline**

```
Original → CLAHE → Histogram Equalization → Adaptive Threshold → OCR
    │
    └──→ Compare extracted text vs. standard OCR results
         Additional text found = potential hidden content
```

**Color Channel Separation**

Hidden text often exists in only one color channel:

```python
channels = cv2.split(image)
for channel in channels:
    # Process each channel independently
    # Hidden text may appear in only R, G, or B
```

**Edge-based Detection**

Text has distinctive edge patterns even when low-contrast:

```python
edges = cv2.Canny(image, 50, 150)
# Analyze edge density in grid regions
# High edge density with no visible text = potential hidden text
```

#### 5.2.3 Suspicious Regions

The module flags specific regions commonly used to hide text:

- Image corners (especially bottom-right)
- Borders and edges
- Regions matching background color (±5 in RGB space)
- Areas with unusual noise patterns

### 5.3 Module 3: Frequency Domain Analysis

#### 5.3.1 Purpose

Detect anomalies in the frequency spectrum that may indicate:
- Steganographic content
- Adversarial perturbations
- Synthetic text overlays
- Image manipulation

#### 5.3.2 Analysis Techniques

**Fast Fourier Transform (FFT) Analysis**

```python
def analyze_fft(image):
    f_transform = np.fft.fft2(image)
    f_shift = np.fft.fftshift(f_transform)
    magnitude_spectrum = np.abs(f_shift)
    
    # Analyze for anomalies
    # - Unexpected periodic patterns
    # - High-frequency spikes (may indicate embedded data)
    # - Unusual energy distribution
    
    return anomaly_score
```

**Discrete Cosine Transform (DCT) Analysis**

JPEG images use DCT compression; anomalies in DCT coefficients can reveal tampering:

```python
def analyze_dct(image):
    # Divide into 8x8 blocks (matching JPEG)
    for block in blocks:
        dct_block = cv2.dct(block)
        # Compare coefficient distribution to natural images
        # LSB of DCT coefficients often used for steganography
```

**Wavelet Analysis**

Multi-scale analysis for detecting localized anomalies:

```python
import pywt

def wavelet_analysis(image):
    coeffs = pywt.dwt2(image, 'haar')
    cA, (cH, cV, cD) = coeffs
    
    # Analyze detail coefficients for unnatural patterns
    # Synthetic text has distinctive wavelet signatures
```

#### 5.3.3 Baseline Comparison

The module maintains statistical baselines for "natural" images:

- Expected frequency distribution curves
- Typical DCT coefficient histograms
- Normal wavelet energy distributions

Deviations from these baselines contribute to the anomaly score.

### 5.4 Module 4: Steganography Detection

#### 5.4.1 Purpose

Detect hidden data embedded within the image using common steganographic techniques.

#### 5.4.2 LSB (Least Significant Bit) Analysis

The most common steganographic method modifies the least significant bits of pixel values:

```python
def lsb_analysis(image):
    # Extract LSB plane
    lsb_plane = image & 1
    
    # Statistical analysis
    # - Chi-square test for non-random distribution
    # - Pairs analysis
    # - RS analysis (Regular/Singular groups)
    
    # Visual analysis
    # - LSB plane should appear as random noise
    # - Patterns indicate hidden data
```

#### 5.4.3 Chi-Square Attack

Detects LSB embedding by analyzing the statistical distribution of pixel value pairs:

```python
def chi_square_test(image):
    histogram = calculate_histogram(image)
    
    # Group adjacent histogram values (pairs)
    # Steganography tends to equalize pairs
    
    expected = [(h[i] + h[i+1]) / 2 for i in range(0, 256, 2)]
    observed = [h[i] for i in range(0, 256, 2)]
    
    chi_sq = sum((o - e)**2 / e for o, e in zip(observed, expected))
    p_value = chi2.sf(chi_sq, df=127)
    
    return p_value  # Low p-value indicates steganography
```

#### 5.4.4 RS Analysis

A more sophisticated method that analyzes regular and singular pixel groups:

```python
def rs_analysis(image):
    # Define flipping function
    # Count regular (R) and singular (S) groups
    # Compare R-S with R(-1)-S(-1)
    # Significant difference indicates hidden data
```

#### 5.4.5 Sample Pair Analysis (SPA)

Analyzes the relationship between adjacent pixel values:

```python
def spa_analysis(image):
    # Count close pairs and same pairs
    # Estimate embedding rate
    # High embedding rate = potential steganography
```

### 5.5 Module 5: Structural Analysis

#### 5.5.1 Purpose

Identify structural elements within images that may contain or facilitate prompt injection.

#### 5.5.2 QR Code and Barcode Detection

```python
def detect_codes(image):
    # QR Code detection
    qr_detector = cv2.QRCodeDetector()
    data, bbox, _ = qr_detector.detectAndDecode(image)
    
    if data:
        # Analyze decoded content for injection patterns
        return analyze_payload(data)
    
    # Barcode detection using pyzbar
    barcodes = decode(image)
    for barcode in barcodes:
        analyze_payload(barcode.data)
```

#### 5.5.3 Screenshot Detection

Screenshots of chat interfaces are a common injection vector:

```python
def detect_screenshot(image):
    features = {
        'has_ui_elements': detect_ui_patterns(image),
        'has_chat_bubbles': detect_chat_layout(image),
        'has_system_chrome': detect_browser_chrome(image),
        'has_timestamps': detect_timestamp_patterns(image),
        'aspect_ratio': check_screen_aspect_ratios(image)
    }
    
    return calculate_screenshot_probability(features)
```

**UI Pattern Detection**

- Common button shapes and positions
- Input field rectangles
- Navigation elements
- Status bars and headers

**Chat Interface Patterns**

- Message bubble shapes
- Alternating left/right alignment
- Avatar placeholders
- "Send" button patterns

#### 5.5.4 Synthetic Text Overlay Detection

Detect text that has been artificially added to an image:

```python
def detect_synthetic_text(image):
    # Analyze text region boundaries
    # - Sharp, artificial edges indicate overlaid text
    # - Natural text in photos has softer boundaries
    
    # Color consistency analysis
    # - Overlaid text often has perfectly uniform color
    # - Natural text varies slightly
    
    # Compression artifact analysis
    # - Added text may have different compression artifacts
    # - Double compression reveals editing
```

---

## 6. Implementation Phases

### Phase 1: Foundation (Weeks 1-3)

**Objective**: Establish core infrastructure and basic text detection

**Deliverables**:
- Project scaffolding and CI/CD pipeline
- Image preprocessing module
- Basic OCR integration (Tesseract)
- Initial pattern matching database
- Unit test framework

**Technical Tasks**:
1. Set up Python project structure with poetry/pip
2. Implement image format handlers (PIL/OpenCV)
3. Integrate Tesseract OCR with multiple PSM modes
4. Create regex-based pattern matcher
5. Build keyword dictionary with severity weights
6. Implement basic scoring algorithm
7. Create CLI interface for testing

**Success Criteria**:
- Can process common image formats (PNG, JPEG, WebP)
- Detects visible text with >90% accuracy
- Matches known injection patterns
- Processing time <200ms for standard images

### Phase 2: Hidden Text Detection (Weeks 4-5)

**Objective**: Detect obfuscated and low-contrast text

**Deliverables**:
- Contrast enhancement pipeline
- Multi-threshold binarization
- Color channel analysis
- Edge-based text detection
- Region-of-interest flagging

**Technical Tasks**:
1. Implement CLAHE and histogram equalization
2. Build multi-threshold processing pipeline
3. Add color channel separation analysis
4. Integrate Canny edge detection
5. Create suspicious region detector
6. Extend scoring algorithm for hidden text

**Success Criteria**:
- Detects white-on-light-gray text
- Finds text in corners and borders
- Identifies single-channel hidden text
- False positive rate <5%

### Phase 3: Frequency Analysis (Weeks 6-7)

**Objective**: Detect spectral anomalies indicating manipulation

**Deliverables**:
- FFT analysis module
- DCT coefficient analyzer
- Wavelet decomposition
- Baseline comparison system
- Anomaly scoring

**Technical Tasks**:
1. Implement FFT with anomaly detection
2. Build DCT block analyzer for JPEG
3. Add wavelet-based analysis (PyWavelets)
4. Create natural image baseline models
5. Implement deviation scoring
6. Optimize for performance

**Success Criteria**:
- Detects synthetic image modifications
- Identifies unusual frequency patterns
- Processing time <100ms
- Calibrated baseline models

### Phase 4: Steganography Detection (Weeks 8-9)

**Objective**: Detect hidden data embedded in images

**Deliverables**:
- LSB extraction and analysis
- Chi-square statistical test
- RS analysis implementation
- Sample pair analysis
- Combined stego score

**Technical Tasks**:
1. Implement LSB plane extraction
2. Build chi-square test for pixel pairs
3. Add RS analysis for regular/singular groups
4. Implement SPA for embedding estimation
5. Create ensemble stego scorer
6. Add visual LSB plane output

**Success Criteria**:
- Detects LSB embedding >50% capacity
- Chi-square p-value threshold calibrated
- RS analysis functional
- Combined detection rate >80%

### Phase 5: Structural Analysis (Weeks 10-11)

**Objective**: Identify structural injection vectors

**Deliverables**:
- QR/barcode detector and analyzer
- Screenshot classifier
- Synthetic text overlay detector
- UI element recognizer

**Technical Tasks**:
1. Integrate OpenCV QR detector
2. Add pyzbar for barcode support
3. Build screenshot pattern classifier
4. Implement overlay detection heuristics
5. Create UI element pattern library
6. Add decoded content analysis

**Success Criteria**:
- Detects and decodes QR codes
- Classifies screenshots with >85% accuracy
- Identifies chat interface patterns
- Flags synthetic text overlays

### Phase 6: Integration and Optimization (Weeks 12-14)

**Objective**: Combine modules into production-ready system

**Deliverables**:
- Ensemble combiner with calibrated weights
- REST API server
- Comprehensive documentation
- Performance optimization
- Production deployment guide

**Technical Tasks**:
1. Implement weighted score aggregation
2. Calibrate module weights using test data
3. Build FastAPI server with async processing
4. Add batch processing capability
5. Optimize critical paths for performance
6. Create Docker container
7. Write deployment documentation
8. Conduct security review

**Success Criteria**:
- End-to-end processing <500ms
- API handles 100 req/sec
- Documentation complete
- All tests passing
- Security review completed

---

## 7. API Specification

### 7.1 REST API Endpoints

#### Analyze Single Image

```
POST /api/v1/analyze
Content-Type: multipart/form-data

Parameters:
  - image: (file) Image to analyze
  - modules: (string[], optional) Specific modules to run
  - return_marked: (boolean, optional) Return image with annotations

Response:
{
  "request_id": "uuid",
  "timestamp": "ISO8601",
  "processing_time_ms": 234,
  "result": {
    "classification": "SAFE" | "SUSPICIOUS" | "DANGEROUS",
    "risk_score": 0.73,
    "confidence": 0.89,
    "threshold_used": 0.5
  },
  "module_scores": {
    "text_extraction": {
      "score": 0.85,
      "details": {
        "text_found": true,
        "extracted_text": "ignore previous instructions...",
        "patterns_matched": ["ignore_instructions", "role_manipulation"],
        "text_regions": 3
      }
    },
    "hidden_text": {
      "score": 0.2,
      "details": {...}
    },
    "frequency_analysis": {
      "score": 0.1,
      "details": {...}
    },
    "steganography": {
      "score": 0.05,
      "details": {...}
    },
    "structural": {
      "score": 0.3,
      "details": {...}
    }
  },
  "marked_image_url": "/results/uuid/marked.png" // if requested
}
```

#### Batch Analysis

```
POST /api/v1/analyze/batch
Content-Type: multipart/form-data

Parameters:
  - images: (file[]) Images to analyze (max 100)
  - modules: (string[], optional) Specific modules to run

Response:
{
  "batch_id": "uuid",
  "total_images": 50,
  "results": [
    {...}, // Same structure as single analysis
  ],
  "summary": {
    "safe": 45,
    "suspicious": 4,
    "dangerous": 1,
    "average_processing_time_ms": 198
  }
}
```

#### Health Check

```
GET /api/v1/health

Response:
{
  "status": "healthy",
  "version": "1.0.0",
  "modules_loaded": ["text_extraction", "hidden_text", ...],
  "uptime_seconds": 86400
}
```

### 7.2 CLI Interface

```bash
# Analyze single image
imageguard analyze image.png

# Analyze with specific modules
imageguard analyze image.png --modules text,hidden,stego

# Batch analyze directory
imageguard analyze ./images/ --output results.json

# Generate marked image
imageguard analyze image.png --mark --output marked.png

# Adjust threshold
imageguard analyze image.png --threshold 0.7

# Verbose output
imageguard analyze image.png -v
```

### 7.3 Python SDK

```python
from imageguard import ImageGuard

# Initialize
guard = ImageGuard(
    modules=['all'],  # or specific modules
    threshold=0.5,
    weights={
        'text_extraction': 2.0,
        'hidden_text': 1.5,
        'frequency_analysis': 1.0,
        'steganography': 1.0,
        'structural': 1.2
    }
)

# Analyze image
result = guard.analyze('image.png')
print(f"Risk Score: {result.risk_score}")
print(f"Classification: {result.classification}")

# Check specific module
if result.text_extraction.score > 0.5:
    print(f"Suspicious text: {result.text_extraction.extracted_text}")

# Batch processing
results = guard.analyze_batch(['img1.png', 'img2.png', 'img3.png'])

# Get marked image
marked = guard.analyze('image.png', return_marked=True)
marked.save_marked_image('output.png')
```

---

## 8. Configuration

### 8.1 Configuration File (config.yaml)

```yaml
# ImageGuard Configuration

general:
  log_level: INFO
  max_image_size_mb: 50
  timeout_seconds: 30
  temp_directory: /tmp/imageguard

preprocessing:
  target_resolution: 1920  # Max dimension
  normalize_format: RGB
  extract_metadata: true

modules:
  text_extraction:
    enabled: true
    weight: 2.0
    ocr_engine: tesseract
    languages: ['eng', 'ro'] # in the future: 'fra', 'deu', 'spa', 'ro', 
    confidence_threshold: 0.6
    pattern_database: /etc/imageguard/patterns.yaml
    
  hidden_text:
    enabled: true
    weight: 1.5
    contrast_thresholds: [50, 100, 150, 200, 250]
    analyze_corners: true
    analyze_borders: true
    
  frequency_analysis:
    enabled: true
    weight: 1.0
    fft_enabled: true
    dct_enabled: true
    wavelet_enabled: true
    baseline_model: /models/frequency_baseline.pkl
    
  steganography:
    enabled: true
    weight: 1.0
    lsb_analysis: true
    chi_square_test: true
    rs_analysis: true
    spa_analysis: false  # Computationally expensive
    
  structural:
    enabled: true
    weight: 1.2
    detect_qr: true
    detect_barcodes: true
    detect_screenshots: true
    analyze_decoded_content: true

scoring:
  aggregation: weighted_average  # or 'max', 'sum'
  thresholds:
    safe: 0.3
    suspicious: 0.6
    dangerous: 0.8
  calibration_data: /models/calibration.pkl

api:
  host: 0.0.0.0
  port: 8080
  workers: 4
  max_batch_size: 100
  rate_limit: 1000  # requests per minute
  cors_origins: ['*']

output:
  include_extracted_text: true
  include_marked_image: false
  max_text_length: 10000
  audit_logging: true
  audit_log_path: /var/log/imageguard/audit.log
```

### 8.2 Pattern Database (patterns.yaml)

```yaml
# Injection Pattern Database

patterns:
  - id: ignore_instructions
    category: direct_instruction
    severity: 0.9
    regex: '(?i)(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above|your)\s+(instructions?|prompts?|rules?)'
    description: "Direct instruction override attempt"
    
  - id: role_manipulation
    category: identity
    severity: 0.85
    regex: '(?i)(you\s+are\s+now|pretend\s+(to\s+be|you\s+are)|act\s+as|your\s+new\s+role)'
    description: "Attempt to change AI identity"
    
  - id: system_prompt_reference
    category: context_manipulation
    severity: 0.8
    regex: '(?i)(system\s+prompt|end\s+of\s+(system|instructions)|<\|system\|>|\[INST\])'
    description: "Reference to system prompt structure"
    
  - id: jailbreak_keywords
    category: jailbreak
    severity: 0.95
    keywords:
      - 'DAN'
      - 'developer mode'
      - 'jailbreak'
      - 'no restrictions'
      - 'bypass'
      - 'unlock'
    description: "Common jailbreak terminology"
    
  - id: encoded_base64
    category: obfuscation
    severity: 0.7
    regex: '(?:[A-Za-z0-9+/]{4}){10,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?'
    min_length: 40
    description: "Potential Base64 encoded content"

keyword_lists:
  high_severity:
    - 'ignore previous'
    - 'ignore all'
    - 'disregard instructions'
    - 'you are now'
    - 'new instructions'
    
  medium_severity:
    - 'pretend'
    - 'roleplay'
    - 'simulation'
    - 'hypothetically'
    
  low_severity:
    - 'as if'
    - 'imagine'
    - 'suppose'
```

---

## 9. Testing Strategy

### 9.1 Test Categories

#### Unit Tests
- Individual function testing
- Pattern matching accuracy
- Score calculation correctness
- Edge case handling

#### Integration Tests
- Module pipeline testing
- API endpoint testing
- Configuration loading
- Error handling

#### Performance Tests
- Latency benchmarks
- Throughput testing
- Memory usage profiling
- Concurrent request handling

#### Accuracy Tests
- Precision/recall measurement
- False positive rate tracking
- Detection threshold tuning
- Cross-validation with test datasets

### 9.2 Test Datasets

#### Benign Dataset
- Natural photographs
- Documents and screenshots (non-malicious)
- Memes and social media images
- Product images

#### Malicious Dataset
- Known injection samples
- Generated variations of injection patterns
- Steganographic images with payloads
- Adversarial examples

#### Edge Cases
- Very large images
- Corrupted/partial images
- Unusual aspect ratios
- Animated GIFs
- Images with minimal content

### 9.3 Evaluation Metrics

```
Precision = TP / (TP + FP)
Recall = TP / (TP + FN)
F1 Score = 2 × (Precision × Recall) / (Precision + Recall)

False Positive Rate = FP / (FP + TN)
False Negative Rate = FN / (FN + TP)

AUC-ROC = Area under ROC curve
```

**Target Metrics**:
- Precision: >90%
- Recall: >95%
- F1 Score: >92%
- False Positive Rate: <5%

---

## 10. Deployment Architecture

### 10.1 Docker Deployment

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libzbar0 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . /app
WORKDIR /app

# Run
EXPOSE 8080
CMD ["uvicorn", "imageguard.api:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 10.2 Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: imageguard
spec:
  replicas: 3
  selector:
    matchLabels:
      app: imageguard
  template:
    metadata:
      labels:
        app: imageguard
    spec:
      containers:
      - name: imageguard
        image: imageguard:latest
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: imageguard-service
spec:
  selector:
    app: imageguard
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
```

### 10.3 Integration Patterns

**Inline Processing** (Recommended for real-time applications)
```
User Request → API Gateway → ImageGuard → LLM → Response
                               ↓
                        (Block if dangerous)
```

**Async Processing** (For batch/non-blocking)
```
User Request → Queue → ImageGuard Worker → Result Store
                                ↓
                    LLM retrieves safe images only
```

**Sidecar Pattern** (Kubernetes)
```
Pod:
  ├── Main Container (LLM Service)
  └── Sidecar Container (ImageGuard)
       └── Intercepts image inputs
```

---

## 11. Security Considerations

### 11.1 Input Validation
- File type verification (magic bytes, not just extension)
- Maximum file size enforcement
- Image dimension limits
- Timeout for processing

### 11.2 Output Sanitization
- Limit extracted text in responses
- Sanitize any reflected content
- Avoid exposing internal patterns

### 11.3 Rate Limiting
- Per-IP rate limits
- Per-API-key quotas
- Burst protection

### 11.4 Audit Logging
- Log all analysis requests
- Include timestamps, source IPs, results
- Retain for compliance requirements

### 11.5 Secrets Management
- API keys in environment variables
- No hardcoded credentials
- Secure configuration storage

---

## 12. Future Enhancements

### 12.1 Short-term (3-6 months)
- Additional language support for OCR
- GPU acceleration for frequency analysis
- WebSocket API for streaming analysis
- Prometheus metrics integration

### 12.2 Medium-term (6-12 months)
- Video frame analysis
- Audio spectrogram injection detection
- Multi-modal content correlation
- Federated pattern database updates

### 12.3 Long-term (12+ months)
- Adversarial robustness testing framework
- Automated pattern discovery from flagged images
- Integration with threat intelligence feeds
- On-device deployment for edge computing

---

## 13. Dependencies

### 13.1 Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Python | 3.10+ | Runtime |
| OpenCV | 4.8+ | Image processing |
| Pillow | 10.0+ | Image handling |
| NumPy | 1.24+ | Numerical operations |
| pytesseract | 0.3+ | OCR interface |
| pyzbar | 0.1.9+ | Barcode detection |
| PyWavelets | 1.4+ | Wavelet analysis |
| FastAPI | 0.100+ | API framework |
| uvicorn | 0.23+ | ASGI server |

### 13.2 System Dependencies

| Package | Purpose |
|---------|---------|
| Tesseract OCR | Text extraction |
| libzbar | Barcode/QR reading |
| libgl1 | OpenCV rendering |

---

## 14. Glossary

| Term | Definition |
|------|------------|
| **Prompt Injection** | Attack where malicious instructions are embedded in user input to manipulate LLM behavior |
| **Steganography** | Technique of hiding data within other media (images, audio, etc.) |
| **LSB** | Least Significant Bit - common steganography target |
| **OCR** | Optical Character Recognition - extracting text from images |
| **FFT** | Fast Fourier Transform - frequency domain analysis |
| **DCT** | Discrete Cosine Transform - used in JPEG compression |
| **CLAHE** | Contrast Limited Adaptive Histogram Equalization |
| **PSM** | Page Segmentation Mode - Tesseract configuration |
| **Adversarial Perturbation** | Small image modifications designed to fool AI systems |

---

## 15. References

1. OWASP - LLM Top 10: Prompt Injection
2. "Steganography: Techniques, Methods, and Tools" - Academic Survey
3. Tesseract OCR Documentation
4. OpenCV Image Processing Tutorials
5. "Frequency Domain Analysis for Image Forensics" - IEEE Paper
6. NIST Guidelines on AI Security

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 17 December 2025 | Raul & Mark & Claude | Initial draft |

---

*End of Document*
