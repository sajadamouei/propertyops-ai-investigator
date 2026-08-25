import { expect, test } from '@playwright/test'

test.describe('PropertyOps application shell', () => {
  test.describe.configure({ mode: 'serial' })

  test('root route opens Operations with a recovered normal run', async ({ page, request }) => {
    const pageErrors: string[] = []

    page.on('pageerror', (error) => {
      pageErrors.push(error.message)
    })

    const reset = await request.post('http://127.0.0.1:8080/api/runs/reset', {
      data: { scenario: 'normal_operation', days: 14, seed: 42 },
    })
    expect(reset.status()).toBe(200)

    for (const path of ['generate', 'features', 'detect', 'incident']) {
      const response = await request.post(`http://127.0.0.1:8080/api/pipeline/${path}`)
      expect(response.status(), await response.text()).toBe(200)
    }

    await page.goto('/')

    await expect(page).toHaveURL(/\/operations$/)

    await expect(
      page.getByRole('heading', {
        name: 'No active incidents',
        level: 1,
      }),
    ).toBeVisible()

    await expect(
      page.getByText(
        'Building systems operating normally',
      ),
    ).toBeVisible()

    expect(pageErrors).toEqual([])
  })

  test('unknown route falls back to Operations', async ({ page }) => {
    await page.goto('/this-route-does-not-exist')

    await expect(page).toHaveURL(/\/operations$/)

    await expect(
      page.getByRole('heading', {
        name: 'No active incidents',
        level: 1,
      }),
    ).toBeVisible()
  })
})
