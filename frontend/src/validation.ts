import { SEVERITIES, TEST_PRIORITIES } from "./api";
import { translate } from "./i18nTranslate";

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
    errors.title = translate("Başlık boş olamaz.");
  } else if (trimmedTitle.length < MIN_TITLE_LENGTH) {
    errors.title = translate("Başlık en az {min} karakter olmalıdır.", {
      min: MIN_TITLE_LENGTH,
    });
  } else if (trimmedTitle.length > MAX_TITLE_LENGTH) {
    errors.title = translate("Başlık en fazla {max} karakter olabilir.", {
      max: MAX_TITLE_LENGTH,
    });
  }

  if (!SEVERITIES.includes(values.severity as (typeof SEVERITIES)[number])) {
    errors.severity = translate("Geçerli bir önem derecesi seçin.");
  }

  if (
    values.testCase &&
    validTestCaseIds &&
    validTestCaseIds.length > 0 &&
    !validTestCaseIds.includes(values.testCase)
  ) {
    errors.testCase = translate("Geçerli bir test vakası seçin.");
  }

  return errors;
}

export function validateLoginForm(values: LoginFormValues): LoginFormErrors {
  const errors: LoginFormErrors = {};
  if (!values.username.trim()) {
    errors.username = translate("Kullanıcı adı boş olamaz.");
  }
  if (!values.password) {
    errors.password = translate("Parola boş olamaz.");
  } else if (new TextEncoder().encode(values.password).length > 72) {
    errors.password = translate("Parola en fazla 72 bayt olabilir.");
  }
  return errors;
}

export function validateProjectForm(values: ProjectFormValues): ProjectFormErrors {
  const errors: ProjectFormErrors = {};
  const name = values.name.trim();
  const description = values.description.trim();

  if (!name) {
    errors.name = translate("Proje adı boş olamaz.");
  } else if (name.length > MAX_PROJECT_NAME_LENGTH) {
    errors.name = translate("Proje adı en fazla {max} karakter olabilir.", {
      max: MAX_PROJECT_NAME_LENGTH,
    });
  }

  if (description.length > MAX_DESCRIPTION_LENGTH) {
    errors.description = translate("Açıklama en fazla {max} karakter olabilir.", {
      max: MAX_DESCRIPTION_LENGTH,
    });
  }

  return errors;
}

