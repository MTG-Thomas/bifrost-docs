import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Link2, Plus, X, Loader2, LinkIcon, ChevronDown, ChevronRight, ExternalLink } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  useRelationships,
  useDeleteRelationship,
  groupRelationshipsByType,
  type RelatedEntity,
} from "@/hooks/useRelationships";
import {
  getEntityIcon,
  getEntityLabel,
  getEntityRoute,
  type EntityType,
} from "@/lib/entity-icons";
import { AddRelationshipDialog } from "./AddRelationshipDialog";
import { PasswordReveal } from "@/components/passwords/PasswordReveal";
import { toast } from "sonner";
import type { components } from "@/lib/v1";

type PasswordPublic = components["schemas"]["PasswordPublic"];

interface RelatedItemRowProps {
  rel: RelatedEntity;
  orgId: string;
  onNavigate: () => void;
  onRemove: (e: React.MouseEvent) => void;
  isDeleting: boolean;
}

function RelatedItemRow({ rel, orgId, onNavigate, onRemove, isDeleting }: RelatedItemRowProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const isPassword = rel.entity_type === "password";

  // Fetch password details when expanded
  const { data: passwordDetails } = useQuery({
    queryKey: ["password", orgId, rel.entity_id],
    queryFn: async () => {
      const response = await api.get<PasswordPublic>(
        `/api/organizations/${orgId}/passwords/${rel.entity_id}`
      );
      return response.data;
    },
    enabled: isPassword && isExpanded,
    staleTime: 30000,
  });

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isPassword) {
      setIsExpanded(!isExpanded);
    } else {
      onNavigate();
    }
  };

  return (
    <div className="border-b last:border-b-0">
      <div className="group flex items-center gap-2 py-1.5">
        {isPassword && (
          <Button
            variant="ghost"
            size="sm"
            className="h-5 w-5 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
            onClick={handleToggle}
          >
            {isExpanded ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
            <span className="sr-only">{isExpanded ? "Collapse" : "Expand"}</span>
          </Button>
        )}
        <span
          className="text-sm truncate flex-1 text-primary hover:underline cursor-pointer"
          onClick={handleToggle}
        >
          {rel.name}
        </span>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={(e) => {
              e.stopPropagation();
              onNavigate();
            }}
          >
            <ExternalLink className="h-3 w-3" />
            <span className="sr-only">Open</span>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={onRemove}
            disabled={isDeleting}
          >
            {isDeleting ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <X className="h-3 w-3" />
            )}
            <span className="sr-only">Remove relationship</span>
          </Button>
        </div>
      </div>

      {/* Expanded password preview */}
      {isPassword && isExpanded && passwordDetails && (
        <div className="pl-2 pr-0 pb-3 pt-1 space-y-2">
          {passwordDetails.username && (
            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground w-16 shrink-0">Username</span>
              <span className="font-medium truncate">{passwordDetails.username}</span>
            </div>
          )}
          {passwordDetails.url && (
            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground w-16 shrink-0">URL</span>
              <a
                href={passwordDetails.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline truncate"
                onClick={(e) => e.stopPropagation()}
              >
                {passwordDetails.url}
              </a>
            </div>
          )}
          <div className="pt-1">
            <PasswordReveal orgId={orgId} passwordId={rel.entity_id} />
          </div>
        </div>
      )}
    </div>
  );
}

interface RelatedItemsSidebarProps {
  orgId: string;
  entityType: EntityType;
  entityId: string;
}

export function RelatedItemsSidebar({
  orgId,
  entityType,
  entityId,
}: RelatedItemsSidebarProps) {
  const navigate = useNavigate();
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);

  const { data, isLoading, error } = useRelationships(orgId, entityType, entityId);
  const deleteRelationship = useDeleteRelationship(orgId);

  const relationships = data?.items ?? [];
  const groupedRelationships = groupRelationshipsByType(relationships);
  const entityTypes = Object.keys(groupedRelationships) as EntityType[];

  const handleNavigate = (rel: RelatedEntity) => {
    const route = getEntityRoute(rel.entity_type as EntityType);
    const path = `/org/${orgId}/${route}/${rel.entity_id}`;
    navigate(path);
  };

  const handleRemoveRelationship = async (
    rel: RelatedEntity,
    e: React.MouseEvent
  ) => {
    e.stopPropagation();
    try {
      await deleteRelationship.mutateAsync(rel.relationship_id);
      toast.success("Relationship removed");
    } catch {
      toast.error("Failed to remove relationship");
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Link2 className="h-4 w-4" />
            Related Items
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Link2 className="h-4 w-4" />
            Related Items
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive">Failed to load relationships</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Link2 className="h-4 w-4" />
              Related Items
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0"
              onClick={() => setIsAddDialogOpen(true)}
            >
              <Plus className="h-4 w-4" />
              <span className="sr-only">Add relationship</span>
            </Button>
          </div>
        </CardHeader>
        <CardContent className="px-3">
          {relationships.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-6 text-center">
              <LinkIcon className="h-8 w-8 text-muted-foreground/50 mb-2" />
              <p className="text-sm text-muted-foreground mb-3">
                No related items yet
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsAddDialogOpen(true)}
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Relationship
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {entityTypes.map((type) => {
                const Icon = getEntityIcon(type);
                const label = getEntityLabel(type);
                const rels = groupedRelationships[type];

                return (
                  <div key={type}>
                    <div className="flex items-center gap-2 mb-2">
                      <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        {label}s
                      </span>
                      <Badge variant="secondary" className="ml-auto text-xs">
                        {rels.length}
                      </Badge>
                    </div>
                    <div className="space-y-0.5">
                      {rels.map((rel) => (
                        <RelatedItemRow
                          key={rel.relationship_id}
                          rel={rel}
                          orgId={orgId}
                          onNavigate={() => handleNavigate(rel)}
                          onRemove={(e) => handleRemoveRelationship(rel, e)}
                          isDeleting={deleteRelationship.isPending}
                        />
                      ))}
                    </div>
                  </div>
                );
              })}

              <div className="pt-2 border-t">
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start text-muted-foreground"
                  onClick={() => setIsAddDialogOpen(true)}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add relationship
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <AddRelationshipDialog
        open={isAddDialogOpen}
        onOpenChange={setIsAddDialogOpen}
        orgId={orgId}
        sourceEntityType={entityType}
        sourceEntityId={entityId}
      />
    </>
  );
}
