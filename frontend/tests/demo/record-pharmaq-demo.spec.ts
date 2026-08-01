import { expect, test, type Locator, type Page } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const frontendRoot = process.cwd();
const repoRoot = path.resolve(frontendRoot, "..");
const demoDir = path.join(repoRoot, "demo");
const sourcePdfPath = path.join(demoDir, "video-demo-complaint.pdf");
const finalWebmPath = path.join(demoDir, "pharmaq-sentinel-7-minute-demo.webm");
const isDryRun = process.env.PHARMAQ_DEMO_RECORDING_MODE === "dry";
const baseUrl = process.env.PHARMAQ_DEMO_BASE_URL ?? "http://127.0.0.1:5173";
const targetDurationMs = isDryRun ? 95_000 : 420_000;

const initialComplaint = [
  "Apollo Pharmacy Delhi reported discoloured capsules. Quantity affected is 48 capsules.",
  "Product involved: Amoxicillin Capsules 500 mg from batch BMX240602.",
  "The complaint was received on 2026-07-18 for the India market."
].join(" ");

const correctionMessage = "Complaint date is 2026-07-18.";
const safetyMessage = [
  "Additional complaint information: a possible adverse event was reported;",
  "one customer developed swelling after consuming a capsule."
].join(" ");
const summaryMessage = "Please summarize the current draft, missing information, evidence, and AI limitations for QA review.";

async function waitForDemoPause(milliseconds: number) {
  await new Promise((resolve) => setTimeout(resolve, isDryRun ? Math.min(milliseconds, 650) : milliseconds));
}

async function installCursorOverlay(page: Page) {
  await page.addStyleTag({
    content: `
      .pharmaq-demo-cursor {
        position: fixed;
        left: 0;
        top: 0;
        z-index: 2147483647;
        width: 24px;
        height: 24px;
        pointer-events: none;
        border: 2px solid #6d28d9;
        border-radius: 999px;
        box-shadow: 0 0 0 6px rgba(109, 40, 217, 0.15), 0 10px 20px rgba(31, 41, 55, 0.18);
        transform: translate(-50%, -50%);
        transition: transform 160ms ease, width 140ms ease, height 140ms ease, background 140ms ease;
      }
      .pharmaq-demo-cursor::after {
        content: "";
        position: absolute;
        width: 6px;
        height: 6px;
        left: 50%;
        top: 50%;
        transform: translate(-50%, -50%);
        border-radius: 999px;
        background: #6d28d9;
      }
      .pharmaq-demo-cursor.is-clicking {
        width: 36px;
        height: 36px;
        background: rgba(109, 40, 217, 0.1);
      }
    `
  });
  await page.evaluate(() => {
    if (document.querySelector(".pharmaq-demo-cursor")) {
      return;
    }
    const cursor = document.createElement("div");
    cursor.className = "pharmaq-demo-cursor";
    cursor.setAttribute("aria-hidden", "true");
    document.body.appendChild(cursor);
    window.addEventListener("mousemove", (event) => {
      cursor.style.transform = `translate(${event.clientX - 12}px, ${event.clientY - 12}px)`;
    });
    window.addEventListener("mousedown", () => cursor.classList.add("is-clicking"));
    window.addEventListener("mouseup", () => cursor.classList.remove("is-clicking"));
  });
}

async function visibleLocator(locator: Locator) {
  await locator.first().scrollIntoViewIfNeeded();
  await expect(locator.first()).toBeVisible({ timeout: 30_000 });
  return locator.first();
}

async function moveTo(page: Page, locator: Locator) {
  const target = await visibleLocator(locator);
  const box = await target.boundingBox();
  if (!box) {
    throw new Error("Target was visible but had no clickable box.");
  }
  const x = box.x + box.width / 2;
  const y = box.y + Math.min(box.height / 2, 32);
  await page.mouse.move(x, y, { steps: isDryRun ? 5 : 18 });
  await waitForDemoPause(250);
  return { target, x, y };
}

async function humanClick(page: Page, locator: Locator) {
  const { target, x, y } = await moveTo(page, locator);
  await target.click({ delay: isDryRun ? 1 : 90 });
  await waitForDemoPause(700);
  return { x, y };
}

async function humanType(page: Page, locator: Locator, text: string) {
  await humanClick(page, locator);
  for (const character of text) {
    await page.keyboard.type(character, { delay: isDryRun ? 1 : 22 + Math.floor(Math.random() * 24) });
    if (!isDryRun && [".", ";", ","].includes(character)) {
      await page.waitForTimeout(90);
    }
  }
  await waitForDemoPause(350);
}

async function submitAssistantMessage(page: Page, text: string) {
  const input = page.getByTestId("complaint-chat-input");
  await humanType(page, input, text);
  await expect(input).toHaveValue(text, { timeout: 10_000 });
  await humanClick(page, page.getByRole("button", { name: "Send assistant message" }));
  await expect(input).toHaveValue("", { timeout: 10_000 });
}

