import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Building2,
  FileText,
  KeyRound,
  MapPin,
  Plus,
  Server,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ConfigForm } from "@/components/configurations/ConfigForm";
import { DocumentForm } from "@/components/documents/DocumentForm";
import { LocationForm } from "@/components/locations/LocationForm";
import { OrganizationForm } from "@/components/organizations/OrganizationForm";
import { PasswordForm } from "@/components/passwords/PasswordForm";
import {
  useConfigurationStatuses,
  useConfigurationTypes,
  useCreateConfiguration,
  type ConfigurationCreate,
  type ConfigurationUpdate,
} from "@/hooks/useConfigurations";
import {
  useCreateDocument,
  type DocumentCreate,
  type DocumentUpdate,
} from "@/hooks/useDocuments";
import {
  useCreateLocation,
  type LocationCreate,
  type LocationUpdate,
} from "@/hooks/useLocations";
import {
  useCreateOrganization,
  useOrganizations,
} from "@/hooks/useOrganizations";
import {
  useCreatePassword,
  type PasswordCreate,
  type PasswordUpdate,
} from "@/hooks/usePasswords";
import { usePermissions } from "@/hooks/usePermissions";
import { useOrganizationStore } from "@/stores/organization.store";

type QuickCreateType =
  | "organization"
  | "password"
  | "configuration"
  | "document"
  | "location";

interface CreatedRecord {
  label: string;
  openLabel: string;
  path: string;
  organizationName?: string;
}

const quickCreateItems = [
  { type: "organization", label: "Organization", icon: Building2 },
  { type: "password", label: "Password", icon: KeyRound },
  { type: "configuration", label: "Configuration", icon: Server },
  { type: "document", label: "Document", icon: FileText },
  { type: "location", label: "Location", icon: MapPin },
] satisfies Array<{
  type: QuickCreateType;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}>;

