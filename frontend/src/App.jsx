import { useCallback, useEffect, useState } from "react";
import { forceTubeBin, getBoard, refreshSimulation, tubeBin } from "./api";

function formatDueTime(value) {
  if (!value) return "Not scheduled";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function MedicationRow({ medication, needsTubing }) {
  return (
    <li className={`medication-row ${needsTubing ? "needs-tubing" : ""}`}>
      <div className="medication-heading">
        <div>
          <strong>{medication.medication_name}</strong>
          {needsTubing && <strong className="tube-now-label">TUBE NOW</strong>}
        </div>
        <span className={medication.status.toUpperCase() === "STAT" ? "status stat" : "status"}>{medication.status}</span>
      </div>
      <dl>
        <div><dt>Order</dt><dd>{medication.order_number}</dd></div>
        <div><dt>Due</dt><dd>{formatDueTime(medication.due_time)}</dd></div>
        <div><dt>Room</dt><dd>{medication.room || "—"}</dd></div>
        <div><dt>Route</dt><dd>{medication.route}</dd></div>
        <div><dt>Medication priority</dt><dd>{medication.priority_score}</dd></div>
      </dl>
    </li>
  );
}

function BinCard({ bin, tubingBin, onTube, priorityStrength, boardBusy }) {
  const ready = bin.ready_to_tube;
  const isTubing = tubingBin === bin.bin_number;
  const queuePriority = bin.queue_priority_score ?? bin.priority_score;

  return (
    <article
      className={`bin-card ${ready ? "is-ready" : ""}`}
      style={{ "--priority-strength": priorityStrength }}
    >
      <header className="bin-header">
        <div>
          <p className="eyebrow">{bin.bin_id}</p>
          <h2>{bin.bin_name}</h2>
        </div>
        <span className={ready ? "tubing-state ready" : "tubing-state"}>
          {ready ? "Ready to tube" : "Pending"}
        </span>
      </header>

      <div className="bin-metrics">
        <div><span>Medication count</span><strong>{bin.medication_count}</strong></div>
        <div><span>Bin priority</span><strong>{queuePriority}</strong></div>
      </div>

      {bin.medications.length ? (
        <ul className="medication-list">
          {bin.medications.map((medication) => (
            <MedicationRow
              key={medication.order_number}
              medication={medication}
              needsTubing={medication.ready_to_tube}
            />
          ))}
        </ul>
      ) : <p className="empty-state">No pending medications.</p>}

      <button
        type="button"
        className="tube-button"
        disabled={!bin.medication_count || tubingBin !== null || boardBusy}
        onClick={() => onTube(bin.bin_number)}
        title={ready ? "Tube currently eligible medications" : "Manual override: tube all pending medications in this bin"}
      >
        {isTubing ? "TUBING…" : "TUBE"}
      </button>
    </article>
  );
}

function TransferNotifications({ transfers }) {
  if (!transfers.length) return null;

  return (
    <section className="transfer-notifications" aria-live="polite">
      <div>
        <p className="eyebrow">Transfer check</p>
        <h2>Medication transfers detected</h2>
      </div>
      <ul>
        {transfers.map((transfer) => (
          <li key={`${transfer.order_number}-${transfer.old_room}-${transfer.new_room}`}>
            <strong>{transfer.medication_name}</strong> <span>· Order {transfer.order_number}</span>
            <p>Room {transfer.old_room} → Room {transfer.new_room} · Bin {transfer.old_bin} → Bin {transfer.new_bin ?? "UNKNOWN"}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function TubedMedications({ medications }) {
  return (
    <section className="tubed-section" aria-label="Tubed medications">
      <div>
        <p className="eyebrow">Confirmed backend history</p>
        <h2>Tubed Medications</h2>
      </div>
      {medications.length ? (
        <ul className="tubed-medication-list">
          {medications.map((medication) => (
            <li key={medication.order_number}>
              <div className="medication-heading">
                <strong>{medication.medication_name}</strong>
                <span className="tubing-state ready">{medication.tubing_status}</span>
              </div>
              <dl>
                <div><dt>Order</dt><dd>{medication.order_number}</dd></div>
                <div><dt>Room</dt><dd>{medication.room || "-"}</dd></div>
                <div><dt>Unit</dt><dd>{medication.unit || "-"}</dd></div>
                <div><dt>Route</dt><dd>{medication.route}</dd></div>
                <div><dt>Due</dt><dd>{formatDueTime(medication.due_time)}</dd></div>
                <div><dt>Status</dt><dd>{medication.clinical_status}</dd></div>
              </dl>
            </li>
          ))}
        </ul>
      ) : <p className="empty-state">No medications have been tubed in this session.</p>}
    </section>
  );
}

export default function App() {
  const [board, setBoard] = useState(null);
  const [transfers, setTransfers] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [tubingBin, setTubingBin] = useState(null);

  const loadBoard = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await getBoard();
      setBoard(response);
      setTransfers(response.detected_transfers || []);
    } catch (requestError) {
      setError(requestError.message || "Unable to load the tubing board.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadBoard(); }, [loadBoard]);

  async function handleTube(binNumber) {
    setTubingBin(binNumber);
    setError("");
    try {
      const selectedBin = [...board.bins, board.unknown_bin].find((bin) => bin.bin_number === String(binNumber));
      const response = selectedBin?.ready_to_tube ? await tubeBin(binNumber) : await forceTubeBin(binNumber);
      setBoard(response);
      setTransfers(response.detected_transfers || []);
    } catch (requestError) {
      setError(requestError.message || `Unable to tube Bin ${binNumber}.`);
    } finally {
      setTubingBin(null);
    }
  }

  async function handleRefreshSimulation() {
    setRefreshing(true);
    setError("");
    try {
      const response = await refreshSimulation();
      setBoard(response);
      setTransfers(response.detected_transfers || []);
    } catch (requestError) {
      setError(requestError.message || "Unable to generate a new medication batch.");
    } finally {
      setRefreshing(false);
    }
  }

  if (loading && !board) {
    return <main className="app-shell"><p className="loading">Loading tubing board…</p></main>;
  }

  const allBins = [...board.bins, board.unknown_bin];
  const highestReadyPriority = Math.max(
    1,
    ...allBins.filter((bin) => bin.ready_to_tube).map((bin) => bin.priority_score),
  );
  const getPriorityStrength = (bin) => (
    bin.ready_to_tube ? Math.max(0, bin.priority_score / highestReadyPriority) : 0
  );

  return (
    <main className="app-shell">
      <header className="page-header">
        <div>
          <p className="eyebrow">Pharmacy operations</p>
          <h1>MediTube Tubing Board</h1>
          <p className="subtitle">Live queue state from the tubing backend.</p>
        </div>
        <button type="button" className="refresh-button" onClick={handleRefreshSimulation} disabled={loading || refreshing || tubingBin !== null}>
          {refreshing ? "Generating…" : "Refresh board"}
        </button>
      </header>

      {error && <p className="error-message" role="alert">{error}</p>}
      <TransferNotifications transfers={transfers} />

      {board && (
        <>
          <section className="bin-grid" aria-label="Standard tubing bins">
            {board.bins.map((bin) => (
              <BinCard
                key={bin.bin_id}
                bin={bin}
                tubingBin={tubingBin}
                onTube={handleTube}
                priorityStrength={getPriorityStrength(bin)}
                boardBusy={refreshing}
              />
            ))}
          </section>
          <section className="unknown-section" aria-label="Unknown destination bin">
            <div><p className="eyebrow">Separate handling queue</p><h2>UNKNOWN</h2></div>
            <BinCard
              bin={board.unknown_bin}
              tubingBin={tubingBin}
              onTube={handleTube}
              priorityStrength={getPriorityStrength(board.unknown_bin)}
              boardBusy={refreshing}
            />
          </section>
          <TubedMedications medications={board.tubed_medications || []} />
        </>
      )}
    </main>
  );
}