function complaintField(page: Page, name: string) {
  return page.getByRole("textbox", { name });
}

async function waitForMilestone(startedAt: number, milliseconds: number) {
  const target = isDryRun ? Math.min(milliseconds, targetDurationMs - 5_000) : milliseconds;
  const remaining = target - (Date.now() - startedAt);
  if (remaining > 0) {
    await pageWait(remaining);
  }
}

async function pageWait(milliseconds: number) {
  await new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function openQualityDock(page: Page) {
  const dock = page.getByTestId("quality-intelligence-dock");
  await expect(dock).toBeVisible({ timeout: 30_000 });
  const expanded = await page.getByRole("tablist", { name: "Quality Intelligence" }).isVisible().catch(() => false);
  if (!expanded) {
    await humanClick(page, page.getByRole("button", { name: "Quality Intelligence" }));
  }
}

test("record PharmaQ Sentinel seven minute working demo", async ({ browser }) => {
  test.setTimeout(isDryRun ? 180_000 : 540_000);

  await fs.mkdir(demoDir, { recursive: true });
  await fs.access(sourcePdfPath);

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    recordVideo: isDryRun
      ? undefined
      : {
          dir: demoDir,
          size: { width: 1920, height: 1080 }
        },
    acceptDownloads: true
  });
  await context.addInitScript(() => {
    sessionStorage.clear();
  });

  const page = await context.newPage();
  const video = page.video();
  const startedAt = Date.now();

  await page.goto(`${baseUrl}/`, { waitUntil: "networkidle" });
  await installCursorOverlay(page);
  await expect(page.getByRole("link", { name: "PharmaQ Sentinel" }).first()).toBeVisible({ timeout: 30_000 });
  await moveTo(page, page.getByRole("link", { name: "PharmaQ Sentinel" }).first());
  await waitForDemoPause(2_000);
  await humanClick(page, page.getByRole("link", { name: "Launch Complaint Workspace" }).first());

  await expect(page.getByTestId("complaint-workspace")).toBeVisible({ timeout: 45_000 });
  await installCursorOverlay(page);
  await waitForDemoPause(1_200);
  await humanClick(page, complaintField(page, "Product Name"));
  await page.keyboard.press("A");
  await expect(complaintField(page, "Product Name")).toHaveValue(/Awaiting AI extraction|Not provided/);
  await page.keyboard.press("ControlOrMeta+A").catch(() => undefined);
  await waitForMilestone(startedAt, 30_000);

  await submitAssistantMessage(page, initialComplaint);
  await expect(complaintField(page, "Product Name")).toHaveValue(/Amoxicillin/i, { timeout: 60_000 });
  await expect(complaintField(page, "Batch/Lot Number")).toHaveValue(/BMX240602/i, { timeout: 60_000 });
  await waitForMilestone(startedAt, 75_000);

  const chooserPromise = page.waitForEvent("filechooser");
  await humanClick(page, page.getByTestId("complaint-upload-dropzone"));
  const fileChooser = await chooserPromise;
  await fileChooser.setFiles(sourcePdfPath);
  await expect(page.getByText("video-demo-complaint.pdf")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("complaint-extraction-progress")).toBeVisible({ timeout: 30_000 });
  await expect(complaintField(page, "Customer Name")).toHaveValue(/Apollo/i, { timeout: 60_000 });
  await waitForMilestone(startedAt, 125_000);

  await submitAssistantMessage(page, correctionMessage);
  await expect(complaintField(page, "Batch/Lot Number")).toHaveValue(/BMX240602/i, { timeout: 60_000 });
  await expect(complaintField(page, "Quantity Affected")).toHaveValue(/48/i, { timeout: 60_000 });
  await expect(complaintField(page, "Complaint Date")).toHaveValue(/2026-07-18/i, { timeout: 60_000 });
  await waitForMilestone(startedAt, 175_000);

  const evidenceButton = page.getByRole("button", { name: "View evidence for Batch/Lot Number" });
  if (await evidenceButton.isVisible().catch(() => false)) {
    await humanClick(page, evidenceButton);
    await expect(page.getByRole("dialog", { name: /Evidence: Batch\/Lot Number/ })).toBeVisible({ timeout: 20_000 });
    await waitForDemoPause(3_000);
    await humanClick(page, page.getByRole("button", { name: "Close drawer" }).last());
  }
  await waitForMilestone(startedAt, 205_000);

  await openQualityDock(page);
  await humanClick(page, page.getByRole("tab", { name: "Batch Intelligence" }));
  await humanClick(page, page.getByRole("button", { name: "Run Analysis" }));
  await expect(page.getByTestId("batch-impact-graph")).toBeVisible({ timeout: 90_000 });
  await expect(page.getByTestId("batch-impact-metrics")).toBeVisible({ timeout: 30_000 });
  const deviationNode = page.getByText("DEV-2026-023").first();
  if (await deviationNode.isVisible().catch(() => false)) {
    await humanClick(page, deviationNode);
    await waitForDemoPause(2_000);
    const closeDrawer = page.getByRole("button", { name: "Close drawer" }).last();
    if (await closeDrawer.isVisible().catch(() => false)) {
      await humanClick(page, closeDrawer);
    }
  }
  await humanClick(page, page.getByRole("button", { name: "Simulate Scope" }));
  await expect(page.getByRole("dialog", { name: "Containment Scope Simulation" })).toBeVisible({ timeout: 20_000 });
  await humanClick(page, page.getByRole("button", { name: "Run Simulation" }));
  await expect(page.getByTestId("containment-simulation-result")).toBeVisible({ timeout: 30_000 });
  await waitForDemoPause(2_000);
  await humanClick(page, page.getByRole("button", { name: "Close" }).last());
  await waitForMilestone(startedAt, 265_000);

  await humanClick(page, page.getByRole("tab", { name: "Quality War Room" }));
  await humanClick(page, page.getByRole("button", { name: "Run War Room" }));
  await expect(page.getByTestId("quality-war-room-panel")).toBeVisible({ timeout: 90_000 });
  await expect(page.getByTestId("auditor-challenge-card")).toBeVisible({ timeout: 45_000 });
  await expect(page.getByTestId("consensus-panel")).toBeVisible({ timeout: 45_000 });
  await waitForMilestone(startedAt, 310_000);

  await submitAssistantMessage(page, safetyMessage);
  await expect(page.getByText(/possible adverse event|pharmacovigilance|PV review/i).first()).toBeVisible({ timeout: 90_000 });
  await waitForMilestone(startedAt, 345_000);

  await openQualityDock(page);
  await humanClick(page, page.getByRole("tab", { name: "Investigation Support" }));
  await humanClick(page, page.getByRole("button", { name: "Run Support" }));
  await expect(page.getByTestId("investigation-support-panel")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId("duplicate-details-table")).toBeVisible({ timeout: 60_000 });
  await waitForMilestone(startedAt, 375_000);

  await submitAssistantMessage(page, summaryMessage);
  await waitForDemoPause(3_000);
  await humanClick(page, page.getByTestId("complaint-save-button"));
  await expect(page.getByRole("dialog", { name: "Save Complaint" })).toBeVisible({ timeout: 20_000 });
  const acknowledgement = page.getByLabel("I acknowledge the listed non-critical missing information.");
  if (await acknowledgement.isVisible().catch(() => false)) {
    await humanClick(page, acknowledgement);
  }
  await humanClick(page, page.getByRole("dialog", { name: "Save Complaint" }).getByRole("button", { name: "Save Complaint" }));
  await expect(page.getByText("View QMS Ledger")).toBeVisible({ timeout: 60_000 });
  await waitForMilestone(startedAt, 397_000);

  await humanClick(page, page.getByText("View QMS Ledger"));
  await expect(page.getByRole("heading", { name: "Saved Complaints" })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("BMX240602")).toBeVisible({ timeout: 30_000 });
  await humanType(page, page.getByPlaceholder("Product name"), "Amoxicillin");
  await humanClick(page, page.getByRole("button", { name: "Search" }));
  await expect(page.getByText("BMX240602")).toBeVisible({ timeout: 30_000 });
  await waitForMilestone(startedAt, 408_000);

  await humanClick(page, page.getByRole("link", { name: "Complaint Workspace" }));
  await expect(page.getByTestId("complaint-workspace")).toBeVisible({ timeout: 30_000 });
  await openQualityDock(page);
  await humanClick(page, page.getByRole("tab", { name: "Evidence & Audit" }));
  await expect(page.getByTestId("inspector-replay")).toBeVisible({ timeout: 30_000 });
  const previewButton = page.getByRole("button", { name: "Preview Inspection Brief" });
  if (await previewButton.isEnabled().catch(() => false)) {
    await humanClick(page, previewButton);
    await expect(page.getByRole("dialog", { name: "Inspection Brief Preview" })).toBeVisible({ timeout: 30_000 });
    await waitForDemoPause(2_000);
    await humanClick(page, page.getByRole("button", { name: "Close drawer" }).last());
  }
  const downloadButton = page.getByRole("button", { name: "Download PDF" });
  if (await downloadButton.isEnabled().catch(() => false)) {
    const downloadPromise = page.waitForEvent("download").catch(() => null);
    await humanClick(page, downloadButton);
    const download = await downloadPromise;
    if (download) {
      await download.cancel().catch(() => undefined);
    }
  }
  const copyButton = page.getByRole("button", { name: "Copy Complaint Summary" });
  if (await copyButton.isEnabled().catch(() => false)) {
    await humanClick(page, copyButton);
  }
  await waitForMilestone(startedAt, targetDurationMs);

  await page.close();
  await context.close();

  if (!isDryRun && video) {
    const rawVideoPath = await video.path();
    await fs.copyFile(rawVideoPath, finalWebmPath);
  }
});
