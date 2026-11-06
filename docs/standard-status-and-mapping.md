# PLN-01: Standards Status and Mapping

**Review date:** 7 November 2026  
**Repository:** Aoreri/SEN0421

## 1. Purpose

This document reviews the status of IEEE 829 and the relevant ISO/IEC/IEEE standards for software testing and software life-cycle processes. It provides an indicative mapping to support the project's documentation approach.

This is a purpose-level mapping, not a claim of full compliance or a one-to-one replacement of every legacy document.

## 2. Standards status

| Standard | Edition / status | Relevance |
|---|---|---|
| IEEE 829-2008 | Superseded | Legacy software test documentation standard |
| ISO/IEC/IEEE 29119-1 | 2022 | General software testing concepts |
| ISO/IEC/IEEE 29119-2 | 2021 | Test processes |
| ISO/IEC/IEEE 29119-3 | 2021 | Test documentation |
| ISO/IEC/IEEE 29119-4 | 2021 | Test design techniques |
| ISO/IEC/IEEE 29119-5 | 2024 | Keyword-driven testing |
| ISO/IEC/IEEE 12207 | 2026 | Software life-cycle processes |

IEEE 829-2008 has been superseded by the ISO/IEC/IEEE 29119 testing standards framework. The current editions listed above should be used when planning project documentation.

ISO/IEC/IEEE 12207:2026 is the current second edition of the software life-cycle processes standard. The 2017 edition has been withdrawn.

## 3. IEEE 829 and ISO/IEC/IEEE 29119 mapping

The following table provides an indicative relationship between legacy IEEE 829 artefacts and relevant areas of the 29119 series.

| IEEE 829 artefact | Relevant 29119 area | Mapping rationale |
|---|---|---|
| Test Plan | 29119-2 and 29119-3 | Test planning processes and documentation |
| Test Design Specification | 29119-2, 29119-3 and 29119-4 | Test design and selection of techniques |
| Test Case Specification | 29119-2, 29119-3 and 29119-4 | Test case design and documentation |
| Test Procedure Specification | 29119-2 and 29119-3 | Test implementation and procedure documentation |
| Test Log | 29119-2 and 29119-3 | Test execution and recording |
| Test Incident Report | 29119-2 and 29119-3 | Recording and handling of test incidents |
| Test Summary Report | 29119-2 and 29119-3 | Test completion and reporting |
| Test Item Transmittal Report | Project configuration and handover records | Transfer and identification of test items |

This mapping is based on purpose and subject area. It does not mean that every IEEE 829 document has an identically named replacement in ISO/IEC/IEEE 29119.

Exact information-item names, required content and conformance requirements must be checked against the full applicable editions before claiming formal conformance.

## 4. Recommended use of the 29119 series

- **Part 1 (2022):** Use as the common vocabulary and conceptual introduction to software testing.
- **Part 2 (2021):** Use as the main reference for organizing and managing testing processes.
- **Part 3 (2021):** Use as the reference for test documentation and documentation templates.
- **Part 4 (2021):** Select suitable test design techniques for project test cases.
- **Part 5 (2024):** Consider only if the project adopts keyword-driven test specifications or automation.

Parts 2, 3 and 4 provide normative requirements for users claiming conformance. The selected practices should be tailored to the project's scope and documented.

## 5. Relationship with ISO/IEC/IEEE 12207

ISO/IEC/IEEE 12207:2026 provides a framework for software life-cycle processes, including development, operation, maintenance and retirement.

It provides the broader life-cycle context for project planning and engineering activities. It does not prescribe a specific development methodology or require every process to be applied identically to every project.

For this project, 12207 should be treated as the high-level life-cycle reference, while 29119 should be used for the testing-specific process and documentation approach.

## 6. Project-level recommendation

The project should use the following documentation baseline:

1. Use ISO/IEC/IEEE 12207:2026 as the high-level software life-cycle reference.
2. Use ISO/IEC/IEEE 29119-2:2021 to structure test processes.
3. Use ISO/IEC/IEEE 29119-3:2021 to guide test documentation.
4. Use ISO/IEC/IEEE 29119-4:2021 to select suitable test design techniques.
5. Apply ISO/IEC/IEEE 29119-5:2024 only if keyword-driven testing is adopted.

The project should tailor the selected practices to its size, risks, architecture and schedule. Any omitted or tailored practices should be documented with their rationale.

## 7. Open verification items

Before making a formal standards-conformance statement, the project team should:

- Review the full text of the selected standard editions.
- Verify exact required information items and their contents.
- Record which processes and artefacts are applicable.
- Document tailoring decisions and justifications.
- Ensure that the Test Plan and other project documents use consistent terminology.

This document establishes the standards baseline and mapping approach. It does not by itself establish that the project conforms to every requirement of the standards.

## 8. Official references

1. IEEE 829-2008: https://standards.ieee.org/ieee/829/3787/
2. ISO/IEC/IEEE 29119-1:2022: https://committee.iso.org/cms/live/live/en/sites/isoorg/contents/data/standard/08/12/81291.html
3. ISO/IEC/IEEE 29119-2:2021: https://www.iso.org/standard/79428.html
4. ISO/IEC/IEEE 29119-3:2021: https://www.iso.org/standard/79429.html
5. ISO/IEC/IEEE 29119-4:2021: https://www.iso.org/standard/79430.html
6. ISO/IEC/IEEE 29119-5:2024: https://www.iso.org/standard/87233.html
7. ISO/IEC/IEEE 12207:2026: https://www.iso.org/standard/90219.html
8. ISO/IEC/IEEE 12207:2017: https://www.iso.org/standard/63712.html