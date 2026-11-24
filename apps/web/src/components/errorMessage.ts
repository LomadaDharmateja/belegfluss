/**
 * Map an API error code (e.g. "upload.too_large") to a message key under "errors".
 * Unknown codes fall back to the generic message, so a new server code never shows a raw key.
 */
export function errorMessageKey(code: string, hasKey: (key: string) => boolean): string {
  const key = `errors.${code}`;
  return /^[a-z_]+(\.[a-z_]+)*$/.test(code) && hasKey(key) ? key : "errors.generic";
}
