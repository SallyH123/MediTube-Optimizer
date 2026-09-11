import { useCallback, useEffect, useState } from "react";
import { forceTubeBin, getBoard, refreshSimulation, tubeBin } from "./api";

function formatDueTime(value) {
  if (!value) return "Not scheduled";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function formatBin(bin) {
  if (!bin) return "UNKNOWN";
  if (String(bin).startsWith("BIN_")) return bin;

  const binNames = {
    1: "BIN_CVICU", 2: "BIN_SICU", 3: "BIN_MICU", 4: "BIN_4", 5: "BIN_5",
    6: "BIN_6", 7: "BIN_7", 8: "BIN_ED", 9: "BIN_PERIOP",
  };
  return binNames[bin] ?? `BIN_${bin}`;
}

function MedicationRow({ medication, needsTubing, transfer }) {
  return (
    <li className={`medication-row ${needsTubing ? "needs-tubing" : ""} ${transfer ? "has-transfer" : ""}`}>
      <div className="medication-heading">
        <div>
          <strong>{medication.medication_name}</strong>
          {needsTubing && <strong className="tube-now-label">TUBE NOW</strong>}
        </div>
        <span className={medication.status.toUpperCase() === "STAT" ? "status stat" : "status"}>{medication.status}</span>
      </div>
      {transfer && (
        <div className="medication-transfer" role="status">
          {(transfer.old_room || transfer.new_room) && (
            <p><strong>Patient transferred:</strong> Room {transfer.old_room ?? "Unknown"} &rarr; Room {transfer.new_room ?? "Unknown"}</p>
          )}
          <p><strong>Move {medication.medication_name}:</strong> {formatBin(transfer.old_bin)} &rarr; {formatBin(transfer.new_bin)}</p>
        </div>
      )}
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

function BinCard({ bin, tubingBin, onTube, priorityStrength, boardBusy, transfersByOrder }) {
  const ready = bin.ready_to_tube;
  const isTubing = tubingBin === bin.bin_number;
  const queuePriority = bin.queue_priority_score ?? bin.priority_score;
  const medicationsByTubingStatus = [...bin.medications].sort(
    (left, right) => Number(right.ready_to_tube) - Number(left.ready_to_tube),
  );

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
          {medicationsByTubingStatus.map((medication) => (
            <MedicationRow
              key={medication.order_number}
              medication={medication}
              needsTubing={medication.ready_to_tube}
              transfer={transfersByOrder.get(medication.order_number)}
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
  return (
    <section className="transfer-notifications" aria-live="polite">
      <div>
        <p className="eyebrow">Transfer check</p>
        <h2>{transfers.length ? "Medication transfers detected" : "Patient transfer status"}</h2>
      </div>
      {transfers.length ? (
        <ul>
          {transfers.map((transfer) => (
            <li key={`${transfer.order_number}-${transfer.old_room}-${transfer.new_room}`}>
              <p className="transfer-rooms"><strong>Patient transferred:</strong> Room {transfer.old_room ?? "Unknown"} &rarr; Room {transfer.new_room ?? "Unknown"}</p>
              <p className="transfer-move"><strong>Move {transfer.medication_name}:</strong> {formatBin(transfer.old_bin)} &rarr; {formatBin(transfer.new_bin)}</p>
              <span>Order {transfer.order_number}</span>
            </li>
          ))}
        </ul>
      ) : <p className="no-transfers">No patient transfers detected in the current queue.</p>}
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
  const isDemo = window.location.pathname.startsWith("/cutoff-demo");
  const demoTime = new URLSearchParams(window.location.search).get("time") === "2030" ? "2030" : "2000";
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
  const transfersByOrder = new Map(transfers.map((transfer) => [transfer.order_number, transfer]));

  return (
    <main className="app-shell">
      <header className="page-header">
        <div>
          <p className="eyebrow">{isDemo ? `Demo scenario · simulated time ${demoTime === "2030" ? "20:30" : "20:00"}` : "Pharmacy operations"}</p>
          <h1>{isDemo ? "MediTube Demo Board" : "MediTube Tubing Board"}</h1>
          <p className="subtitle">{isDemo ? "Ten fixed medication cases for cutoff and transfer review." : "Live queue state from the tubing backend."}</p>
        </div>
        <div className="header-actions">
          {isDemo ? (
            <>
              <a className={demoTime === "2000" ? "demo-time-button active" : "demo-time-button"} href="/cutoff-demo?time=2000">8:00 PM</a>
              <a className={demoTime === "2030" ? "demo-time-button active" : "demo-time-button"} href="/cutoff-demo?time=2030">8:30 PM</a>
              <a className="refresh-button" href="/">Back to live board</a>
            </>
          ) : (
            <>
              <a className="demo-button" href="/cutoff-demo">Open demo</a>
              <button type="button" className="refresh-button" onClick={handleRefreshSimulation} disabled={loading || refreshing || tubingBin !== null}>
                {refreshing ? "Generating…" : "Refresh board"}
              </button>
            </>
          )}
        </div>
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
                transfersByOrder={transfersByOrder}
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
              transfersByOrder={transfersByOrder}
            />
          </section>
          <TubedMedications medications={board.tubed_medications || []} />
        </>
      )}
    </main>
  );
}
