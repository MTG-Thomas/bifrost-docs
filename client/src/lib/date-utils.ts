/**
 * Date formatting utilities.
 *
 * Centralized date formatting to ensure consistent display across the app.
 * All dates are stored in UTC and converted to local timezone for display.
 */

/**
 * Format a date/time string for display.
 *
 * @param dateString - ISO date string or Date object
 * @returns Formatted date/time string in local timezone
 */
export function formatDateTime(dateString: string | Date | null | undefined): string {
  if (!dateString) return "";

  const date = typeof dateString === "string" ? new Date(dateString) : dateString;

  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Format a date string for display (date only, no time).
 *
 * @param dateString - ISO date string or Date object
 * @returns Formatted date string in local timezone
 */
export function formatDate(dateString: string | Date | null | undefined): string {
  if (!dateString) return "";

  const date = typeof dateString === "string" ? new Date(dateString) : dateString;

  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/**
 * Format a relative time string (e.g., "2 hours ago").
 *
 * @param dateString - ISO date string or Date object
 * @returns Relative time string
 */
export function formatRelativeTime(dateString: string | Date | null | undefined): string {
  if (!dateString) return "";

  const date = typeof dateString === "string" ? new Date(dateString) : dateString;
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) {
    return "just now";
  } else if (diffMinutes < 60) {
    return `${diffMinutes} minute${diffMinutes === 1 ? "" : "s"} ago`;
  } else if (diffHours < 24) {
    return `${diffHours} hour${diffHours === 1 ? "" : "s"} ago`;
  } else if (diffDays < 7) {
    return `${diffDays} day${diffDays === 1 ? "" : "s"} ago`;
  } else {
    return formatDate(date);
  }
}
