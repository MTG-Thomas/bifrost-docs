import { Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  useIsFavorite,
  useAddFavorite,
  useUnfavoriteEntity,
} from "@/hooks/useFavorites";
import { cn } from "@/lib/utils";

// =============================================================================
// Types
// =============================================================================

interface FavoriteButtonProps {
  organizationId: string;
  entityType: string;
  entityId: string;
  entityName?: string;
  size?: "sm" | "default" | "lg";
  variant?: "ghost" | "outline" | "secondary";
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function FavoriteButton({
  organizationId,
  entityType,
  entityId,
  entityName,
  size = "default",
  variant = "ghost",
  className,
}: FavoriteButtonProps) {
  const { data: favoriteCheck, isLoading: isChecking } = useIsFavorite(
    organizationId,
    entityType,
    entityId
  );
  const addFavorite = useAddFavorite();
  const unfavorite = useUnfavoriteEntity();

  const isFavorite = favoriteCheck?.is_favorite ?? false;
  const isPending = addFavorite.isPending || unfavorite.isPending;

  const handleToggle = () => {
    if (isFavorite) {
      unfavorite.mutate({
        organization_id: organizationId,
        entity_type: entityType,
        entity_id: entityId,
      });
    } else {
      addFavorite.mutate({
        organization_id: organizationId,
        entity_type: entityType,
        entity_id: entityId,
        custom_label: entityName || null,
      });
    }
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={variant}
            size={size}
            onClick={handleToggle}
            disabled={isChecking || isPending}
            className={cn(
              "transition-all duration-200",
              isFavorite && "text-yellow-500 hover:text-yellow-600",
              className
            )}
          >
            <Star
              className={cn(
                "h-4 w-4 transition-all duration-200",
                size === "sm" && "h-3 w-3",
                size === "lg" && "h-5 w-5",
                isFavorite && "fill-current"
              )}
            />
            <span className="sr-only">
              {isFavorite ? "Remove from favorites" : "Add to favorites"}
            </span>
          </Button>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          <p>{isFavorite ? "Remove from favorites" : "Add to favorites"}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
