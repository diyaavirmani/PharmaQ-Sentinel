import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

const batchImpactResponse = {
  run_id: "screenshot-batch-impact-run",
  nodes: [
    { id: "complaint-1", type: "complaint", label: "Complaint: blister leakage", subtitle: "Demo complaint", status: "Draft", severity: "Major", evidence_record_id: "complaint-1", metadata: { demo_record: true }, position_hint: "center" },
    { id: "product-amox", type: "product", label: "Amoxicillin Capsules", subtitle: "500 mg", status: "Active", severity: null, evidence_record_id: "product-amox", metadata: { product_code: "AMX-CAP-500" }, position_hint: "upstream" },
    { id: "batch-bmx240602", type: "batch", label: "BMX240602", subtitle: "Primary batch", status: "Released", severity: "Major", evidence_record_id: "batch-bmx240602", metadata: { quantity_released: "50000.000" }, position_hint: "center" },
    { id: "batch-bmx240603", type: "batch", label: "BMX240603", subtitle: "Shared packaging line", status: "Released", severity: null, evidence_record_id: "batch-bmx240603", metadata: { quantity_released: "52000.000" }, position_hint: "related" },
    { id: "pkg-pl-04", type: "packaging_material_lot", label: "Foil Lot PL-04-F-778", subtitle: "Shared packaging lot", status: "Released", severity: "Elevated", evidence_record_id: "pkg-pl-04", metadata: { supplier: "Demo Pack Supplier" }, position_hint: "upstream" },
    { id: "equipment-sealer-04", type: "equipment", label: "Blister Sealer PL-04", subtitle: "Packaging line equipment", status: "Qualified", severity: null, evidence_record_id: "equipment-sealer-04", metadata: { line: "PL-04" }, position_hint: "process" },
    { id: "deviation-dev-2026-023", type: "deviation", label: "DEV-2026-023", subtitle: "Seal temperature excursion", status: "Open", severity: "Major", evidence_record_id: "deviation-dev-2026-023", metadata: { demo_record: true }, position_hint: "quality" },
    { id: "capa-2026-011", type: "capa", label: "CAPA-2026-011", subtitle: "Review sealer controls", status: "Open", severity: null, evidence_record_id: "capa-2026-011", metadata: { effectiveness_status: "Pending" }, position_hint: "quality" },
    { id: "historical-hc-001", type: "historical_complaint", label: "HC-2026-014", subtitle: "Blister leakage", status: "Closed", severity: "Major", evidence_record_id: "historical-hc-001", metadata: { complaint_date: "2026-06-19" }, position_hint: "quality" },
    { id: "distribution-delhi", type: "distribution_location", label: "Delhi", subtitle: "18,000 units distributed", status: "Shipped", severity: null, evidence_record_id: "distribution-delhi", metadata: { market_city: "Delhi" }, position_hint: "downstream" },
    { id: "inventory-wh-01", type: "warehouse_inventory", label: "Central Warehouse", subtitle: "51,000 units available", status: "Available", severity: null, evidence_record_id: "inventory-wh-01", metadata: { warehouse: "Central Warehouse" }, position_hint: "downstream" }
  ],
  edges: [
    { id: "edge-complaint-batch", source: "complaint-1", target: "batch-bmx240602", type: "complaint_involves_batch", relationship_label: "Involves batch", source_record_ids: ["complaint-1", "batch-bmx240602"], why_connected: "The complaint draft references batch BMX240602.", limitation: "Batch reference supports scope review only; it is not final impact determination.", confidence: "0.9100" },
    { id: "edge-product-batch", source: "product-amox", target: "batch-bmx240602", type: "product_has_batch", relationship_label: "Product batch", source_record_ids: ["product-amox", "batch-bmx240602"], why_connected: "The batch is linked to the same demonstration product record.", limitation: "Seeded records are fictional and for demonstration only.", confidence: "0.9600" },
    { id: "edge-batch-packaging", source: "batch-bmx240602", target: "pkg-pl-04", type: "used_packaging_lot", relationship_label: "Used packaging lot", source_record_ids: ["batch-bmx240602", "pkg-pl-04"], why_connected: "The batch record lists this packaging material lot.", limitation: "Shared material use suggests review scope only.", confidence: "0.8800" },
    { id: "edge-batch-equipment", source: "batch-bmx240602", target: "equipment-sealer-04", type: "used_equipment", relationship_label: "Used equipment", source_record_ids: ["batch-bmx240602", "equipment-sealer-04"], why_connected: "The batch was packaged on equipment from line PL-04.", limitation: "Equipment relationship does not establish root cause.", confidence: "0.8400" },
    { id: "edge-batch-deviation", source: "batch-bmx240602", target: "deviation-dev-2026-023", type: "has_deviation", relationship_label: "Has deviation", source_record_ids: ["batch-bmx240602", "deviation-dev-2026-023"], why_connected: "The demo deviation references seal temperature on the linked packaging line.", limitation: "Deviation linkage requires QA review before any conclusion.", confidence: "0.8200" },
    { id: "edge-deviation-capa", source: "deviation-dev-2026-023", target: "capa-2026-011", type: "linked_capa", relationship_label: "Linked CAPA", source_record_ids: ["deviation-dev-2026-023", "capa-2026-011"], why_connected: "The CAPA is linked to the open deviation.", limitation: "CAPA status is contextual and not a complaint decision.", confidence: "0.8000" },
    { id: "edge-batch-distribution", source: "batch-bmx240602", target: "distribution-delhi", type: "distributed_to", relationship_label: "Distributed to market", source_record_ids: ["batch-bmx240602", "distribution-delhi"], why_connected: "Distribution records show released quantity for this batch.", limitation: "Distribution scope requires authorized confirmation.", confidence: "0.9000" }
  ],
  signals: [
    { name: "Open deviation on linked line or equipment", category: "deviation", level: "HIGH", explanation: "Open deviation DEV-2026-023 should be reviewed before QA disposition.", evidence_record_ids: ["deviation-dev-2026-023", "equipment-sealer-04"], confidence: "0.8200", recommended_assessment: "Review deviation and linked CAPA before complaint disposition.", limitation: "Deviation linkage does not establish final root cause." },
    { name: "Shared packaging material lot", category: "packaging", level: "ELEVATED", explanation: "Primary and related batches share a packaging lot.", evidence_record_ids: ["pkg-pl-04", "batch-bmx240603"], confidence: "0.7800", recommended_assessment: "Compare retained samples from batches using the same packaging lot.", limitation: "Shared lot means possible review scope only." },
    { name: "Similar historical complaint", category: "historical", level: "ELEVATED", explanation: "One historical blister leakage complaint exists in the demo context.", evidence_record_ids: ["historical-hc-001"], confidence: "0.7100", recommended_assessment: "Review historical complaint narrative and closure rationale.", limitation: "Historical similarity is not recurrence confirmation." },
    { name: "Distributed inventory exposure", category: "distribution", level: "WATCH", explanation: "Distributed and warehouse records define possible assessment scope.", evidence_record_ids: ["distribution-delhi", "inventory-wh-01"], confidence: "0.7600", recommended_assessment: "Confirm shipment status and remaining inventory quantities.", limitation: "Scope must be confirmed by authorized QA records." },
    { name: "Supplier context available", category: "supplier", level: "INFO", explanation: "Supplier data is available for material review.", evidence_record_ids: ["pkg-pl-04"], confidence: "0.6600", recommended_assessment: "Review supplier qualification only if QA requests packaging material assessment.", limitation: "Supplier context alone is not a quality signal." }
  ],
  impact_summary: {
    primary_batch: "BMX240602",
    related_batches: ["BMX240603", "BMX240604"],
    similar_complaint_count: 1,
    open_deviations: 1,
    linked_capas: 1,
    distributed_quantity: "49500.000",
    markets_or_locations: ["Delhi", "Mumbai", "Jaipur"],
    remaining_inventory: "51000.000",
    suppliers_involved: ["Demo Pack Supplier"],
    elevated_recurrence_signal: true,
    overall_investigation_priority: "HIGH",
    data_limitations: ["Connected records indicate assessment scope; they do not establish final quality impact or root cause."]
  },
  recommended_assessments: [
    { title: "Review open deviation DEV-2026-023", rationale: "The open deviation is connected to the linked packaging line.", evidence_record_ids: ["deviation-dev-2026-023"], limitation: "Requires authorized QA interpretation." },
    { title: "Compare retained samples", rationale: "Shared packaging lot may define comparison batches.", evidence_record_ids: ["pkg-pl-04", "batch-bmx240603"], limitation: "Comparison does not imply impact." },
    { title: "Confirm distribution and inventory", rationale: "Downstream records define potential assessment scope.", evidence_record_ids: ["distribution-delhi", "inventory-wh-01"], limitation: "Quantities require QA confirmation." },
    { title: "Review historical complaint closure", rationale: "Prior blister leakage record may inform investigation planning.", evidence_record_ids: ["historical-hc-001"], limitation: "Historical similarity is contextual." }
  ],
  limitations: ["Seeded pharmaceutical records are fictional demonstration data.", "Connected records indicate assessment scope; they do not establish final quality impact or root cause."]
};

