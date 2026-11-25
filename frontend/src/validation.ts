import { SEVERITIES, TEST_PRIORITIES } from "./api";

export type DefectFormValues = {
  title: string;
  severity: string;
  testCase: string;
};

export type DefectFormErrors = Partial<Record<keyof DefectFormValues, string>>;

export type LoginFormValues = {
  username: string;
  password: string;
};

export type LoginFormErrors = Partial<Record<keyof LoginFormValues, string>>;

export type ProjectFormValues = {
  name: string;
  description: string;
};

export type ProjectFormErrors = Partial<Record<keyof ProjectFormValues, string>>;

export type ReleaseFormValues = {
  projectId: string;
  version: string;
};

export type ReleaseFormErrors = Partial<Record<keyof ReleaseFormValues, string>>;

export type RequirementFormValues = {
  id: string;
  projectId: string;
  title: string;
  description: string;
};

export type RequirementFormErrors = Partial<Record<keyof RequirementFormValues, string>>;

export type TestCaseFormValues = {
  stableKey: string;
  title: string;
  priority: string;
  stepsText: string;
  expectedResult: string;
  requirements: string[];
};

export type TestCaseFormErrors = Partial<Record<keyof TestCaseFormValues, string>>;

export type TestSuiteFormValues = {
  projectId: string;
  name: string;
  description: string;
};

export type TestSuiteFormErrors = Partial<Record<keyof TestSuiteFormValues, string>>;

export type TestRunFormValues = {
  name: string;
  projectId: string;
  testCaseIds: string[];
};

export type TestRunFormErrors = Partial<Record<keyof TestRunFormValues, string>>;

export type ExitCriteriaFormValues = {
  minPassRate: string;
  maxOpenCritical: string;
  minReqCoverage: string;
};

export type ExitCriteriaFormErrors = Partial<Record<keyof ExitCriteriaFormValues, string>>;

export type TestPlanFormValues = {
  projectId: string;
  version: string;
  title: string;
  scope: string;
  approach: string;
  passFailCriteria: string;
  environment: string;
  scheduleRisks: string;
};

export type TestPlanFormErrors = Partial<Record<keyof TestPlanFormValues, string>>;

const MIN_TITLE_LENGTH = 3;
const MAX_TITLE_LENGTH = 120;
const MAX_PROJECT_NAME_LENGTH = 100;
const MAX_DESCRIPTION_LENGTH = 1000;
const MAX_VERSION_LENGTH = 50;
const MAX_REQ_CODE_LENGTH = 20;
const MAX_REQ_TITLE_LENGTH = 200;
const MAX_TEST_KEY_LENGTH = 20;
const MAX_TEST_TITLE_LENGTH = 200;
const MAX_SUITE_NAME_LENGTH = 100;
const MAX_PLAN_TITLE_LENGTH = 200;
const MAX_PLAN_SECTION_LENGTH = 2000;

export function validateDefectForm(
  values: DefectFormValues,
  validTestCaseIds?: string[],
): DefectFormErrors {
  const errors: DefectFormErrors = {};
  const trimmedTitle = values.title.trim();

  if (!trimmedTitle) {
    errors.title = "Başlık boş olamaz.";
  } else if (trimmedTitle.length < MIN_TITLE_LENGTH) {
    errors.title = `Başlık en az ${MIN_TITLE_LENGTH} karakter olmalıdır.`;
  } else if (trimmedTitle.length > MAX_TITLE_LENGTH) {
    errors.title = `Başlık en fazla ${MAX_TITLE_LENGTH} karakter olabilir.`;
  }

  if (!SEVERITIES.includes(values.severity as (typeof SEVERITIES)[number])) {
    errors.severity = "Geçerli bir önem derecesi seçin.";
  }

  if (
    values.testCase &&
    validTestCaseIds &&
    validTestCaseIds.length > 0 &&
    !validTestCaseIds.includes(values.testCase)
  ) {
    errors.testCase = "Geçerli bir test vakası seçin.";
  }

  return errors;
}

export function validateLoginForm(values: LoginFormValues): LoginFormErrors {
  const errors: LoginFormErrors = {};
  if (!values.username.trim()) {
    errors.username = "Kullanıcı adı boş olamaz.";
  }
  if (!values.password) {
    errors.password = "Parola boş olamaz.";
  } else if (new TextEncoder().encode(values.password).length > 72) {
    errors.password = "Parola en fazla 72 bayt olabilir.";
  }
  return errors;
}

export function validateProjectForm(values: ProjectFormValues): ProjectFormErrors {
  const errors: ProjectFormErrors = {};
  const name = values.name.trim();
  const description = values.description.trim();

  if (!name) {
    errors.name = "Proje adı boş olamaz.";
  } else if (name.length > MAX_PROJECT_NAME_LENGTH) {
    errors.name = `Proje adı en fazla ${MAX_PROJECT_NAME_LENGTH} karakter olabilir.`;
  }

  if (description.length > MAX_DESCRIPTION_LENGTH) {
    errors.description = `Açıklama en fazla ${MAX_DESCRIPTION_LENGTH} karakter olabilir.`;
  }

  return errors;
}

