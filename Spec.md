# OcuGuard AI — Engineering & Terminology Specification

**Version:** 2.0.0  
**Framework Classification:** Non-Diagnostic Assisted Orientation Middleware  
**Development Standard:** Strict Pydantic Runtime Type Validation  
**Project Origin:** Inspired by a patient-survivor’s journey through post-cataract vision recovery.

---

## 0. Project Genesis & Core Mission
This middleware architecture was designed following an engineering contributor's personal journey navigating strict post-operative visual positioning constraints. While development focuses entirely on non-clinical assistive utilities, the system's core orchestration rules (specifically the "Discomfort Pattern Cascade" and "Ergonomic Habit Multipliers") are engineered to bridge the accessibility gaps left unaddressed by mass-market hardware manufacturers.

**Key Technical Innovation:** A zero-trust, safety-first telemetry translator where external network or cloud anomalies never cause software runtime lockups—slipping instantly into local deterministic mathematical loops.

---

## 1. System Architecture

### 1.1 Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Core Language** | Python 3.10+ | Type hints, clean structured data manipulation |
| **API Framework** | Flask | Lightweight, well-tested REST ingestion gateway |
| **Orchestration** | LangChain + OpenAI (GPT-4) | Flexible abstract context parsing paths |
| **Validation Layer**| Pydantic | Strict, declarative runtime type verification |
| **Local Failsafe** | Local Keyword & Rule Matcher | Zero-dependency, low-latency execution backup |
| **Environment** | python-dotenv | Secure deployment credential management |

### 1.2 Data Flow & Mesh Architecture

* Wearable Client / Simulator Dashboard transfers parameters to REST API Gateway (/v1/stream/evaluate)
* Supervisor Agent validates credentials and applies PII Scrubbing
* Payload splits across Active Plugin Matrix (Eye Sentinel, Gaze Compass, Tabular Layout, Ergonomic Schedule, Ambient Luminance, Be My Eyes Proxy Node)
* Cloud LLM Optimization Engine acts as primary path; Local Zero-Dependency Rules Engine functions as the ultimate baseline fallback loop

---

## 2. Core Functional Requirements

#### **Post-Operative Positioning Guidance**
When an active telemetry frame contains the `post_op_recovery` flag or matching user intent, the EyeSentinelAgent processes orientation data via a time-series schedule:
- **Airway Clearance:** Automatically appends the "Triple Pillow Triangle" ergonomic configuration guidelines to help maintain clear breathing space while face-down.
- **Timestamp-Driven Rotation:** Extracts the current hour from the ISO 8601 UTC timestamp to cyclically vary recommended orientations across three positions over successive hour boundaries:

$$\text{Hour} \pmod 3 \implies 0: \text{Prone (Face-Down)}, \quad 1: \text{Left Side}, \quad 2: \text{Right Side}$$

#### **Stream Urgency Evaluation Framework (Non-Diagnostic)**
To isolate operations from diagnostic liability, user inputs and telemetry tracking arrays match against three severity rings:
The agent should be capable of providing "Survival Hacks" for the 24-hour prone (face-down) recovery period if the user is identified as a post-op patient:
- **Instructional logic:** If status == POST_OP_RECOVERY, suggest the "Triple Pillow Triangle" for airway clearance.
- **Positioning logic:** Rotate guidance each hour over a three-position cycle: prone, left side, right side.
- **Timing logic:** Apply the rotation based on the UTC timestamp hour to keep guidance consistent across deployments.

### 2.1 Triage Engine (Red Flag Logic)

The triage engine identifies critical indicators across three channels:

#### **Emergency Keywords (EMERGENCY Level)**
- **Visual Terms:** "black curtain," "shadow," "darkness," "cannot see," "half blinded"
- **Temporal:** "sudden," "sudden onset," "just happened"
- **Specific:** "flashing lights," "lightning flashes," "vision loss"
- **Severity:** "blacked out," "completely dark"

**Decision Rule:** If ANY emergency keyword + post-cataract history -> CRITICAL_ALERT (confidence >= 0.90)

#### **Urgent Keywords (URGENT Level)**
- **Floaters:** "floaters," "sudden floaters," "increase in floaters"
- **Vision Changes:** "blurry," "sudden blur," "light sensitivity"
- **Pain:** "eye pain," "severe pain," "sharp pain"

**Decision Rule:** If urgent keyword detected -> ELEVATED_ALERT (confidence >= 0.70)

#### **Routine Keywords (ROUTINE Level)**
- **Comfort:** "dryness," "dry eye," "itchiness," "itch," "watery," "redness," "discomfort"

**Decision Rule:** If routine keyword detected -> STANDARD_LOG (confidence >= 0.60)

### 2.2 Risk Factor Weighting System

Risk factors are applied multiplicatively to base confidence scores:

