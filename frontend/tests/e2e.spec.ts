import { test, expect } from '@playwright/test';

const SAMPLE_PROMPT = 'Create a 3-slide deck about AI-assisted design trends in 2025.';

test('入力からPDF生成までのフロー', async ({ page }) => {
    let dialogMessage = '';
    page.on('dialog', async (dialog) => {
        dialogMessage = dialog.message();
        await dialog.accept();
    });

    await page.goto('/');

    await page.getByTestId('plan-input').fill(SAMPLE_PROMPT);
    await page.getByTestId('generate-plan').click();

    const slideStatus = page.getByTestId('slide-status-1');
    await expect(slideStatus).toHaveAttribute('data-status', 'ready', { timeout: 120000 });

    await expect(page.getByTestId('slide-spinner-1')).toHaveCount(0);
    await expect(page.getByTestId('slide-image-1')).toBeVisible();

    const [popup, assembleResponse] = await Promise.all([
        page.waitForEvent('popup'),
        page.waitForResponse((response) => {
            return response.url().includes('/api/assemble') && response.request().method() === 'POST';
        }),
        page.getByTestId('download-pdf').click()
    ]);

    if (!assembleResponse.ok()) {
        const bodyText = await assembleResponse.text();
        throw new Error(`assemble failed: ${assembleResponse.status()} ${bodyText}`);
    }
    const assembleData = await assembleResponse.json();
    expect(assembleData.url).toContain('/static/pdfs/');
    expect(popup).toBeTruthy();
    expect(dialogMessage).toBe('');
});