export function validateReleaseForm(values: ReleaseFormValues): ReleaseFormErrors {
  const errors: ReleaseFormErrors = {};
  const projectId = Number(values.projectId);
  const version = values.version.trim();

  if (!values.projectId || !Number.isInteger(projectId) || projectId <= 0) {
    errors.projectId = "Geçerli bir proje seçin.";
  }

  if (!version) {
    errors.version = "Sürüm bilgisi boş olamaz.";
  } else if (version.length > MAX_VERSION_LENGTH) {
    errors.version = `Sürüm en fazla ${MAX_VERSION_LENGTH} karakter olabilir.`;
  }

  return errors;
}

export function validateRequirementForm(
  values: RequirementFormValues,
  requireId = true,
): RequirementFormErrors {
  const errors: RequirementFormErrors = {};
  const id = values.id.trim();
  const projectId = Number(values.projectId);
  const title = values.title.trim();
  const description = values.description.trim();

  if (requireId) {
    if (!id) {
      errors.id = "Gereksinim kodu boş olamaz (örn. R9).";
    } else if (id.length > MAX_REQ_CODE_LENGTH) {
      errors.id = `Gereksinim kodu en fazla ${MAX_REQ_CODE_LENGTH} karakter olabilir.`;
    }
  }

  if (!values.projectId || !Number.isInteger(projectId) || projectId <= 0) {
    errors.projectId = "Geçerli bir proje seçin.";
  }

  if (!title) {
    errors.title = "Gereksinim başlığı boş olamaz.";
  } else if (title.length > MAX_REQ_TITLE_LENGTH) {
    errors.title = `Başlık en fazla ${MAX_REQ_TITLE_LENGTH} karakter olabilir.`;
  }

  if (description.length > MAX_DESCRIPTION_LENGTH) {
    errors.description = `Açıklama en fazla ${MAX_DESCRIPTION_LENGTH} karakter olabilir.`;
  }

  return errors;
}

export function validateTestCaseForm(values: TestCaseFormValues): TestCaseFormErrors {
  const errors: TestCaseFormErrors = {};
  const stableKey = values.stableKey.trim();
  const title = values.title.trim();
  const steps = values.stepsText
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  const expectedResult = values.expectedResult.trim();

  if (!stableKey) {
    errors.stableKey = "Kararlı test anahtarı boş olamaz (örn. TC-007).";
  } else if (stableKey.length > MAX_TEST_KEY_LENGTH) {
    errors.stableKey = `Anahtar en fazla ${MAX_TEST_KEY_LENGTH} karakter olabilir.`;
  } else if (!/^[A-Za-z0-9_-]+$/.test(stableKey)) {
    errors.stableKey = "Anahtar yalnızca harf, rakam, '-' ve '_' içerebilir.";
  }

  if (!title) {
    errors.title = "Test vakası başlığı boş olamaz.";
  } else if (title.length < MIN_TITLE_LENGTH) {
    errors.title = `Başlık en az ${MIN_TITLE_LENGTH} karakter olmalıdır.`;
  } else if (title.length > MAX_TEST_TITLE_LENGTH) {
    errors.title = `Başlık en fazla ${MAX_TEST_TITLE_LENGTH} karakter olabilir.`;
  }

  if (!TEST_PRIORITIES.includes(values.priority as (typeof TEST_PRIORITIES)[number])) {
    errors.priority = "Geçerli bir öncelik seçin.";
  }

  if (steps.length === 0) {
    errors.stepsText = "En az bir test adımı girin (satır başına bir adım).";
  }

  if (!expectedResult) {
    errors.expectedResult = "Beklenen sonuç alanı boş olamaz.";
  } else if (expectedResult.length > MAX_DESCRIPTION_LENGTH) {
    errors.expectedResult = `Beklenen sonuç en fazla ${MAX_DESCRIPTION_LENGTH} karakter olabilir.`;
  }

  if (values.requirements.length === 0) {
    errors.requirements = "FR-REQ-01 gereği en az bir gereksinim seçilmelidir.";
  }

  return errors;
}

export function validateTestSuiteForm(values: TestSuiteFormValues): TestSuiteFormErrors {
  const errors: TestSuiteFormErrors = {};
  const projectId = Number(values.projectId);
  const name = values.name.trim();
  const description = values.description.trim();

  if (!values.projectId || !Number.isInteger(projectId) || projectId <= 0) {
    errors.projectId = "Geçerli bir proje seçin.";
  }

  if (!name) {
    errors.name = "Suite adı boş olamaz.";
  } else if (name.length < 2) {
    errors.name = "Suite adı en az 2 karakter olmalıdır.";
  } else if (name.length > MAX_SUITE_NAME_LENGTH) {
    errors.name = `Suite adı en fazla ${MAX_SUITE_NAME_LENGTH} karakter olabilir.`;
  }

  if (description.length > MAX_DESCRIPTION_LENGTH) {
    errors.description = `Açıklama en fazla ${MAX_DESCRIPTION_LENGTH} karakter olabilir.`;
  }

  return errors;
}

