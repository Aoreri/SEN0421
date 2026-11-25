# SDS-06 — Standards Alignment and Compliance Checklist

**Plan item:** PLN-38  
**Prepared:** 22 November 2026  
**Assessment type:** Project-level, tailored evidence review; not a certification.

## 1. Checklist

| Reference | Project application | Evidence / work product | Status | Remaining action |
|---|---|---|---|---|
| ISO/IEC/IEEE 12207 — Software life-cycle processes | Project planning, implementation, verification, configuration management, release and work-product control. | Bi-weekly plans, task-specific branches/PRs, SRS, SDD, RTM, CI, migration history, release workflow PR #40. | **Partially evidenced.** | Complete integrated review, final release evidence, final report and retrospective. |
| ISO/IEC/IEEE 29148:2018 — Requirements engineering | Requirements definition, quality/traceability attributes, interface and acceptance requirements. | SRS v1.0, FR/NFR catalogue, RTM v2. | **Project-tailored evidence present.** | Confirm original R1–R8 statements and approve baseline with the course owner. |
| IEEE 1016 — Software Design Descriptions | Context, composition, deployment, information, interface, behavior and design decisions. | SDD v1.0. | **Project-tailored evidence present.** | Reconcile after any remaining API/schema PRs merge. |
| ISO/IEC/IEEE 29119-2:2021 — Test processes | Test planning, design, execution, monitoring, defect reporting, completion and evidence. | Test Plan, workflow Test Case Specification, automated API/integration tests, metric checks, PR #37/#38 report work. | **Partially evidenced.** | Finish integration and record final test execution/summary evidence. |
| ISO/IEC/IEEE 29119-3:2021 — Test documentation | Test Plan, Test Case Specification, Test Log, Test Incident Report, Test Summary Report information items. | Test Plan and snapshots integrated; workflow test specification integrated; Test Incident/Log PR #37 and Summary Report PR #38. | **Partially evidenced.** | Merge/report review, inspect generated document content, PDF output and snapshots. |
| IEEE 829-2008 — legacy course-facing test artefact terminology | Course uses legacy document names such as Test Plan, Test Incident Report, Test Log and Test Summary Report. | Test Plan template/API; PLN-39 incident/log templates; PLN-30 summary report template. | **Tailored terminology mapping only.** | Do not claim current formal IEEE 829 conformance; map purposes to 29119-2/-3. |
| IEEE 1012-2024 — System, Software, and Hardware V&V | Verification of requirements, design, implementation, tests, interfaces and intended use. | `ieee-1012-verification-results.md`, CI checks, API/PostgreSQL tests, review records. | **Partially evidenced.** | Complete integrated V&V, performance/install measurements, PDF inspection, and demo recording. |
| ISO/IEC 25010:2023 — Product quality model | Evaluate functional suitability, performance efficiency, compatibility, interaction capability, reliability, security, maintainability, flexibility and safety. | `iso-25010-quality-evaluation.md`; SRS NFRs; tests and CI. | **Assessment matrix prepared; several measures pending.** | Complete p95, clean-machine, security and PDF-runtime evidence. |

## 2. Tailoring and conformance statement

The project is an academic software product and applies selected processes and information items appropriate to its scope. The mapping above identifies the intended purpose of each work product and the evidence available at the assessment date. It does not assert that every normative clause, process outcome, or information item in each licensed standard has been fully implemented or independently assessed.

IEEE 829-2008 is treated as legacy course-facing artefact terminology. The project maps test process and documentation purposes to ISO/IEC/IEEE 29119-2:2021 and 29119-3:2021 rather than claiming that IEEE 829 remains the current testing framework.

## 3. Edition notes and official references

1. ISO/IEC/IEEE 29148:2018 remains the published edition listed by ISO as current after review in 2024; a third-edition draft is under development. [ISO catalogue](https://www.iso.org/standard/72089.html).
2. ISO/IEC 25010:2023 is Edition 2 and defines a product quality model with nine characteristics. The 2011 edition is listed as withdrawn. [ISO catalogue](https://www.iso.org/standard/78176.html).
3. IEEE 1012-2024 is listed as active by IEEE SA and supersedes IEEE 1012-2016. [IEEE SA record](https://standards.ieee.org/ieee/1012/7324/).
4. ISO/IEC/IEEE 29119-2:2021 and 29119-3:2021 are the project's testing process and documentation references.
5. ISO/IEC/IEEE 12207 is the project's life-cycle process reference; the exact course baseline edition should be confirmed with the instructor.
