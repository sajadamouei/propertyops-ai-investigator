import { expect, test } from '@playwright/test'

const welcomeTitle = 'From fragmented building data to evidence-based maintenance decisions'

test.beforeEach(async ({ page }) => {
  // An empty session is enough to exercise guidance without running the pipeline.
  await page.route('**/api/runs/current/recovery', (route) => route.fulfill({
    status: 404,
    json: { detail: 'No current run' },
  }))
})

test('starts in Lab and remembers the first-visit dismissal', async ({ page }) => {
  await page.goto('/operations')
  const welcome = page.getByRole('dialog', { name: welcomeTitle })
  await expect(welcome.getByRole('heading', { name: welcomeTitle })).toBeFocused()
  await welcome.getByRole('link', { name: 'Start in Lab' }).click()

  await expect(page).toHaveURL(/\/lab$/)
  await expect(welcome).toHaveCount(0)
  await expect(page.getByLabel('Scenario')).toHaveValue('fault')
  await expect(page.getByLabel('Days')).toHaveValue('14')
  await expect(page.getByLabel('Random seed')).toHaveValue('42')
  await expect(page.getByText('Choose a simulated operating scenario, then run the full pipeline or inspect it one stage at a time.')).toBeVisible()

  await page.reload()
  await expect(page.getByRole('heading', { name: 'Investigation Lab' })).toBeVisible()
  await expect(welcome).toHaveCount(0)
})

test('can stay in Operations and start the recommended investigation later', async ({ page }) => {
  await page.goto('/')
  const welcome = page.getByRole('dialog', { name: welcomeTitle })
  await welcome.getByRole('button', { name: 'Explore on my own' }).click()

  await expect(page).toHaveURL(/\/operations$/)
  await expect(page.getByRole('heading', { name: 'No active investigation' })).toBeVisible()
  await expect(page.getByText('Recommended: Heating Valve Fault · 14 days · Seed 42')).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'No active investigation' })).toBeVisible()
  await expect(welcome).toHaveCount(0)
  await page.getByRole('link', { name: 'Start demo investigation' }).click()
  await expect(page).toHaveURL(/\/lab$/)
})

test('hands off to the guide and restores focus when the drawer closes', async ({ page }) => {
  await page.goto('/operations')
  const welcome = page.getByRole('dialog', { name: welcomeTitle })
  const guide = page.getByRole('dialog', { name: 'Demo guide' })
  const guideButton = page.getByRole('button', { name: 'Demo guide', exact: true })
  await welcome.getByRole('button', { name: 'How does the demo work?' }).click()

  await expect(welcome).toHaveCount(0)
  await page.locator('.topbar-guide').evaluate((button: HTMLButtonElement) => button.focus())
  await expect(guide.getByRole('heading', { name: 'Demo guide' })).toBeFocused()
  await expect(guide.getByRole('link', { name: 'View GitHub' })).toHaveAttribute('target', '_blank')

  await page.keyboard.press('Escape')
  await expect(guide).toHaveCount(0)
  await expect(guideButton).toBeFocused()
  await guideButton.click()
  await expect(guide).toBeVisible()
  await page.mouse.click(16, 16)
  await expect(guide).toHaveCount(0)

  await guideButton.click()
  await guide.getByRole('link', { name: 'Open Lab' }).click()
  await expect(page).toHaveURL(/\/lab$/)
  await expect(guide).toHaveCount(0)
  await guideButton.click()
  await guide.getByRole('button', { name: 'Close demo guide' }).click()
  await expect(guideButton).toBeFocused()
})

test('keeps the dark welcome and guide usable on a small screen', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 568 })
  await page.goto('/lab')
  const welcome = page.getByRole('dialog', { name: welcomeTitle })
  const welcomeBody = welcome.getByRole('region', { name: welcomeTitle })
  await expect(welcomeBody).toBeVisible()
  expect(await welcomeBody.evaluate((element) => element.scrollHeight > element.clientHeight)).toBe(true)
  await expect(welcome.getByRole('link', { name: 'Start in Lab' })).toBeInViewport()
  await page.keyboard.press('Escape')
  await expect(welcome).toHaveCount(0)

  await page.getByRole('button', { name: 'Demo guide', exact: true }).click()
  const guide = page.getByRole('dialog', { name: 'Demo guide' })
  const guideBody = guide.getByRole('region', { name: 'Demo guide' })
  await expect(guideBody).toBeVisible()
  expect(await guideBody.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true)
  await expect(guide.getByRole('button', { name: 'Close demo guide' })).toBeInViewport()
  await expect(guide.getByRole('link', { name: 'Project presentation' })).toBeInViewport()
})
