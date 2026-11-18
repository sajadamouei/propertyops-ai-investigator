import { test as base } from '@playwright/test'

export { expect } from '@playwright/test'

// Workflow tests start with onboarding already completed.
export const test = base.extend({
  page: async ({ page }, use) => {
    await page.addInitScript(() => {
      localStorage.setItem('propertyops_demo_welcome_seen', 'true')
    })
    await use(page)
  },
})
