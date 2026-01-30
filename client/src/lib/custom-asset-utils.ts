import type { CustomAssetType, CustomAsset } from "@/hooks/useCustomAssets";

/**
 * Get the display field key for an asset type.
 *
 * Falls back to:
 * 1. The explicit display_field_key if set
 * 2. First text/textbox field
 * 3. First non-header field
 * 4. null if no fields exist
 */
export function getDisplayFieldKey(assetType: CustomAssetType): string | null {
  if (assetType.display_field_key) {
    return assetType.display_field_key;
  }

  // Fall back to first text/textbox field
  const nonHeaderFields = assetType.fields.filter((f) => f.type !== "header");
  for (const field of nonHeaderFields) {
    if (field.type === "text" || field.type === "textbox") {
      return field.key;
    }
  }

  // Fall back to first non-header field
  if (nonHeaderFields.length > 0) {
    return nonHeaderFields[0].key;
  }

  return null;
}

/**
 * Get the display value for an asset based on the display field key.
 */
export function getDisplayValue(
  asset: CustomAsset,
  displayFieldKey: string | null
): string {
  if (!displayFieldKey) return "Unnamed";
  const value = asset.values[displayFieldKey];
  if (value === undefined || value === null || value === "") return "Unnamed";
  return String(value);
}