export function QuickCreateButton() {
  const navigate = useNavigate();
  const { orgId } = useParams<{ orgId?: string }>();
  const { canEdit, isAdmin } = usePermissions();
  const currentOrg = useOrganizationStore((state) => state.currentOrg);
  const setCurrentOrg = useOrganizationStore((state) => state.setCurrentOrg);
  const { data: organizations = [] } = useOrganizations();

  const enabledOrganizations = useMemo(
    () => organizations.filter((organization) => organization.is_enabled),
    [organizations]
  );

  const preferredOrgId = useMemo(() => {
    if (orgId && enabledOrganizations.some((organization) => organization.id === orgId)) {
      return orgId;
    }
    if (
      currentOrg?.is_enabled &&
      enabledOrganizations.some((organization) => organization.id === currentOrg.id)
    ) {
      return currentOrg.id;
    }
    return enabledOrganizations[0]?.id;
  }, [currentOrg, enabledOrganizations, orgId]);

  const [activeType, setActiveType] = useState<QuickCreateType | null>(null);
  const [selectedOrgId, setSelectedOrgId] = useState(preferredOrgId ?? "");
  const [createdRecord, setCreatedRecord] = useState<CreatedRecord | null>(null);

  useEffect(() => {
    if (!preferredOrgId) return;

    setSelectedOrgId(preferredOrgId);
  }, [preferredOrgId]);

  const selectedOrganization = enabledOrganizations.find(
    (organization) => organization.id === selectedOrgId
  );
  const activeOrgId = selectedOrganization?.id ?? "";

  const createOrganization = useCreateOrganization();
  const createPassword = useCreatePassword(activeOrgId);
  const createConfiguration = useCreateConfiguration(activeOrgId);
  const createDocument = useCreateDocument(activeOrgId);
  const createLocation = useCreateLocation(activeOrgId);
  const loadConfigurationMetadata = activeType === "configuration";
  const { data: configurationTypes = [] } = useConfigurationTypes({
    enabled: loadConfigurationMetadata,
  });
  const { data: configurationStatuses = [] } = useConfigurationStatuses({
    enabled: loadConfigurationMetadata,
  });

  const closeActiveForm = () => {
    setActiveType(null);
  };

  const finishCreate = (record: CreatedRecord) => {
    closeActiveForm();
    setCreatedRecord(record);
  };

  const requireOrganization = () => {
    if (!selectedOrganization) {
      toast.error("Select an organization before creating this record");
      return null;
    }
    return selectedOrganization;
  };

  const handleOpenType = (type: QuickCreateType) => {
    setActiveType(type);
  };

  const handleOrganizationCreate = async (formData: {
    name: string;
    metadata?: Record<string, unknown>;
  }) => {
    try {
      const result = await createOrganization.mutateAsync({ name: formData.name });
      const organization = result.data;
      setCurrentOrg(organization);
      toast.success("Organization created successfully");
      finishCreate({
        label: "Organization",
        openLabel: "Open organization",
        path: `/org/${organization.id}`,
      });
    } catch {
      toast.error("Failed to create organization");
    }
  };

  const handlePasswordCreate = async (formData: PasswordCreate | PasswordUpdate) => {
    const organization = requireOrganization();
    if (!organization) return;

    try {
      const password = await createPassword.mutateAsync(formData as PasswordCreate);
      toast.success("Password created successfully");
      finishCreate({
        label: "Password",
        openLabel: "Open password",
        path: `/org/${organization.id}/passwords/${password.id}`,
        organizationName: organization.name,
      });
    } catch {
      toast.error("Failed to create password");
    }
  };

  const handleConfigurationCreate = async (
    formData: ConfigurationCreate | ConfigurationUpdate
  ) => {
    const organization = requireOrganization();
    if (!organization) return;

    try {
      const configuration = await createConfiguration.mutateAsync(
        formData as ConfigurationCreate
      );
      toast.success("Configuration created successfully");
      finishCreate({
        label: "Configuration",
        openLabel: "Open configuration",
        path: `/org/${organization.id}/configurations/${configuration.id}`,
        organizationName: organization.name,
      });
    } catch {
      toast.error("Failed to create configuration");
    }
  };

  const handleDocumentCreate = async (formData: DocumentCreate | DocumentUpdate) => {
    const organization = requireOrganization();
    if (!organization) return;

    try {
      const document = await createDocument.mutateAsync(formData as DocumentCreate);
      toast.success("Document created successfully");
      finishCreate({
        label: "Document",
        openLabel: "Open document",
        path: `/org/${organization.id}/documents/${document.id}`,
        organizationName: organization.name,
      });
    } catch {
      toast.error("Failed to create document");
    }
  };

  const handleLocationCreate = async (formData: LocationCreate | LocationUpdate) => {
    const organization = requireOrganization();
    if (!organization) return;

    try {
      const location = await createLocation.mutateAsync(formData as LocationCreate);
      toast.success("Location created successfully");
      finishCreate({
        label: "Location",
        openLabel: "Open location",
        path: `/org/${organization.id}/locations/${location.id}`,
        organizationName: organization.name,
      });
    } catch {
      toast.error("Failed to create location");
    }
  };

  const handleNavigateToCreatedRecord = () => {
    if (!createdRecord) return;

    const path = createdRecord.path;
    setCreatedRecord(null);
    navigate(path);
  };

  const organizationContextSlot =
    activeType && activeType !== "organization" ? (
      <div className="space-y-2 rounded-md border bg-muted/30 p-3">
        <Label htmlFor="quick-create-organization">Organization</Label>
        {enabledOrganizations.length > 0 ? (
          <Select value={selectedOrgId} onValueChange={setSelectedOrgId}>
            <SelectTrigger id="quick-create-organization">
              <SelectValue placeholder="Select organization" />
            </SelectTrigger>
            <SelectContent>
              {enabledOrganizations.map((organization) => (
                <SelectItem key={organization.id} value={organization.id}>
                  {organization.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <p className="text-sm text-muted-foreground">
            Create or enable an organization before adding this record.
          </p>
        )}
      </div>
    ) : undefined;

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            size="icon"
            aria-label="Quick create"
            title="Quick create"
          >
            <Plus className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-52">
          <DropdownMenuLabel>Create</DropdownMenuLabel>
          {quickCreateItems.map(({ type, label, icon: Icon }) => {
            const requiresOrganization = type !== "organization";
            const disabled =
              (type === "organization" && !isAdmin) ||
              (requiresOrganization && (!canEdit || !selectedOrganization));

            return (
              <DropdownMenuItem
                key={type}
                disabled={disabled}
                onSelect={() => handleOpenType(type)}
              >
                <Icon className="h-4 w-4" />
                <span>{label}</span>
              </DropdownMenuItem>
            );
          })}
          <DropdownMenuSeparator />
          <p className="px-2 py-1 text-xs text-muted-foreground">
            {selectedOrganization
              ? `Using ${selectedOrganization.name}`
              : "Select an organization to create records"}
          </p>
        </DropdownMenuContent>
      </DropdownMenu>

      {activeType === "organization" && (
        <OrganizationForm
          open
          onOpenChange={(open) => {
            if (!open) closeActiveForm();
          }}
          onSubmit={handleOrganizationCreate}
          isSubmitting={createOrganization.isPending}
          mode="create"
        />
      )}

      {activeType === "password" && selectedOrganization && (
        <PasswordForm
          key={`password-${selectedOrganization.id}`}
          open
          onOpenChange={(open) => {
            if (!open) closeActiveForm();
          }}
          onSubmit={handlePasswordCreate}
          isSubmitting={createPassword.isPending}
          mode="create"
          orgId={selectedOrganization.id}
          contextSlot={organizationContextSlot}
        />
      )}

      {activeType === "configuration" && selectedOrganization && (
        <ConfigForm
          key={`configuration-${selectedOrganization.id}`}
          open
          onOpenChange={(open) => {
            if (!open) closeActiveForm();
          }}
          onSubmit={handleConfigurationCreate}
          isSubmitting={createConfiguration.isPending}
          mode="create"
          types={configurationTypes}
          statuses={configurationStatuses}
          orgId={selectedOrganization.id}
          contextSlot={organizationContextSlot}
        />
      )}

      {activeType === "document" && selectedOrganization && (
        <DocumentForm
          key={`document-${selectedOrganization.id}`}
          open
          onOpenChange={(open) => {
            if (!open) closeActiveForm();
          }}
          onSubmit={handleDocumentCreate}
          isSubmitting={createDocument.isPending}
          mode="create"
          orgId={selectedOrganization.id}
          contextSlot={organizationContextSlot}
        />
      )}

      {activeType === "location" && selectedOrganization && (
        <LocationForm
          key={`location-${selectedOrganization.id}`}
          open
          onOpenChange={(open) => {
            if (!open) closeActiveForm();
          }}
          onSubmit={handleLocationCreate}
          isSubmitting={createLocation.isPending}
          mode="create"
          orgId={selectedOrganization.id}
          contextSlot={organizationContextSlot}
        />
      )}

      <Dialog
        open={createdRecord !== null}
        onOpenChange={(open) => {
          if (!open) setCreatedRecord(null);
        }}
      >
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>{createdRecord?.label} created</DialogTitle>
            <DialogDescription>
              {createdRecord?.organizationName
                ? `Created in ${createdRecord.organizationName}.`
                : "The new organization is ready."}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreatedRecord(null)}>
              Stay here
            </Button>
            <Button onClick={handleNavigateToCreatedRecord}>
              {createdRecord?.openLabel ?? "Open record"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
