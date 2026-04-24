# Skill: evaluate_roles

This skill enables the agent to perform strategic, high-rigor evaluation of job roles in-context.

## Instructions

### 1. Identify Target Roles
Locate roles in `applications/review.yaml` with the status `pending_scout_evaluation`.

### 2. Strategic Assessment Logic
For each role, perform the following analysis against the master `configs/profile.yaml` and `configs/evaluation.yaml`:

#### A) Archetype Detection
Classify the role as:
- **FDE**: Field Design / Delivery Engineer (Fast delivery, client-facing).
- **SA**: Solutions Architect (Systems design, integrations).
- **LLMOps/Agentic**: Specialization in LLM pipelines, evals, or agentic systems.
- **Enterprise Security**: Traditional large-scale security engineering.
- **Transformation**: Change management or security-first migrations.

#### B) Strategic Mapping
- **Proof Points**: Identify specific experiences in the user's profile that directly satisfy JD requirements.
- **Gaps**: IdentifyJD requirements NOT covered by the profile.
- **Tone Hook**: Suggest a 2-sentence "reason for interest" that maps a JD need to a profile strength.

#### C) Scoring
Apply the weights from `evaluation.yaml`:
- **Tech Stack**: 40% (Python, IaC, Security prioritize).
- **Role Fit**: 30% (Seniority check).
- **Logistics**: 20% (Remote/CH match).
- **Mission**: 10% (Alignment with AI/Security domains).

### 3. Update Status
- **Auto-Reject (< 5.0)**: Move to `applications/archived.yaml`. Ensure a mandatory `rejection_reason` is provided.
- **Manual Review (5.0 - 8.5)**: Keep in `review.yaml` but update status to `reviewed`.
- **Auto-Match (> 8.5)**: Move to `applications/in_progress.yaml` (Hot list).
