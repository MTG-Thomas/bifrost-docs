import { toast as sonnerToast } from "sonner";

type ToastOptions = {
  title?: string;
  description?: string;
  variant?: "default" | "destructive";
};

export function useToast() {
  return {
    toast({ title, description, variant = "default" }: ToastOptions) {
      const message = title ?? description ?? "";
      const options = description && title ? { description } : undefined;

      if (variant === "destructive") {
        sonnerToast.error(message, options);
        return;
      }

      sonnerToast.success(message, options);
    },
  };
}
