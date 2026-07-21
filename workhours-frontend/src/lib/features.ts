/**
 * Frontend-only feature flags for admin modules that still have live backend
 * support but should not be exposed in the current UI.
 */
export const features = {
  adminRoles: false,
  adminAudit: false,
  adminReports: false,
} as const
