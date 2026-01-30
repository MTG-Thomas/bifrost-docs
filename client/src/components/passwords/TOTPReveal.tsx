import { useState, useCallback } from "react";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import api from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { TOTPDisplay } from "@/components/ui/totp-display";
import { toast } from "sonner";
import { useTimedReveal } from "@/hooks/useTimedReveal";

interface TOTPRevealProps {
  orgId: string;
  passwordId: string;
}

interface PasswordRevealResponse {
  password: string;
  totp_secret: string | null;
}

export function TOTPReveal({ orgId, passwordId }: TOTPRevealProps) {
  // Store secret in local state only - no React Query caching for secrets
  const [totpSecret, setTotpSecret] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Clear secret from state when hiding
  const handleClearSecret = useCallback(() => {
    setTotpSecret(null);
  }, []);

  const { revealed, reveal, hide } = useTimedReveal({
    onHide: handleClearSecret,
  });

  // Always fetch fresh - no caching
  const fetchSecret = async (): Promise<string | null> => {
    setIsLoading(true);
    try {
      const response = await api.get<PasswordRevealResponse>(
        `/api/organizations/${orgId}/passwords/${passwordId}/reveal`
      );
      const secret = response.data.totp_secret;
      setTotpSecret(secret);
      return secret;
    } catch {
      toast.error("Failed to reveal TOTP");
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleReveal = async () => {
    if (revealed) {
      hide();
    } else {
      await fetchSecret();
      reveal();
    }
  };

  return (
    <div className="space-y-2">
      {revealed && totpSecret ? (
        <div className="flex items-center gap-2">
          <div className="flex-1">
            <TOTPDisplay secret={totpSecret} />
          </div>
          <Button
            variant="outline"
            size="icon"
            onClick={handleToggleReveal}
          >
            <EyeOff className="h-4 w-4" />
          </Button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <div className="flex-1 font-mono text-sm bg-muted px-3 py-2 rounded-md">
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <span className="tracking-widest">******</span>
            )}
          </div>
          <Button
            variant="outline"
            size="icon"
            onClick={handleToggleReveal}
            disabled={isLoading}
          >
            <Eye className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
