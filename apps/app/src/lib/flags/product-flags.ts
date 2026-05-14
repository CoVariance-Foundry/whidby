export const PRODUCT_FLAGS = {
  userManagementEnabled: {
    key: "user_management_enabled",
    defaultValue: false,
  },
  billingCheckoutEnabled: {
    key: "billing_checkout_enabled",
    defaultValue: false,
  },
  reportQuotaEnforcementEnabled: {
    key: "report_quota_enforcement_enabled",
    defaultValue: true,
  },
  freshReportGenerationEnabled: {
    key: "fresh_report_generation_enabled",
    defaultValue: true,
  },
  cachedReportsEnabled: {
    key: "cached_reports_enabled",
    defaultValue: true,
  },
} as const;