export function validateTestRunForm(values: TestRunFormValues): TestRunFormErrors {
  const errors: TestRunFormErrors = {};
  const projectId = Number(values.projectId);
  const name = values.name.trim();

  if (!name) {
    errors.name = "Koşum adı boş olamaz.";
  } else if (name.length < MIN_TITLE_LENGTH) {
    errors.name = `Koşum adı en az ${MIN_TITLE_LENGTH} karakter olmalıdır.`;
  } else if (name.length > MAX_TITLE_LENGTH) {
    errors.name = `Koşum adı en fazla ${MAX_TITLE_LENGTH} karakter olabilir.`;
  }

  if (!values.projectId || !Number.isInteger(projectId) || projectId <= 0) {
    errors.projectId = "Geçerli bir proje seçin.";
  }

  if (values.testCaseIds.length === 0) {
    errors.testCaseIds = "Koşuma en az bir test vakası eklenmelidir.";
  }

  return errors;
}

export function validateExitCriteriaForm(values: ExitCriteriaFormValues): ExitCriteriaFormErrors {
  const errors: ExitCriteriaFormErrors = {};
  const passRate = Number(values.minPassRate);
  const openCritical = Number(values.maxOpenCritical);
  const reqCoverage = Number(values.minReqCoverage);

  if (Number.isNaN(passRate) || passRate < 0 || passRate > 100) {
    errors.minPassRate = "Başarı oranı 0 ile 100 arasında olmalıdır.";
  }
  if (!Number.isInteger(openCritical) || openCritical < 0) {
    errors.maxOpenCritical = "Açık Critical limiti 0 veya daha büyük tam sayı olmalıdır.";
  }
  if (Number.isNaN(reqCoverage) || reqCoverage < 0 || reqCoverage > 100) {
    errors.minReqCoverage = "Gereksinim kapsamı 0 ile 100 arasında olmalıdır.";
  }

  return errors;
}

export function validateWaiverReason(reason: string): string | undefined {
  const trimmed = reason.trim();
  if (!trimmed) return "Muafiyet gerekçesi boş olamaz.";
  if (trimmed.length < 5) return "Muafiyet gerekçesi en az 5 karakter olmalıdır.";
  if (trimmed.length > MAX_DESCRIPTION_LENGTH) {
    return `Muafiyet gerekçesi en fazla ${MAX_DESCRIPTION_LENGTH} karakter olabilir.`;
  }
  return undefined;
}

export function validateTestPlanForm(values: TestPlanFormValues): TestPlanFormErrors {
  const errors: TestPlanFormErrors = {};
  const projectId = Number(values.projectId);
  const version = values.version.trim();
  const title = values.title.trim();

  if (!values.projectId || !Number.isInteger(projectId) || projectId <= 0) {
    errors.projectId = "Geçerli bir proje seçin.";
  }

  if (!version) {
    errors.version = "Sürüm numarası boş olamaz (örn. v1.0).";
  } else if (version.length > MAX_VERSION_LENGTH) {
    errors.version = `Sürüm numarası en fazla ${MAX_VERSION_LENGTH} karakter olabilir.`;
  }

  if (!title) {
    errors.title = "Test Plan başlığı boş olamaz.";
  } else if (title.length < MIN_TITLE_LENGTH) {
    errors.title = `Başlık en az ${MIN_TITLE_LENGTH} karakter olmalıdır.`;
  } else if (title.length > MAX_PLAN_TITLE_LENGTH) {
    errors.title = `Başlık en fazla ${MAX_PLAN_TITLE_LENGTH} karakter olabilir.`;
  }

  if (values.scope.trim().length > MAX_PLAN_SECTION_LENGTH) {
    errors.scope = `Kapsam alanı en fazla ${MAX_PLAN_SECTION_LENGTH} karakter olabilir.`;
  }
  if (values.approach.trim().length > MAX_PLAN_SECTION_LENGTH) {
    errors.approach = `Yaklaşım alanı en fazla ${MAX_PLAN_SECTION_LENGTH} karakter olabilir.`;
  }
  if (values.passFailCriteria.trim().length > MAX_PLAN_SECTION_LENGTH) {
    errors.passFailCriteria = `Kabul/Red kriterleri en fazla ${MAX_PLAN_SECTION_LENGTH} karakter olabilir.`;
  }
  if (values.environment.trim().length > MAX_PLAN_SECTION_LENGTH) {
    errors.environment = `Test ortamı alanı en fazla ${MAX_PLAN_SECTION_LENGTH} karakter olabilir.`;
  }
  if (values.scheduleRisks.trim().length > MAX_PLAN_SECTION_LENGTH) {
    errors.scheduleRisks = `Takvim ve riskler alanı en fazla ${MAX_PLAN_SECTION_LENGTH} karakter olabilir.`;
  }

  return errors;
}

export function hasFormErrors(errors: Record<string, string | undefined>): boolean {
  return Object.values(errors).some((msg) => Boolean(msg));
}
