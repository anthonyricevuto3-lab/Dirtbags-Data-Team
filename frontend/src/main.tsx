import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
type Player = { id: number; name: string };
type Outing = {
  id: number;
  played_on: string;
  opponent: string;
  pitch_count: number;
};
type Arsenal = {
  pitch_type: string;
  count: number;
  usage_pct: number;
  velocity: number | null;
  velocity_samples: number;
  ivb: number | null;
  hb: number | null;
  whiff_pct: number | null;
};
type Detail = Outing & {
  name: string;
  arsenal: Arsenal[];
  locations: {
    pitch_number: number;
    pitch_type: string;
    plate_x: number | null;
    plate_z: number | null;
  }[];
};
async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, options);
  const body = await response.json();
  if (!response.ok)
    throw new Error(body.error || "Request failed. Please try again.");
  return body;
}
const fmt = (n: number | null) => (n === null ? "—" : n.toFixed(1));
const colors = ["#e4b64b", "#61b5b0", "#bc96db", "#ec927b", "#8fb66f"];
function App() {
  const [players, setPlayers] = useState<Player[]>([]),
    [player, setPlayer] = useState("");
  const [outings, setOutings] = useState<Outing[]>([]),
    [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(false);
  const [revision, setRevision] = useState(0);
  const sequence = useRef(0);
  useEffect(() => {
    let active = true;
    api<Player[]>("/api/players")
      .then((p) => {
        if (active) setPlayers(p);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [revision]);
  useEffect(() => {
    let active = true;
    sequence.current++;
    setDetail(null);
    setOutings([]);
    setLoading(false);
    if (player)
      api<Outing[]>(`/api/players/${player}/outings`)
        .then((o) => {
          if (active) setOutings(o);
        })
        .catch((e) => {
          if (active) setError(e.message);
        });
    return () => {
      active = false;
    };
  }, [player, revision]);
  async function show(id: number) {
    const ticket = ++sequence.current;
    setError("");
    setDetail(null);
    setLoading(true);
    try {
      const data = await api<Detail>(`/api/outings/${id}`);
      if (ticket === sequence.current) setDetail(data);
    } catch (e) {
      if (ticket === sequence.current) setError((e as Error).message);
    } finally {
      if (ticket === sequence.current) setLoading(false);
    }
  }
  async function upload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await api<{
        inserted: number;
        skipped: number;
        warnings: string[];
      }>("/api/imports", {
        method: "POST",
        body: new FormData(event.currentTarget),
      });
      setNotice(
        `${result.inserted} pitches imported · ${result.skipped} already present. ${result.warnings.join(" ")}`,
      );
      setRevision((r) => r + 1);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="shell">
      <header>
        <div className="brand">
          D<span>/</span>D
        </div>
        <div>
          <p className="eyebrow">DIRTBAGS DATA TEAM</p>
          <h1>Player development</h1>
        </div>
        <span className="badge">LOCAL WORKSPACE</span>
      </header>
      <p className="intro">
        From the outing to the next conversation. Import tracking data and
        review a pitcher’s arsenal.
      </p>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="notice" role="status">
          {notice}
        </div>
      )}
      <div className="layout">
        <aside>
          <section>
            <p className="eyebrow">01 / IMPORT</p>
            <h2>Add an outing</h2>
            <form onSubmit={upload}>
              <label>
                Game ID
                <input
                  name="game_id"
                  placeholder="2026-10-31-demo-game1"
                  required
                  maxLength={200}
                />
              </label>
              <p className="hint">
                Use the same ID for every file from this game. Doubleheaders
                need separate IDs.
              </p>
              <label>
                Game date
                <input type="date" name="played_on" required />
              </label>
              <label>
                Opponent
                <input
                  name="opponent"
                  placeholder="Demo opponent"
                  required
                  maxLength={200}
                />
              </label>
              <label>
                TrackMan CSV
                <input name="file" type="file" accept=".csv" required />
              </label>
              <p className="hint">
                10 MB maximum. Duplicate pitches are skipped; conflicting
                records require review.
              </p>
              <button disabled={busy} className="primary">
                {busy ? "Importing…" : "Import outing →"}
              </button>
            </form>
          </section>
          <section>
            <p className="eyebrow">02 / SELECT</p>
            <label>
              Pitcher
              <select
                value={player}
                onChange={(e) => setPlayer(e.target.value)}
              >
                <option value="">Select a pitcher</option>
                {players.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="outing-list">
              {outings.map((o) => (
                <button
                  key={o.id}
                  className={detail?.id === o.id ? "outing active" : "outing"}
                  onClick={() => show(o.id)}
                >
                  <strong>{o.played_on}</strong>
                  <span>vs {o.opponent}</span>
                  <small>{o.pitch_count} pitches</small>
                </button>
              ))}
            </div>
            {player && !outings.length && (
              <p className="hint">No outings available.</p>
            )}
          </section>
        </aside>
        <main>
          {!detail ? (
            <div className="empty">
              <div className="diamond">◇</div>
              <p className="eyebrow">OUTING REVIEW</p>
              <h2>
                {loading ? "Loading outing…" : "Every pitch has a story."}
              </h2>
              <p>
                Import a CSV, choose a pitcher, then select an outing to explore
                the data.
              </p>
              <p className="hint">
                Try the synthetic CSV in tests/fixtures to explore without team
                data.
              </p>
            </div>
          ) : (
            <>
              <div className="title-row">
                <div>
                  <p className="eyebrow">OUTING REVIEW / {detail.played_on}</p>
                  <h2>{detail.name}</h2>
                  <p>vs {detail.opponent}</p>
                </div>
                <div className="stat">
                  <strong>{detail.pitch_count}</strong>
                  <span>PITCHES</span>
                </div>
              </div>
              <section>
                <h3>Pitch arsenal</h3>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        {[
                          "Pitch",
                          "Count",
                          "Usage %",
                          "Velo mph",
                          "Velo N",
                          "IVB in",
                          "HB in",
                          "Whiff %",
                        ].map((h) => (
                          <th key={h}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {detail.arsenal.map((a, i) => (
                        <tr key={a.pitch_type}>
                          <td>
                            <i
                              style={{ background: colors[i % colors.length] }}
                            />
                            {a.pitch_type}
                          </td>
                          <td>{a.count}</td>
                          <td>{fmt(a.usage_pct)}</td>
                          <td>{fmt(a.velocity)}</td>
                          <td>{a.velocity_samples}</td>
                          <td>{fmt(a.ivb)}</td>
                          <td>{fmt(a.hb)}</td>
                          <td>{fmt(a.whiff_pct)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="hint">
                  Whiff % = swinging strikes ÷ swings. — means no swings or an
                  unknown pitch call. Missing measurements are excluded from
                  averages.
                </p>
              </section>
              <section>
                <h3>Pitch locations</h3>
                <p className="hint">
                  Catcher’s perspective · inches · fixed reference zone, not a
                  called-strike judgment
                </p>
                <svg
                  viewBox="0 0 480 360"
                  role="img"
                  aria-label="Pitch locations with a reference strike zone"
                  className="chart"
                >
                  <rect
                    x={189}
                    y={75}
                    width={102}
                    height={144}
                    fill="none"
                    stroke="#788b91"
                    strokeDasharray="5 5"
                  />
                  <line x1={240} y1={20} x2={240} y2={320} stroke="#243b43" />
                  {detail.locations
                    .filter((p) => p.plate_x !== null && p.plate_z !== null)
                    .map((p) => (
                      <circle
                        key={p.pitch_number}
                        cx={240 + p.plate_x! * 6}
                        cy={327 - p.plate_z! * 6}
                        r={5}
                        fill={
                          colors[
                            detail.arsenal.findIndex(
                              (a) => a.pitch_type === p.pitch_type,
                            ) % colors.length
                          ]
                        }
                      >
                        <title>
                          Pitch {p.pitch_number}: {p.pitch_type},{" "}
                          {fmt(p.plate_x)} in horizontal / {fmt(p.plate_z)} in
                          high
                        </title>
                      </circle>
                    ))}
                  <text x={10} y={350} fill="#9cafb5">
                    Reference: ±8.5 in wide; 18–42 in high
                  </text>
                </svg>
                <p className="hint">
                  {
                    detail.locations.filter(
                      (p) => p.plate_x === null || p.plate_z === null,
                    ).length
                  }{" "}
                  pitches missing location. Extreme locations may fall outside
                  the plot.
                </p>
              </section>
            </>
          )}
        </main>
      </div>
      <footer>
        Built for coaching conversations. Milestone 1 · imports & outing review
      </footer>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