async function openBatchIntelligence(page: Page) {
  await page.route("**/api/v1/complaint-drafts/*/batch-impact", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(batchImpactResponse) });
  });
  await page.goto("/workspace?state=populated");
  await expect(page.getByTestId("quality-intelligence-dock")).toBeVisible();
  await page.getByRole("button", { name: "Quality Intelligence" }).click();
  await page.getByRole("tab", { name: "Batch Intelligence" }).click();
  await page.getByRole("button", { name: "Run Analysis" }).click();
  await expect(page.getByTestId("batch-impact-overview")).toBeVisible();
}

test("batch intelligence overview screenshot", async ({ page }) => {
  await openBatchIntelligence(page);
  await page.screenshot({ path: "test-results/screenshots/batch-intelligence-overview.png", fullPage: true });
});

test("batch intelligence summary map screenshot", async ({ page }) => {
  await openBatchIntelligence(page);
  await page.getByRole("tab", { name: "Relationship Map" }).click();
  await expect(page.getByTestId("batch-impact-graph")).toBeVisible();
  await expect(page.getByRole("button", { name: "Summary View" })).toHaveAttribute("aria-pressed", "true");
  await page.screenshot({ path: "test-results/screenshots/batch-intelligence-map-summary.png", fullPage: true });
});

test("batch intelligence all records map screenshot", async ({ page }) => {
  await openBatchIntelligence(page);
  await page.getByRole("tab", { name: "Relationship Map" }).click();
  await page.getByRole("button", { name: "All Records" }).click();
  await expect(page.getByText("DEV-2026-023")).toBeVisible();
  await page.screenshot({ path: "test-results/screenshots/batch-intelligence-map-all-records.png", fullPage: true });
});

test("batch intelligence details and limitations screenshot", async ({ page }) => {
  await openBatchIntelligence(page);
  await page.getByRole("tab", { name: "Details & Limitations" }).click();
  await expect(page.getByTestId("batch-impact-details-view")).toBeVisible();
  await page.screenshot({ path: "test-results/screenshots/batch-intelligence-details-limitations.png", fullPage: true });
});