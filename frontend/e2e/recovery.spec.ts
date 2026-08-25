import { expect, test } from '@playwright/test'

async function expectSuccessfulJson<T>(response: import('@playwright/test').Response): Promise<T> {
  const body = await response.text()
  expect(
    response.status(),
    `${response.request().method()} ${response.url()} failed with response body:\n${body}`,
  ).toBe(200)
  return JSON.parse(body) as T
}

test.describe('Persisted run recovery', () => {
  test.describe.configure({ mode: 'serial' })

  let approvedWorkOrderId = ''

  test('refreshes at approval, resumes the real checkpoint, and creates a work order', async ({ page }) => {
    test.setTimeout(240_000)

    await page.goto('/lab')
    await page.getByLabel('Scenario').selectOption('fault')

    const workflowResponsePromise = page.waitForResponse(
      (response) =>
        response.url().endsWith('/api/workflow/start') &&
        response.request().method() === 'POST',
      { timeout: 180_000 },
    )

    await page.getByRole('button', { name: 'Run full pipeline' }).click()

    const workflow = await expectSuccessfulJson<{
      status: string
      manifest: { status: string; current_step: string | null }
    }>(await workflowResponsePromise)

    expect(workflow.status).toBe('waiting_for_approval')
    expect(workflow.manifest.status).toBe('waiting')
    expect(workflow.manifest.current_step).toBe('human_approval')
    await expect(page.getByText('Waiting for approval')).toBeVisible()

    await page.getByRole('link', { name: 'Operations', exact: true }).click()
    await expect(
      page.getByRole('heading', { name: 'Review proposed work order', level: 2 }),
    ).toBeVisible()

    await page.reload()

    await expect(
      page.getByRole('heading', { name: 'Heating delivery anomaly', level: 1 }),
    ).toBeVisible()
    await expect(page.getByText('AI assessment')).toBeVisible()
    await expect(
      page.getByRole('heading', { name: 'Review proposed work order', level: 2 }),
    ).toBeVisible()
    await expect(page.getByRole('button', { name: 'Approve work order' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Reject' })).toBeVisible()

    const decisionResponsePromise = page.waitForResponse(
      (response) =>
        response.url().endsWith('/api/workflow/decision') &&
        response.request().method() === 'POST',
      { timeout: 60_000 },
    )

    await page.getByRole('button', { name: 'Approve work order' }).click()

    const decision = await expectSuccessfulJson<{
      status: string
      approval: { approved: boolean }
      work_order: { created: boolean; work_order: { id: string } } | null
    }>(await decisionResponsePromise)

    expect(decision.status).toBe('complete')
    expect(decision.approval.approved).toBe(true)
    expect(decision.work_order?.created).toBe(true)
    approvedWorkOrderId = decision.work_order?.work_order.id ?? ''
    expect(approvedWorkOrderId).not.toBe('')

    await expect(
      page.getByRole('heading', { name: 'Work order approved', level: 2 }),
    ).toBeVisible()
    await expect(page.getByText(approvedWorkOrderId, { exact: false }).first()).toBeVisible()
  })

  test('refreshes after completion without repeating approval', async ({ page }) => {
    test.setTimeout(60_000)
    expect(approvedWorkOrderId).not.toBe('')

    let decisionRequestCount = 0
    page.on('request', (request) => {
      if (
        request.url().endsWith('/api/workflow/decision') &&
        request.method() === 'POST'
      ) {
        decisionRequestCount += 1
      }
    })

    await page.goto('/operations')

    await expect(
      page.getByRole('heading', { name: 'Work order approved', level: 2 }),
    ).toBeVisible()
    await expect(page.getByText(approvedWorkOrderId, { exact: false }).first()).toBeVisible()

    await page.reload()

    await expect(
      page.getByRole('heading', { name: 'Work order approved', level: 2 }),
    ).toBeVisible()
    await expect(page.getByText(approvedWorkOrderId, { exact: false }).first()).toBeVisible()
    await expect(page.getByRole('button', { name: 'Approve work order' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Reject' })).toHaveCount(0)
    expect(decisionRequestCount).toBe(0)
  })

  test('shows neutral UI while the real recovery snapshot is pending', async ({ page }) => {
    test.setTimeout(60_000)
    expect(approvedWorkOrderId).not.toBe('')

    let releaseRecovery = () => {}
    const recoveryGate = new Promise<void>((resolve) => {
      releaseRecovery = resolve
    })
    let signalRecoveryStarted = () => {}
    const recoveryStarted = new Promise<void>((resolve) => {
      signalRecoveryStarted = resolve
    })

    await page.route('**/api/runs/current/recovery', async (route) => {
      signalRecoveryStarted()
      await recoveryGate
      await route.continue()
    })

    const navigationPromise = page.goto('/operations')
    await recoveryStarted

    try {
      const restoringStatus = page.getByRole('status')
      await expect(restoringStatus).toBeVisible()
      await expect(restoringStatus).toContainText('Restoring current run')
      await expect(
        page.getByRole('heading', { name: 'No active investigation', level: 1 }),
      ).toHaveCount(0)
    } finally {
      releaseRecovery()
    }

    await navigationPromise

    await expect(
      page.getByRole('heading', { name: 'Work order approved', level: 2 }),
    ).toBeVisible()
    await expect(
      page.getByText(approvedWorkOrderId, { exact: false }).first(),
    ).toBeVisible()
  })
})
