# Contributing to OcuGuard AI

First off, thank you for taking the time to contribute! OcuGuard AI is a community-driven project dedicated to closing the structural gaps in mass-market consumer smart eyewear. We are building background automation framework layers that empower individuals during high-stakes visual adaptation and ergonomic recovery windows.

Whether you are an engineer, an accessibility advocate, a designer, or a researcher, your insights are incredibly valuable to this mission.

---

## 🌟 Areas We Need Help With

We are actively seeking contributions for our upcoming hackathon showcases and open-source milestones in the following areas:

### 1. New Spatial Sub-Agent Plugins
Help us expand the capability matrix! By leveraging our core plugin system, you can design non-diagnostic evaluation modules for diverse visual adaptation tracking profiles (e.g., automated stability trackers, gaze tracking filters, or low-illumination helpers).
* Look at `plugin_interface.py` to see the abstract baseline.
* Review `ergonomic_schedule.py` and `ambient_luminance.py` for reference implementations.

### 2. Frontend & Simulation Enhancements (`index.html`)
Our HTML simulation dashboard is how we demo the system without requiring physical smart glasses. We welcome enhancements such as:
* Migrating visualizers to WebGL / Three.js for true 3D telemetry tracking.
* Implementing advanced spatialized audio panning velocities using the Web Audio API.
* Expanding responsive layout constraints for mobile testing contexts.

### 3. Data Pipelines & Performance
* Optimizing Pydantic schema validation speeds for ultra-low latency streams.
* Writing edge-side proxy deployment guides for processing telemetry locally inside iOS/Android companion applications.

---

## ⚖️ Strict Terminology & Architectural Rules

Because this software is built to operate completely outside of regulated clinical medical definitions, **all contributions must strictly protect the project from medical liability boundaries.**

* 🚫 **NO CLINICAL OR DIAGNOSTIC WORDS:** Any Pull Request or Issue containing diagnostic language, medical triage assertions, clinical prescriptions, or explicit medical checking text (e.g., diagnosing, clinical triage, hospital rules) will be automatically closed.
* ✅ **USE MIDDLEWARE LOGIC TERMINOLOGY:** Use objective, sensor-centric, data-mapping, and vision-ergonomic language. Frame capabilities as "assisted orientation utilities," "OCR optimization matrices," or "acoustic layout enhancements."
* ⚡ **ZERO-DEPENDENCY EDGE FALLBACKS:** If your plugin utilizes cloud-based LLM logic, you *must* implement a robust, local, deterministic mathematical fallback route to handle network dropouts gracefully.

---

## 🚀 Step-by-Step Contribution Pipeline

1. **Fork the Repository:** Create your own feature branch from the main branch.
2. **Setup Local Environment:** Ensure your environment parameters match `.env.example` and that all `pytest` suites pass cleanly offline.
3. **Commit with Intention:** Use clear, descriptive commit messages outlining your technical enhancement.
4. **Run Local Tests:** Ensure your refactoring passes our automated checks:
   ```bash
   pytest test_triage_agent.py -q