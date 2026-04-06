import { Link } from "react-router-dom";
import { Star, Building2, Lock, FileText, MapPin, Box } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useFavorites, useRemoveFavorite } from "@/hooks/useFavorites";
import { cn } from "@/lib/utils";

// =============================================================================
// Types
// =============================================================================

interface FavoritesListProps {
  maxItems?: number;
  className?: string;
  showHeader?: boolean;
}

// =============================================================================
// Entity Type Helpers
// =============================================================================

const entityTypeIcons: Record<string, React.ReactNode> = {
  password: <Lock className="h-4 w-4" />,
  configuration: <Box className="h-4 w-4" />,
  document: <FileText className="h-4 w-4" />,
  location: <MapPin className="h-4 w-4" />,
  custom_asset: <Box className="h-4 w-4" />,
  organization: <Building2 className="h-4 w-4" />,
};

const entityTypePaths: Record<string, string> = {
  password: "passwords",
  configuration: "configurations",
  document: "documents",
  location: "locations",
  custom_asset: "custom-assets",
  organization: "",
};

function getEntityIcon(entityType: string): React.ReactNode {
  return entityTypeIcons[entityType] || <Box className="h-4 w-4" />;
}

function getEntityPath(entityType: string): string {
  return entityTypePaths[entityType] || "";
}

// =============================================================================
// Component
// =============================================================================

export function FavoritesList({
  maxItems = 10,
  className,
  showHeader = true,
}: FavoritesListProps) {
  const { data: favoritesData, isLoading, error } = useFavorites(maxItems);
  const removeFavorite = useRemoveFavorite();

  if (isLoading) {
    return (
      <Card className={cn("w-full", className)}>
        {showHeader && (
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Star className="h-4 w-4 text-yellow-500" />
              Favorites
            </CardTitle>
          </CardHeader>
        )}
        <CardContent>
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className="h-8 bg-muted rounded animate-pulse"
              />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={cn("w-full", className)}>
        {showHeader && (
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Favorites</CardTitle>
          </CardHeader>
        )}
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Failed to load favorites
          </p>
        </CardContent>
      </Card>
    );
  }

  const favorites = favoritesData?.items || [];
  const total = favoritesData?.total || 0;

  if (favorites.length === 0) {
    return (
      <Card className={cn("w-full", className)}>
        {showHeader && (
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Star className="h-4 w-4 text-yellow-500" />
              Favorites
            </CardTitle>
          </CardHeader>
        )}
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No favorites yet. Star items to add them here.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn("w-full", className)}>
      {showHeader && (
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Star className="h-4 w-4 text-yellow-500 fill-current" />
            Favorites
            {total > 0 && (
              <span className="text-xs text-muted-foreground">({total})</span>
            )}
          </CardTitle>
        </CardHeader>
      )}
      <CardContent className="pt-0">
        <ScrollArea className="h-[200px]">
          <div className="space-y-1">
            {favorites.map((favorite) => {
              const path = getEntityPath(favorite.entity_type);
              const to = `/organizations/${favorite.organization_id}${
                path ? `/${path}` : ""
              }/${favorite.entity_id}`;

              return (
                <div
                  key={favorite.id}
                  className="group flex items-center gap-2 p-2 rounded-md hover:bg-muted transition-colors"
                >
                  <Link
                    to={to}
                    className="flex items-center gap-2 flex-1 min-w-0"
                  >
                    <span className="text-muted-foreground">
                      {getEntityIcon(favorite.entity_type)}
                    </span>
                    <span className="text-sm truncate">
                      {favorite.custom_label ||
                        `${favorite.entity_type} - ${favorite.entity_id.slice(
                          0,
                          8
                        )}`}
                    </span>
                  </Link>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={() => removeFavorite.mutate(favorite.id)}
                    disabled={removeFavorite.isPending}
                  >
                    <Star className="h-3 w-3 fill-current text-yellow-500" />
                    <span className="sr-only">Remove from favorites</span>
                  </Button>
                </div>
              );
            })}
          </div>
        </ScrollArea>
        {total > maxItems && (
          <div className="mt-2 pt-2 border-t">
            <p className="text-xs text-muted-foreground text-center">
              +{total - maxItems} more
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
