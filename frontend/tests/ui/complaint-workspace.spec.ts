import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

async function expectTwoColumnContract(page: Page) {
  const workspace = page.getByTestId("complaint-workspace");
  const formPanel = page.getByTestId("complaint-form-panel");
  const assistantPanel = page.getByTestId("complaint-assistant-panel");

  await expect(workspace).toBeVisible();
  await expect(formPanel).toBeVisible();
  await expect(assistantPanel).toBeVisible();
  await expect(workspace).toHaveAttribute("data-column-count", "2");

  const workspaceBox = await workspace.boundingBox();
  const formBox = await formPanel.boundingBox();
  const assistantBox = await assistantPanel.boundingBox();

  expect(workspaceBox).not.toBeNull();
  expect(formBox).not.toBeNull();
  expect(assistantBox).not.toBeNull();

  if (!workspaceBox || !formBox || !assistantBox) {
    return;
  }

  const formRatio = formBox.width / workspaceBox.width;
  const assistantRatio = assistantBox.width / workspaceBox.width;

  expect(formBox.x).toBeLessThan(assistantBox.x);
  expect(formRatio).toBeGreaterThan(0.56);
  expect(formRatio).toBeLessThan(0.62);
  expect(assistantRatio).toBeGreaterThan(0.38);
  expect(assistantRatio).toBeLessThan(0.44);
}

test("empty desktop workspace screenshot", async ({ page }) => {
  await page.goto("/?state=empty");
  await expect(page.getByText("Log Customer Complaint")).toBeVisible();
  await expect(page.getByTestId("quality-intelligence-dock")).toHaveCount(0);
  await page.screenshot({ path: "test-results/screenshots/empty-desktop-workspace.png", fullPage: true });
});

test("extracting desktop workspace screenshot", async ({ page }) => {
  await page.goto("/?state=extracting");
  await expectTwoColumnContract(page);
  await expect(page.getByTestId("complaint-extraction-progress")).toContainText("62%");
  await expect(page.getByTestId("quality-intelligence-dock")).toBeVisible();
  await page.screenshot({ path: "test-results/screenshots/extracting-desktop-workspace.png", fullPage: true });
});

test("populated desktop workspace screenshot", async ({ page }) => {
  await page.goto("/?state=populated");
  await expectTwoColumnContract(page);
  const productName = page.getByRole("textbox", { name: "Product Name" });
  await expect(productName).toHaveValue("Amoxicillin Capsules 500 mg");
  await expect(productName).toHaveAttribute("readonly", "");
  await page.screenshot({ path: "test-results/screenshots/populated-desktop-workspace.png", fullPage: true });
});

test("edited desktop workspace screenshot", async ({ page }) => {
  await page.goto("/?state=edited");
  await expectTwoColumnContract(page);
  await expect(page.getByText("Recent assistant correction applied to highlighted fields.")).toBeVisible();
  await expect(page.getByText("Updated by AI")).toHaveCount(2);
  await page.screenshot({ path: "test-results/screenshots/edited-desktop-workspace.png", fullPage: true });
});

test("mobile stacked workspace screenshot", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto("/?state=extracting");

  const formPanel = page.getByTestId("complaint-form-panel");
  const assistantPanel = page.getByTestId("complaint-assistant-panel");
  const dock = page.getByTestId("quality-intelligence-dock");
  const formBox = await formPanel.boundingBox();
  const assistantBox = await assistantPanel.boundingBox();
  const dockBox = await dock.boundingBox();

  expect(formBox).not.toBeNull();
  expect(assistantBox).not.toBeNull();
  expect(dockBox).not.toBeNull();

  if (formBox && assistantBox && dockBox) {
    expect(formBox.y).toBeLessThan(assistantBox.y);
    expect(assistantBox.y).toBeLessThan(dockBox.y);
  }

  await page.screenshot({ path: "test-results/screenshots/mobile-stacked-workspace.png", fullPage: true });
});
