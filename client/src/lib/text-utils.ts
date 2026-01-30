/**
 * Strip HTML tags from a string and return plain text.
 * Uses the browser's DOM parser for safe HTML removal.
 */
export function stripHtml(html: string): string {
  if (!html) return "";
  const div = document.createElement("div");
  div.innerHTML = html;
  return div.textContent || "";
}

/**
 * Truncate text to a maximum length, adding ellipsis if truncated.
 */
export function truncateText(text: string, maxLength = 100): string {
  if (!text) return "";
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + "...";
}

/**
 * Strip HTML and truncate in one operation.
 * Useful for displaying rich text content in table cells.
 */
export function stripAndTruncate(html: string, maxLength = 100): string {
  return truncateText(stripHtml(html), maxLength);
}
