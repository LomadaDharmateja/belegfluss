import { createFormatter } from "next-intl";
import { describe, expect, it } from "vitest";
import { TIME_ZONE } from "./locales";

// Regression (found in the M2b walkthrough): times were shown in the server's time zone (UTC in
// the container), so "approved at 03:34" in Germany showed as 2:34.
describe("time zone", () => {
  const format = createFormatter({ locale: "en", timeZone: TIME_ZONE });

  it("is set explicitly, not taken from the machine", () => {
    expect(TIME_ZONE).toBe("Europe/Berlin");
  });

  it("shows times in German time, winter and summer", () => {
    expect(format.dateTime(new Date("2026-11-25T02:34:00Z"), { timeStyle: "short" })).toBe(
      "3:34 AM",
    );
    expect(format.dateTime(new Date("2026-07-01T10:00:00Z"), { timeStyle: "short" })).toBe(
      "12:00 PM",
    );
  });
});
