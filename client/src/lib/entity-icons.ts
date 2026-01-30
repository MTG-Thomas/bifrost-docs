import { KeyRound, Server, MapPin, FileText, Layers } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type EntityType = "password" | "configuration" | "location" | "document" | "custom_asset";

export const entityIcons: Record<EntityType, LucideIcon> = {
  password: KeyRound,
  configuration: Server,
  location: MapPin,
  document: FileText,
  custom_asset: Layers,
};

export const entityLabels: Record<EntityType, string> = {
  password: "Password",
  configuration: "Configuration",
  location: "Location",
  document: "Document",
  custom_asset: "Custom Asset",
};

export const entityPluralLabels: Record<EntityType, string> = {
  password: "Passwords",
  configuration: "Configurations",
  location: "Locations",
  document: "Documents",
  custom_asset: "Custom Assets",
};

export const entityRoutes: Record<EntityType, string> = {
  password: "passwords",
  configuration: "configurations",
  location: "locations",
  document: "documents",
  custom_asset: "assets",
};

export function getEntityIcon(entityType: string): LucideIcon {
  return entityIcons[entityType as EntityType] || Layers;
}

export function getEntityLabel(entityType: string): string {
  return entityLabels[entityType as EntityType] || entityType;
}

export function getEntityPluralLabel(entityType: string): string {
  return entityPluralLabels[entityType as EntityType] || entityType;
}

export function getEntityRoute(entityType: string): string {
  return entityRoutes[entityType as EntityType] || entityType;
}