export function validateReleaseForm(values: ReleaseFormValues): ReleaseFormErrors {
  const errors: ReleaseFormErrors = {};
  const projectId = Number(values.projectId);
  const version = values.version.trim();

  if (!values.projectId || !Number.isInteger(projectId) || projectId <= 0) {
    errors.projectId = translate("Geçerli bir proje seçin.");
  }

  if (!version) {
    errors.version = translate("Sürüm bilgisi boş olamaz.");
  } else if (version.length > MAX_VERSION_LENGTH) {
    errors.version = translate("Sürüm en fazla {max} karakter olabilir.", {
      max: MAX_VERSION_LENGTH,
    });
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
      errors.id = translate("Gereksinim kodu boş olamaz (örn. R9).");
    } else if (id.length > MAX_REQ_CODE_LENGTH) {
      errors.id = translate("Gereksinim kodu en fazla {max} karakter olabilir.", {
        max: MAX_REQ_CODE_LENGTH,
      });
    }
  }

  if (!values.projectId || !Number.isInteger(projectId) || projectId <= 0) {
    errors.projectId = translate("Geçerli bir proje seçin.");
  }

  if (!title) {
    errors.title = translate("Gereksinim başlığı boş olamaz.");
  } else if (title.length > MAX_REQ_TITLE_LENGTH) {
    errors.title = translate("Başlık en fazla {max} karakter olabilir.", {
      max: MAX_REQ_TITLE_LENGTH,
    });
  }

  if (description.length > MAX_DESCRIPTION_LENGTH) {
    errors.description = translate("Açıklama en fazla {max} karakter olabilir.", {
      max: MAX_DESCRIPTION_LENGTH,
    });
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
    errors.stableKey = translate("Kararlı test anahtarı boş olamaz (örn. TC-007).");
  } else if (stableKey.length > MAX_TEST_KEY_LENGTH) {
    errors.stableKey = translate("Anahtar en fazla {max} karakter olabilir.", {
      max: MAX_TEST_KEY_LENGTH,
    });
  } else if (!/^[A-Za-z0-9_-]+$/.test(stableKey)) {
    errors.stableKey = translate("Anahtar yalnızca harf, rakam, '-' ve '_' içerebilir.");
  }

  if (!title) {
    errors.title = translate("Test vakası başlığı boş olamaz.");
  } else if (title.length < MIN_TITLE_LENGTH) {
    errors.title = translate("Başlık en az {min} karakter olmalıdır.", {
      min: MIN_TITLE_LENGTH,
    });
  } else if (title.length > MAX_TEST_TITLE_LENGTH) {
    errors.title = translate("Başlık en fazla {max} karakter olabilir.", {
      max: MAX_TEST_TITLE_LENGTH,
    });
  }

  if (!TEST_PRIORITIES.includes(values.priority as (typeof TEST_PRIORITIES)[number])) {
    errors.priority = translate("Geçerli bir öncelik seçin.");
  }

  if (steps.length === 0) {
    errors.stepsText = translate("En az bir test adımı girin (satır başına bir adım).");
  }

  if (!expectedResult) {
    errors.expectedResult = translate("Beklenen sonuç alanı boş olamaz.");
  } else if (expectedResult.length > MAX_DESCRIPTION_LENGTH) {
    errors.expectedResult = translate("Beklenen sonuç en fazla {max} karakter olabilir.", {
      max: MAX_DESCRIPTION_LENGTH,
    });
  }

  if (values.requirements.length === 0) {
    errors.requirements = translate("FR-REQ-01 gereği en az bir gereksinim seçilmelidir.");
  }

  return errors;
}

export function validateTestSuiteForm(values: TestSuiteFormValues): TestSuiteFormErrors {
  const errors: TestSuiteFormErrors = {};
  const projectId = Number(values.projectId);
  const name = values.name.trim();
  const description = values.description.trim();

  if (!values.projectId || !Number.isInteger(projectId) || projectId <= 0) {
    errors.projectId = translate("Geçerli bir proje seçin.");
  }

  if (!name) {
    errors.name = translate("Suite adı boş olamaz.");
  } else if (name.length < 2) {
    errors.name = translate("Suite adı en az 2 karakter olmalıdır.");
  } else if (name.length > MAX_SUITE_NAME_LENGTH) {
    errors.name = translate("Suite adı en fazla {max} karakter olabilir.", {
      max: MAX_SUITE_NAME_LENGTH,
    });
  }

  if (description.length > MAX_DESCRIPTION_LENGTH) {
    errors.description = translate("Açıklama en fazla {max} karakter olabilir.", {
      max: MAX_DESCRIPTION_LENGTH,
    });
  }

  return errors;
}

export function validateTestRunForm(values: TestRunFormValues): TestRunFormErrors {
  const errors: TestRunFormErrors = {};
  const projectId = Number(values.projectId);
  const name = values.name.trim();

  if (!name) {
    errors.name = translate("Koşum adı boş olamaz.");
  } else if (name.length < MIN_TITLE_LENGTH) {
    errors.name = translate("Koşum adı en az {min} karakter olmalıdır.", {
      min: MIN_TITLE_LENGTH,
    });
  } else if (name.length > MAX_TITLE_LENGTH) {
    errors.name = translate("Koşum adı en fazla {max} karakter olabilir.", {
      max: MAX_TITLE_LENGTH,
    });
  }

  if (!values.projectId || !Number.isInteger(projectId) || projectId <= 0) {
    errors.projectId = translate("Geçerli bir proje seçin.");
  }

  if (values.testCaseIds.length === 0) {
    errors.testCaseIds = translate("Koşuma en az bir test vakası eklenmelidir.");
  }

  return errors;
}

