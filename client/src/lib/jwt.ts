/**
 * JWT Utilities
 *
 * Utilities for decoding and validating JWT tokens on the frontend.
 */

/**
 * JWT payload structure
 */
export interface JwtPayload {
  exp: number; // Expiration time (Unix timestamp)
  sub: string; // Subject (user ID)
  type?: string; // Token type ("access" or "refresh")
  [key: string]: unknown;
}

/**
 * Decode a JWT token and return its payload.
 *
 * @param token - The JWT token to decode
 * @returns The decoded payload, or null if invalid
 */
export function decodeJwt(token: string): JwtPayload | null {
  try {
    // JWT format: header.payload.signature
    const base64Url = token.split('.')[1];
    if (!base64Url) {
      return null;
    }

    // Convert base64url to base64
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');

    // Decode base64
    const json = atob(base64);

    return JSON.parse(json) as JwtPayload;
  } catch {
    return null;
  }
}

/**
 * Check if a JWT token is expired or will expire soon.
 *
 * @param token - The JWT token to check
 * @param bufferSeconds - Buffer time in seconds (default: 300 = 5 minutes)
 * @returns True if token is expired or will expire within the buffer time
 */
export function isTokenExpired(token: string, bufferSeconds: number = 300): boolean {
  const payload = decodeJwt(token);
  if (!payload?.exp) {
    return true; // Invalid token, consider it expired
  }

  const currentTime = Math.floor(Date.now() / 1000);
  return payload.exp - bufferSeconds < currentTime;
}

/**
 * Get the expiration date of a JWT token.
 *
 * @param token - The JWT token
 * @returns The expiration date as a Date object, or null if invalid
 */
export function getTokenExpiresAt(token: string): Date | null {
  const payload = decodeJwt(token);
  if (!payload?.exp) {
    return null;
  }

  return new Date(payload.exp * 1000);
}

/**
 * Get the number of seconds until a token expires.
 *
 * @param token - The JWT token
 * @returns Seconds until expiry (negative if expired), or null if invalid
 */
export function getTimeUntilExpiry(token: string): number | null {
  const payload = decodeJwt(token);
  if (!payload?.exp) {
    return null;
  }

  const currentTime = Math.floor(Date.now() / 1000);
  return payload.exp - currentTime;
}
