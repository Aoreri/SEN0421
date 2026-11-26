import assert from "node:assert/strict";
import test from "node:test";
import { translate } from "../src/i18nTranslate.ts";

test("Turkish is the default language", () => {
  assert.equal(translate("Kapat"), "Kapat");
  assert.equal(translate("Test Vakaları"), "Test Vakaları");
});

test("English is returned after switching, with placeholders filled", () => {
  assert.equal(translate("Kapat", undefined, "en"), "Close");
  assert.equal(
    translate("Başlık en az {min} karakter olmalıdır.", { min: 3 }, "en"),
    "Title must be at least 3 characters.",
  );
});

test("an unknown key falls back to the Turkish text", () => {
  assert.equal(translate("Bilinmeyen bir anahtar", undefined, "en"), "Bilinmeyen bir anahtar");
});
