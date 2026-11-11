import { SEVERITIES } from "./api";

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

const MIN_TITLE_LENGTH = 3;
const MAX_TITLE_LENGTH = 120;
const MAX_PROJECT_NAME_LENGTH = 100;
const MAX_DESCRIPTION_LENGTH = 1000;
const MAX_VERSION_LENGTH = 50;
const MAX_REQ_CODE_LENGTH = 20;
const MAX_REQ_TITLE_LENGTH = 200;

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

export function hasFormErrors(errors: Record<string, string | undefined>): boolean {
  return Object.values(errors).some((msg) => Boolean(msg));
}
