import { useState, useEffect, useCallback, useRef } from "react";

const DEFAULT_TIMEOUT_MS = 15000; // 15 seconds

interface UseTimedRevealOptions {
  /** Timeout in milliseconds before auto-hiding. Default: 15000 (15s) */
  timeout?: number;
  /** Called when the reveal times out - use to clear sensitive data from memory */
  onHide?: () => void;
}

interface UseTimedRevealReturn {
  /** Whether the content is currently revealed */
  revealed: boolean;
  /** Show the content and start the auto-hide timer */
  reveal: () => void;
  /** Hide the content and clear the timer */
  hide: () => void;
  /** Toggle revealed state */
  toggle: () => void;
}

/**
 * Hook for managing timed reveal of sensitive content.
 *
 * Automatically hides content after a timeout and calls onHide to clear
 * sensitive data from memory (DOM, React state, query cache, etc.)
 *
 * @example
 * ```tsx
 * const { revealed, reveal, hide, toggle } = useTimedReveal({
 *   timeout: 15000,
 *   onHide: () => queryClient.removeQueries({ queryKey: ['secret'] })
 * });
 * ```
 */
export function useTimedReveal(options: UseTimedRevealOptions = {}): UseTimedRevealReturn {
  const { timeout = DEFAULT_TIMEOUT_MS, onHide } = options;
  const [revealed, setRevealed] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onHideRef = useRef(onHide);

  // Keep onHide ref updated to avoid stale closures
  useEffect(() => {
    onHideRef.current = onHide;
  }, [onHide]);

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const hide = useCallback(() => {
    clearTimer();
    setRevealed(false);
    onHideRef.current?.();
  }, [clearTimer]);

  const reveal = useCallback(() => {
    // Clear any existing timer
    clearTimer();

    setRevealed(true);

    // Start new timer
    timerRef.current = setTimeout(() => {
      setRevealed(false);
      onHideRef.current?.();
    }, timeout);
  }, [clearTimer, timeout]);

  const toggle = useCallback(() => {
    if (revealed) {
      hide();
    } else {
      reveal();
    }
  }, [revealed, hide, reveal]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearTimer();
    };
  }, [clearTimer]);

  return { revealed, reveal, hide, toggle };
}
