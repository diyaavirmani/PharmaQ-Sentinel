import { useState } from "react";
import { ConfirmationModal } from "../../components/common/ConfirmationModal";
import type { ContainmentSimulationRequest, ContainmentSimulationResponse } from "./batchImpactTypes";

interface ContainmentSimulatorModalProps {
  isOpen: boolean;
  isSimulating: boolean;
  result: ContainmentSimulationResponse | null;
  onCancel: () => void;
  onSimulate: (request: ContainmentSimulationRequest) => void;
}

export function ContainmentSimulatorModal({
  isOpen,
  isSimulating,
  result,
  onCancel,
  onSimulate
}: ContainmentSimulatorModalProps) {
  const [includePrimary, setIncludePrimary] = useState(true);
  const [includePackaging, setIncludePackaging] = useState(true);
  const [includeMaterial, setIncludeMaterial] = useState(false);
  const [includeEquipment, setIncludeEquipment] = useState(false);
  const [windowDays, setWindowDays] = useState(7);

  function handleSimulate() {
    onSimulate({
      include_primary_batch: includePrimary,
      include_shared_packaging_lot: includePackaging,
      include_shared_material_lot: includeMaterial,
      include_shared_equipment: includeEquipment,
      equipment_date_window_days: windowDays
    });
  }

  return (
    <ConfirmationModal
      title="Containment Scope Simulation"
      message="SIMULATION ONLY - No batch, inventory or shipment status will be changed."
      isOpen={isOpen}
      confirmLabel="Run Simulation"
      cancelLabel="Close"
      isProcessing={isSimulating}
      onConfirm={handleSimulate}
      onCancel={onCancel}
    >
      <div className="containment-simulator">
        <label>
          <input
            type="checkbox"
            checked={includePrimary}
            onChange={(event) => setIncludePrimary(event.target.checked)}
          />
          Include primary batch
        </label>
        <label>
          <input
            type="checkbox"
            checked={includePackaging}
            onChange={(event) => setIncludePackaging(event.target.checked)}
          />
          Include shared packaging lot
        </label>
        <label>
          <input
            type="checkbox"
            checked={includeMaterial}
            onChange={(event) => setIncludeMaterial(event.target.checked)}
          />
          Include shared material lot
        </label>
        <label>
          <input
            type="checkbox"
            checked={includeEquipment}
            onChange={(event) => setIncludeEquipment(event.target.checked)}
          />
          Include shared equipment
        </label>
        <label>
          Equipment date window
          <input
            type="number"
            min={0}
            max={90}
            value={windowDays}
            onChange={(event) => setWindowDays(Number(event.target.value))}
          />
        </label>
        {result ? (
          <div className="containment-result" data-testid="containment-simulation-result">
            <strong>Simulated Scope</strong>
            <ul>
              {result.batches_included.map((batch) => (
                <li key={batch.batch_number}>
                  {batch.batch_number}: {batch.inclusion_reasons.join(" ")}
                </li>
              ))}
            </ul>
            <p>Inventory potentially assessed: {result.internal_inventory_potentially_assessed}</p>
            <p>Distributed quantity: {result.distributed_quantity}</p>
            <p>{result.possible_supply_impact}</p>
          </div>
        ) : null}
      </div>
    </ConfirmationModal>
  );
}
