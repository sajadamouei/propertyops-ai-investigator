import { expect, test } from '@playwright/test'

async function expectSuccessfulResponse<T>(response: import('@playwright/test').Response): Promise<T> {
  const responseBody = await response.text()

  expect(
    response.status(),
    `${response.request().method()} ${response.url()} failed with response body:\n${responseBody}`,
  ).toBe(200)

  return JSON.parse(responseBody) as T
}

test.describe('PropertyOps real investigation workflow', () => {
  test.describe.configure({ mode: 'serial' })
  test('fault scenario reaches the human approval boundary', async ({ page }) => {
    test.setTimeout(240_000)

    const pageErrors: string[] = []

    page.on('pageerror', (error) => {
      pageErrors.push(error.message)
    })

    await page.goto('/lab')

    await expect(
      page.getByRole('heading', {
        name: 'Investigation Lab',
        level: 1,
      }),
    ).toBeVisible()

    await page.getByLabel('Scenario').selectOption('fault')
    await expect(page.getByLabel('Scenario')).toHaveValue('fault')

    const workflowResponsePromise = page.waitForResponse(
      (response) =>
        response.url().endsWith('/api/workflow/start') &&
        response.request().method() === 'POST',
      { timeout: 180_000 },
    )

    await page.getByRole('button', {
      name: 'Run full pipeline',
    }).click()

    await expect(
      page.getByRole('button', { name: 'Run full pipeline' }),
    ).toBeDisabled()

    const workflowResponse = await workflowResponsePromise

    const workflow = await expectSuccessfulResponse<{
      status: string
      manifest: { status: string; current_step: string }
      investigation: unknown
      assessment: unknown
      approval_request: unknown
    }>(workflowResponse)

    expect(workflow.status).toBe('waiting_for_approval')
    expect(workflow.manifest.status).toBe('waiting')
    expect(workflow.manifest.current_step).toBe('human_approval')
    expect(workflow.investigation).toBeTruthy()
    expect(workflow.assessment).toBeTruthy()
    expect(workflow.approval_request).toBeTruthy()

    await expect(
      page.getByText('7 / 9 complete'),
    ).toBeVisible()

    await expect(
      page.getByText('Waiting for approval'),
    ).toBeVisible()

    // Use client-side navigation so the current React run state is preserved.
    await page.getByRole('link', { name: 'Operations', exact: true }).click()

    await expect(page).toHaveURL(/\/operations$/)

    await expect(
      page.getByRole('heading', {
        name: 'Heating delivery anomaly',
        level: 1,
      }),
    ).toBeVisible()

    await expect(
      page.getByText('AI assessment'),
    ).toBeVisible()

    await expect(
      page.getByRole('heading', {
        name: 'Review proposed work order',
        level: 2,
      }),
    ).toBeVisible()

    await expect(
      page.getByRole('button', { name: 'Approve work order' }),
    ).toBeVisible()

    expect(pageErrors).toEqual([])
  })

  test('rapid approval creates one real decision request and displays the work order ID', async ({ page }) => {
    test.setTimeout(240_000)

    await page.goto('/lab')
    await page.getByLabel('Scenario').selectOption('fault')
    await expect(page.getByLabel('Scenario')).toHaveValue('fault')

    const workflowResponsePromise = page.waitForResponse(
      (response) =>
        response.url().endsWith('/api/workflow/start') &&
        response.request().method() === 'POST',
      { timeout: 180_000 },
    )

    await page.getByRole('button', { name: 'Run full pipeline' }).click()

    const workflow = await expectSuccessfulResponse<{
      status: string
      manifest: { status: string; current_step: string | null }
    }>(await workflowResponsePromise)

    expect(workflow.status).toBe('waiting_for_approval')
    expect(workflow.manifest.status).toBe('waiting')
    expect(workflow.manifest.current_step).toBe('human_approval')

    // Use client-side navigation so the current React run state is preserved.
    await page.getByRole('link', { name: 'Operations', exact: true }).click()
    await expect(page).toHaveURL(/\/operations$/)

    const approveButton = page.getByRole('button', {
      name: 'Approve work order',
    })
    const rejectButton = page.getByRole('button', { name: 'Reject' })
    await expect(approveButton).toBeVisible()

    let decisionRequestCount = 0
    let signalDecisionRequestStarted!: () => void
    const decisionRequestStarted = new Promise<void>((resolve) => {
      signalDecisionRequestStarted = resolve
    })
    let releaseDecisionRequest!: () => void
    const decisionRequestRelease = new Promise<void>((resolve) => {
      releaseDecisionRequest = resolve
    })

    await page.route('**/api/workflow/decision', async (route) => {
      if (route.request().method() !== 'POST') {
        await route.continue()
        return
      }

      decisionRequestCount += 1
      if (decisionRequestCount === 1) signalDecisionRequestStarted()

      // Keep the real request pending until both controls have been checked.
      await decisionRequestRelease
      await route.continue()
    })

    const decisionResponsePromise = page.waitForResponse(
      (response) =>
        response.url().endsWith('/api/workflow/decision') &&
        response.request().method() === 'POST',
      { timeout: 60_000 },
    )

    await approveButton.evaluate((button) => {
      const approveElement = button as HTMLButtonElement

      approveElement.click()
      approveElement.click()
    })

    await decisionRequestStarted

    try {
      await expect(approveButton).toBeDisabled()
      await expect(rejectButton).toBeDisabled()
    } finally {
      releaseDecisionRequest()
    }

    const decision = await expectSuccessfulResponse<{
      status: string
      manifest: { status: string; current_step: string | null }
      approval: { approved: boolean }
      work_order: {
        created: boolean
        work_order: { id: string }
      } | null
    }>(await decisionResponsePromise)

    expect(decisionRequestCount).toBe(1)
    expect(decision.status).toBe('complete')
    expect(decision.manifest.status).toBe('complete')
    expect(decision.manifest.current_step).toBeNull()
    expect(decision.approval.approved).toBe(true)
    expect(decision.work_order?.created).toBe(true)

    const workOrderId = decision.work_order?.work_order.id
    expect(workOrderId).toBeTruthy()

    await expect(
      page.getByRole('heading', {
        name: 'Work order approved',
        level: 2,
      }),
    ).toBeVisible()

    await expect(
      page.getByText(`Approval recorded. Work order ${workOrderId} is now available.`),
    ).toBeVisible()
  })
})
