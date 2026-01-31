---
status: resolved
trigger: "Clicking on Filters throws error about Select.Item having empty string value"
created: 2026-01-30T00:00:00Z
updated: 2026-01-30T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - SelectItem in ColumnFiltersDropdown uses empty string value
test: Read data-table.tsx and examine SelectItem usage
expecting: Found SelectItem with value=""
next_action: Fix by using a sentinel value like "__all__" instead of empty string

## Symptoms

expected: Filters dropdown/dialog should open without errors
actual: Error thrown: "A <Select.Item /> must have a value prop that is not an empty string"
errors: Uncaught Error: A <Select.Item /> must have a value prop that is not an empty string. This is because the Select value can be set to an empty string to clear the selection and show the placeholder.
reproduction: Click on Filters
started: Current issue

## Eliminated

## Evidence

- timestamp: 2026-01-30T00:01:00Z
  checked: Grep for Filters and SelectItem in codebase
  found: data-table.tsx appears in both searches - likely location of issue
  implication: The Filters functionality likely uses SelectItem in data-table.tsx

## Resolution

root_cause: Line 562 in data-table.tsx uses `<SelectItem value="">` for the "All" filter option. Radix UI Select explicitly forbids empty string values because empty string is used to clear selection and show placeholder.
fix: Introduced sentinel value `ALL_FILTER_VALUE = "__all__"` and updated getFilterValue, handleFilterChange, and getSelectedLabel to use it. SelectItem now uses this sentinel value instead of empty string.
verification: TypeScript compilation passes. Lint passes (pre-existing warnings only). The SelectItem now has a valid non-empty value.
files_changed: ["/home/jack/GitHub/bifrost-docs/client/src/components/ui/data-table.tsx"]
