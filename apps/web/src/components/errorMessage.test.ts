import { describe, expect, it } from "vitest";
import { errorMessageKey } from "./errorMessage";

const known = new Set(["errors.upload.too_large", "errors.generic"]);
const hasKey = (key: string) => known.has(key);

describe("errorMessageKey", () => {
  it("maps a known server code to its message", () => {
    expect(errorMessageKey("upload.too_large", hasKey)).toBe("errors.upload.too_large");
  });

  it("falls back for unknown or malformed codes", () => {
    expect(errorMessageKey("upload.something_new", hasKey)).toBe("errors.generic");
    expect(errorMessageKey("../../secret", hasKey)).toBe("errors.generic");
    expect(errorMessageKey("", hasKey)).toBe("errors.generic");
  });
});
