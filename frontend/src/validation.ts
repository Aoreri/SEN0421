import { SEVERITIES } from "./api";

export type DefectFormValues = {
  title: string;
  severity: string;
  testCase: string;
};

export type DefectFormErrors = Partial<Record<keyof DefectFormValues, string>>;

const MIN_TITLE_LENGTH = 3;
const MAX_TITLE_LENGTH = 120;

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

export function hasFormErrors(errors: DefectFormErrors): boolean {
  return Object.values(errors).some((msg) => Boolean(msg));
}
