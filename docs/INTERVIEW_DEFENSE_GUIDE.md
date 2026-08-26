# Placement Control Tower: Technical Defense & Interview Preparation Guide

This guide equips you to defend and explain every engineering and mathematical decision made in this system during senior technical interviews, viva voce, and system architecture defenses.

---

## Key Questions & Engineering Answers

### 1. "Why Google OR-Tools CP-SAT instead of Genetic Algorithms or Greedy Heuristics?"

**Defense:**
- **Exact Feasibility Guarantee**: Placement scheduling has strict safety requirements (a student cannot physically be in two rooms at once; a panel cannot interview two candidates simultaneously). Greedy heuristics frequently encounter dead-ends (forcing backtracks) or generate invalid schedules. Genetic algorithms cannot guarantee 100% hard-constraint compliance in large discrete domains.
- **Constraint Propagation & Dual Bounds**: CP-SAT (Constraint Programming over SAT solver) uses modern Boolean Satisfiability (CDCL) techniques combined with linear integer domain propagation to prune infeasible branches exponentially faster than pure MILP or metaheuristics.
- **Deterministic Reproducibility**: Given fixed random seeds and constraint parameters, CP-SAT generates mathematically optimal and verifiable solutions within a specified time ceiling ($T_{limit} = 20\text{s}$).

---

### 2. "How does the Minimal-Disruption Replanning Engine prevent schedule churn?"

**Defense:**
- Traditional systems regenerate the schedule from scratch upon a disruption, causing $80-100\%$ of interviews to move. This creates massive panic on campus.
- Our replanning engine incorporates a **Stability Scalarization Objective**:
  $$\sum_{i \in \text{Interviews}} W_{stab} \cdot \mathbf{1}_{\{ \text{Assignment}(i) = \text{OriginalAssignment}(i) \}}$$
- In **Balanced Optimization**, $W_{stab} = 500$, which heavily penalizes unnecessary slot changes, ensuring $>90\%$ stability while accommodating recruiter delays or panel failures.

---

### 3. "How do you eliminate AI Hallucinations in the Placement Control Tower?"

**Defense:**
- The LLM is **never** tasked with calculating schedule assignments or checking constraint feasibility.
- All constraint checks and mathematical proofs are computed by the deterministic OR-Tools engine and SQLAlchemy queries.
- When a user asks a question in the AI Copilot:
  1. The backend gathers real quantitative facts (utilization %, conflict counts, room allocations).
  2. The facts are serialized into an immutable JSON context.
  3. The prompt constrains the LLM (Groq Llama-3.3) to synthesize explanations based strictly on the grounded payload.

---

### 4. "How is data consistency maintained across disruptions?"

**Defense:**
- The system uses an **Append-Only Versioning Schema**:
  - `ScheduleVersion` records are immutable once published.
  - When replanning is accepted, a new version is created (`v1.0 -> v2.0`).
  - A corresponding `ReplanningRun` and multiple `ScheduleChange` entries are generated to provide a complete audit diff.
  - A deterministic validator independently runs on the resulting version before publication to guarantee zero constraint violations.