export function validateExitCriteriaForm(values: ExitCriteriaFormValues): ExitCriteriaFormErrors {
  const errors: ExitCriteriaFormErrors = {};
  const passRate = Number(values.minPassRate);
  const openCritical = Number(values.maxOpenCritical);
  const reqCoverage = Number(values.minReqCoverage);

  if (Number.isNaN(passRate) || passRate < 0 || passRate > 100) {
    errors.minPassRate = translate("Başarı oranı 0 ile 100 arasında olmalıdır.");
  }
  if (!Number.isInteger(openCritical) || openCritical < 0) {
    errors.maxOpenCritical = translate(
      "Açık Critical limiti 0 veya daha büyük tam sayı olmalıdır.",
    );
  }
  if (Number.isNaN(reqCoverage) || reqCoverage < 0 || reqCoverage > 100) {
    errors.minReqCoverage = translate("Gereksinim kapsamı 0 ile 100 arasında olmalıdır.");
  }

  return errors;
}

export function validateWaiverReason(reason: string): string | undefined {
  const trimmed = reason.trim();
  if (!trimmed) return translate("Muafiyet gerekçesi boş olamaz.");
  if (trimmed.length < 5) return translate("Muafiyet gerekçesi en az 5 karakter olmalıdır.");
  if (trimmed.length > MAX_DESCRIPTION_LENGTH) {
    return translate("Muafiyet gerekçesi en fazla {max} karakter olabilir.", {
      max: MAX_DESCRIPTION_LENGTH,
    });
  }
  return undefined;
}

export function validateTestPlanForm(values: TestPlanFormValues): TestPlanFormErrors {
  const errors: TestPlanFormErrors = {};
  const projectId = Number(values.projectId);
  const version = values.version.trim();
  const title = values.title.trim();

  if (!values.projectId || !Number.isInteger(projectId) || projectId <= 0) {
    errors.projectId = translate("Geçerli bir proje seçin.");
  }

  if (!version) {
    errors.version = translate("Sürüm numarası boş olamaz (örn. v1.0).");
  } else if (version.length > MAX_VERSION_LENGTH) {
    errors.version = translate("Sürüm numarası en fazla {max} karakter olabilir.", {
      max: MAX_VERSION_LENGTH,
    });
  }

  if (!title) {
    errors.title = translate("Test Plan başlığı boş olamaz.");
  } else if (title.length < MIN_TITLE_LENGTH) {
    errors.title = translate("Başlık en az {min} karakter olmalıdır.", {
      min: MIN_TITLE_LENGTH,
    });
  } else if (title.length > MAX_PLAN_TITLE_LENGTH) {
    errors.title = translate("Başlık en fazla {max} karakter olabilir.", {
      max: MAX_PLAN_TITLE_LENGTH,
    });
  }

  if (values.scope.trim().length > MAX_PLAN_SECTION_LENGTH) {
    errors.scope = translate("Kapsam alanı en fazla {max} karakter olabilir.", {
      max: MAX_PLAN_SECTION_LENGTH,
    });
  }
  if (values.approach.trim().length > MAX_PLAN_SECTION_LENGTH) {
    errors.approach = translate("Yaklaşım alanı en fazla {max} karakter olabilir.", {
      max: MAX_PLAN_SECTION_LENGTH,
    });
  }
  if (values.passFailCriteria.trim().length > MAX_PLAN_SECTION_LENGTH) {
    errors.passFailCriteria = translate(
      "Kabul/Red kriterleri en fazla {max} karakter olabilir.",
      { max: MAX_PLAN_SECTION_LENGTH },
    );
  }
  if (values.environment.trim().length > MAX_PLAN_SECTION_LENGTH) {
    errors.environment = translate("Test ortamı alanı en fazla {max} karakter olabilir.", {
      max: MAX_PLAN_SECTION_LENGTH,
    });
  }
  if (values.scheduleRisks.trim().length > MAX_PLAN_SECTION_LENGTH) {
    errors.scheduleRisks = translate("Takvim ve riskler alanı en fazla {max} karakter olabilir.", {
      max: MAX_PLAN_SECTION_LENGTH,
    });
  }

  return errors;
}

export function hasFormErrors(errors: Record<string, string | undefined>): boolean {
  return Object.values(errors).some((msg) => Boolean(msg));
}