```python
# Formula: adjusted_confidence = min(1.0, base_confidence x factor_1 x factor_2 x ...)
RISK_FACTORS = {
    "cataract_surgery": 1.2,
    "retinal_disease": 1.3,
    "diabetic_retinopathy": 1.25,
    "previous_detachment": 1.4,
    "age_over_50": 1.1
}

"""

## 3. Exception Handling & Fallback Mechanisms

### 3.1 LLM Timeout & Outage Cascades

```
1. Initial Cloud Dispatches: Strict 2.0-second timeout constraints apply.

2. Retry Attempts: If a connection anomaly or timeout occurs, the system triggers exactly one retry (maximum 2 deployment attempts total).

3. Deterministic Fallback Interception: If the cloud resource remains exhausted, the system drops the external call entirely, bypassing runtime lockups to execute localized mathematical keyword matching loops within 100ms.

4. Conservative Safety Bias: If incoming text strings display high ambiguity and fail all local keyword arrays, the pipeline assigns an ELEVATED_ALERT urgency response by default to ensure optimal user positioning awareness.


### 3.2 Error Handling Strategy

| Error Type | Handling | User Impact |
|-----------|----------|------------|
| **Invalid Input** | Reject with 422 | Clear validation message |
| **LLM Timeout** | Fallback to local | Slower but still accurate |
| **LLM Error** | Conservative bias | Treat as URGENT if uncertain |
| **API Auth Failure** | Log + Return 401 | Reject unauthorized calls |
| **Rate Limit** | Queue or return 429 | Polite rejection with retry info |
| **Internal Error** | Return 500 + log | Generic error, no PII exposure |

### 3.3 PII Protection

**Strict Redaction Targets**: High-speed regex layers filter email strings, phone variations, and identification patterns from input fields.
**Stateless Metadata Architecture**: System memory excludes fields for patient identity or symptom profiling from persistent logs. Variables track only generic error summaries, timestamp structures, and abstract urgency tags.

---

## 4. API Specification (FINAL)

### 4.1 Single Triage Analysis

**Endpoint:** `POST /v1/stream/evaluate`

**Request:**
```json
{
  "user_id": "demo_anonymized_wearer_uuid",
  "input_string": "Visual block or clouding baseline noticed since five minutes ago",
  "multimodal_flags": ["shadow", "sudden"],
  "agent_mode": "EYE_SENTINEL",
  "pitch": -58.5,
  "client_id": "OCUGUARD_CLIENT",
  "user_token": "OCUGUARD_TOKEN",
  "history": {
    "cataract_surgery": true,
    "age_over_50": true
  }
}
```

**Response (EMERGENCY):**
```json
{
  "message": "Stream evaluation completed",
  "data": {
    "status": "CRITICAL_ALERT",
    "action_required": "System Notification: Ingested telemetry strings match your pre-configured alert profile for acute discomfort. Please consult your supervisor, a professional mobility coach, or your personal emergency contact baseline instructions.",
    "confidence_score": 1.0,
    "escalation_trigger": "Human Escalation Protocol",
    "disclaimer": "Abstract stream data serialization tool. This software only evaluates geometric sensor orientations and raw string structural patterns against user-defined parameters.",
    "reasoning": "Discomfort indicators matched with structural post-surgical history flags.",
    "timestamp": "2026-06-09T22:04:22.000Z",
    "compliance_gate": {
      "software_classification": "Assisted Orientation Aid (Non-Diagnostic Middleware)",
      "regulatory_disclaimer": "OcuGuard AI does not replace direct physician oversight or certified low-vision mobility coaching."
    }
  },
  "timestamp": "2026-06-09T22:04:22.105Z"
}
```

### 4.2 Batch Triage Analysis

**Endpoint:** `POST /v1/stream/evaluate/batch`

**Request:**
```json
{
  "requests": [
    {
      "user_id": "user_demo_1",
      "input_string": "clouding baseline noticed",
      "agent_mode": "EYE_SENTINEL",
      "client_id": "OCUGUARD_CLIENT",
      "user_token": "OCUGUARD_TOKEN"
    },
    {
      "user_id": "user_demo_2",
      "input_string": "dryness parameters",
      "agent_mode": "AMBIENT_LUMINANCE",
      "client_id": "OCUGUARD_CLIENT",
      "user_token": "OCUGUARD_TOKEN"
    }
  ]
}
```

**Array Scope Constraints**: Array payload accepts up to 10 unified request payloads per execution window. Max batch size is strictly enforced.

### 4.3 System Information

**Endpoint:** `GET /v1/triage/info`  
**Authorization:** None required  
**Response:** System documentation and emergency keywords

### 4.4 Health Check

**Endpoint:** `GET /health`  
**Use:** Load balancer health checks, monitoring  
**Response:** `{"status": "healthy"}`

---

## 5. Data Flow & "What If" Scenarios

### 5.1 Scenario: User is Driving

**Current:** Text input "can't see"  
**AI Response:** Detects driving context (if provided in multimodal_flags)  
**Action:** Prioritize "Pull over" in action_required  
**Implementation:** Add "driving_context" to multimodal_flags

### 5.2 Scenario: Ambiguous Input ("Eye feels weird")

**Current:** Non-specific symptom  
**AI Response:** No emergency keywords matched  
**Local Fallback:** No keywords match  
**Decision:** Return URGENT with conservative bias  
**Rationale:** Safety-first—better to escalate conservatively

### 5.3 Scenario: LLM is Down

**Current:** OpenAI API unavailable  
**Step 1:** Retry up to 2 times with exponential backoff  
**Step 2:** Fall back to LocalKeywordMatcher  
**Result:** Still returns accurate triage (e.g., EMERGENCY for black curtain)  
**Logging:** Warns about LLM unavailability but doesn't fail

### 5.4 Scenario: False Positive ("I'm just joking, my vision is fine")

**Current:** Analyzed as EMERGENCY  
**Response:** Includes disclaimer that AI is not perfect  
**Action:** Patient can dismiss or seek care  
**Logging:** False positive tracked but not used to retrain locally  
**Note:** Better to escalate conservatively than miss real emergency

### 5.5 Scenario: Incomplete Input ("I can't see well")

**Current:** Vague symptom description  
**AI Response:** LLM can ask clarifying questions  
**Fallback (No LLM):** Trigger recursive prompt in client app  
**Example Recursive Prompt:** "Is it a blur or a solid shadow? Does it cover half your vision?"

---

## 6. Development Standards

### 6.1 Code Quality Requirements

✅ **Type Hints:** ALL functions and methods  
✅ **Docstrings:** Google-style with Args, Returns, Raises  
✅ **Comments:** Explain "why", not "what"  
✅ **Testing:** 80%+ coverage minimum  
✅ **Error Handling:** Custom exceptions with meaningful messages  
✅ **Logging:** Info-level for key operations, no PII  

### 6.2 Safety Requirements

✅ **Emergency Response:** Impossible to bypass if "curtain" or "shadow" detected  
✅ **Conservative Bias:** When uncertain, escalate as URGENT  
✅ **PII Protection:** No user_id or symptom details in logs  
✅ **Fallback Guarantee:** System never completely fails (local matcher as ultimate fallback)  

### 6.3 Performance Requirements

⚡ **Response Time:** < 2 seconds for LLM analysis, < 100ms for fallback  
⚡ **Throughput:** 60 requests/minute per user (configurable)  
⚡ **Availability:** 99.9% uptime target (using fallback on LLM outage)  

---

## 7. Security & Privacy

### 7.1 Authentication

- **Optional API Key:** Set `API_KEY` env var to enforce authentication
- **Protected Endpoints:** `/v1/system/config`, `/v1/system/stats` require API key
- **Rate Limiting:** 60 requests/minute per user_id (configurable)

### 7.2 Data Protection

- **No Persistence:** Responses not stored by default
- **No Logging PII:** user_id and symptom details excluded from logs
- **Timeout Protection:** All external calls have configurable timeouts
- **Input Validation:** Pydantic schema enforces strict types

### 7.3 Compliance

- **HIPAA:** No Protected Health Information stored; designed for patient-initiated consultation
- **GDPR:** No personal data retained; each request is stateless
- **Disclaimer:** Explicitly states AI is not medical advice

---

## 8. Implementation Checklist ✅

- ✅ `triage_agent.py`: Core LLM agent with LangChain (Note: modularized as `eye_sentinel.py`)
- ✅ `app.py`: Flask REST API wrapper
- ✅ `.env.example`: Environment configuration template
- ✅ `test_triage_agent.py`: 29+ unit tests
- ✅ `README.md`: Comprehensive documentation
- ✅ `spec.md`: This specification (updated)
- ✅ MIT License headers in all files
- ✅ Comments and docstrings throughout
- ✅ Error handling for connectivity issues
- ✅ Fallback local keyword matcher

---

## 9. Deployment Instructions

### Development
```bash
cp .env.example .env
# Edit .env with your OpenAI API key
python app.py  # Runs on http://localhost:5000
```

### Production (Gunicorn)
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker
```bash
docker build -t eye-sentinel .
docker run -e OPENAI_API_KEY=$KEY -p 5000:5000 eye-sentinel
```

---

## 10. License & Attribution

**MIT License**
Copyright (c) 2026 The Eye-Sentinel Project (Lead Architect: Anonymous Cloud/AI Engineer)

**Attribution:**
This specification and the subsequent code were developed to bridge the gap between smart-wearable technology (Meta Glasses) and emergency ophthalmology. 

**Recognition:**
Special thanks to the medical professionals who treat retinal detachments and the patient-advocates who refuse to let the "silent thief" of sight win. This effort is dedicated to every patient currently lying face-down, fighting for their vision.