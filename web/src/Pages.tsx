import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowDownToLine,
  ArrowRight,
  BookOpen,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Database,
  Fingerprint,
  Layers3,
  RotateCcw,
  ShieldCheck,
} from 'lucide-react';
import { api, date, percent } from './api';
import type { Benchmark, Inspection, Model, OperatingPoint } from './types';

export function BenchmarkPage({
  report,
  model,
  error,
}: {
  report?: Benchmark;
  model: Model;
  error?: string;
}) {
  const [override, setOverride] = useState<number | null>(null);
  const threshold = override ?? model.calibration.threshold;
  if (!report)
    return (
      <div className="empty-state">
        <h1>Model performance</h1>
        <p>{error || 'Loading the benchmark…'}</p>
      </div>
    );
  const outcome = { tp: 0, fp: 0, tn: 0, fn: 0 };
  report.samples.forEach((sample) => {
    const flagged = sample.score > threshold;
    outcome[sample.anomalous ? (flagged ? 'tp' : 'fn') : flagged ? 'fp' : 'tn']++;
  });
  const minimum = Math.floor(Math.min(...report.samples.map((s) => s.score)) * 0.8 * 200) / 200;
  const maximum = Math.ceil(Math.max(...report.samples.map((s) => s.score)) * 1.05 * 200) / 200;
  const recall = outcome.tp / (outcome.tp + outcome.fn);
  const fpr = outcome.fp / (outcome.fp + outcome.tn);
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <span /> VALIDATION / HELD-OUT EVIDENCE
          </div>
          <h1>
            Measure what matters<span className="orange">.</span>
          </h1>
          <p>One category. A fixed split. Every prediction available for inspection.</p>
        </div>
        <a className="button secondary" href="/api/benchmark" download="forgesight-benchmark.json">
          <ArrowDownToLine size={15} />
          Export metrics
        </a>
      </div>
      <div className="split-banner">
        <div>
          <span className="step-number">01</span>
          <span>
            <strong>{model.fit_count} normal images</strong>
            <small>Fit feature memory</small>
          </span>
        </div>
        <ArrowRight size={17} />
        <div>
          <span className="step-number">02</span>
          <span>
            <strong>{model.calibration.count} normal images</strong>
            <small>Calibrate alert threshold</small>
          </span>
        </div>
        <ArrowRight size={17} />
        <div>
          <span className="step-number">03</span>
          <span>
            <strong>{report.test_count} test images</strong>
            <small>
              {report.normal_count} normal · {report.defect_count} defective
            </small>
          </span>
        </div>
        <span className="split-badge">
          <ShieldCheck size={14} /> Disjoint splits
        </span>
      </div>
      <div className="stat-grid">
        <Stat
          label="IMAGE AUROC"
          value={percent(report.image_auroc)}
          sub={`95% bootstrap interval ${percent(report.image_auroc_ci95.low)} – ${percent(report.image_auroc_ci95.high)}`}
        />
        <Stat
          label="PIXEL AUROC"
          value={percent(report.pixel_auroc)}
          sub="Localization at 224 × 224 resolution"
        />
        <Stat
          label="PIXEL AVERAGE PRECISION"
          value={percent(report.pixel_average_precision)}
          sub="Accounts for sparse defect pixels"
        />
        <Stat
          label="P95 INFERENCE LATENCY"
          value={`${report.latency_ms.p95.toFixed(0)} ms`}
          sub={`${report.latency_ms.device.toUpperCase()} · includes feature extraction and localization`}
        />
      </div>
      <div className="benchmark-grid">
        <section className="panel-card">
          <div className="section-label">
            <span>DISCRIMINATION</span>
            <span className="tiny-badge">IMAGE LEVEL</span>
          </div>
          <h2>Deep features vs. a simple baseline</h2>
          <p>Both methods use the same normal fitting images and held-out test set.</p>
          <div className="method-comparison">
            <MetricBar label="Deep patch memory" value={report.image_auroc} primary />
            <MetricBar label="RGB template baseline" value={report.baseline.image_auroc} />
          </div>
          <div className="roc-chart">
            <svg
              viewBox="0 0 440 245"
              role="img"
              aria-label="Receiver operating characteristic curve"
            >
              <title>ROC curve: true positive rate versus false positive rate</title>
              {[0, 0.25, 0.5, 0.75, 1].map((v) => (
                <g key={v}>
                  <line x1="48" y1={205 - v * 170} x2="413" y2={205 - v * 170} stroke="#e6e8e4" />
                  <text x="33" y={209 - v * 170} textAnchor="end">
                    {v}
                  </text>
                  <text x={48 + v * 365} y="225" textAnchor="middle">
                    {v}
                  </text>
                </g>
              ))}
              <path d="M48 205L413 35" stroke="#b7bfba" strokeDasharray="5 6" fill="none" />
              <polyline
                points={report.roc_curve
                  .map((p) => `${48 + p.fpr * 365},${205 - p.tpr * 170}`)
                  .join(' ')}
                fill="none"
                stroke="#d4532d"
                strokeWidth="3"
              />
              <text x="230" y="243" textAnchor="middle">
                False positive rate
              </text>
              <text x="49" y="17">
                True positive rate
              </text>
            </svg>
          </div>
        </section>
        <section className="panel-card threshold-card">
          <div className="section-label">
            <span>OPERATING POINT</span>
            <span className="tiny-badge">EXPLORATION ONLY</span>
          </div>
          <h2>A threshold is a tradeoff.</h2>
          <p>
            Explore false alarms and missed defects. This slider never changes the saved model or
            its calibrated threshold.
          </p>
          <div className="threshold-reading">
            <strong>{threshold.toFixed(3)}</strong>
            <button className="text-button" onClick={() => setOverride(null)}>
              <RotateCcw size={13} />
              Calibrated: {report.threshold.toFixed(3)}
            </button>
          </div>
          <label htmlFor="threshold" className="field-label">
            Sandbox anomaly threshold
          </label>
          <input
            id="threshold"
            type="range"
            min={minimum}
            max={maximum}
            step="0.005"
            value={threshold}
            onChange={(e) => setOverride(Number(e.target.value))}
          />
          <div className="threshold-axis">
            <span>More alerts</span>
            <span>Fewer alerts</span>
          </div>
          <div className="confusion-grid">
            <div>
              <span>Defects found</span>
              <strong>
                {outcome.tp}
                <small> / {report.defect_count}</small>
              </strong>
            </div>
            <div className={outcome.fn ? 'negative' : ''}>
              <span>Defects missed</span>
              <strong>{outcome.fn}</strong>
            </div>
            <div>
              <span>Normal accepted</span>
              <strong>
                {outcome.tn}
                <small> / {report.normal_count}</small>
              </strong>
            </div>
            <div className={outcome.fp ? 'negative' : ''}>
              <span>False alerts</span>
              <strong>{outcome.fp}</strong>
            </div>
          </div>
          <div className="threshold-summary">
            <span>
              Defect recall <strong>{percent(recall)}</strong>
            </span>
            <span>
              False alert rate <strong>{percent(fpr)}</strong>
            </span>
          </div>
          <div className="calibration-note">
            <ShieldCheck size={16} />
            <p>
              The saved threshold uses only {model.calibration.count} normal calibration examples
              and a {percent(model.calibration.alpha)} target false-alarm rate, assuming
              exchangeable data.
            </p>
          </div>
        </section>
      </div>
      <section className="panel-card shift-card">
        <div className="section-label">
          <span>ROBUSTNESS / CONTROLLED SHIFTS</span>
          <span className="tiny-badge">THRESHOLD HELD FIXED</span>
        </div>
        <h2>What happens when the image changes?</h2>
        <p>
          The same test images, altered one condition at a time. These are synthetic stress probes,
          not validation on another camera.
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Condition</th>
                <th>Image AUROC</th>
                <th>Defect recall</th>
                <th>Normal false alerts</th>
                <th>Missed defects</th>
              </tr>
            </thead>
            <tbody>
              <ShiftRow
                name="Original images"
                auc={report.image_auroc}
                point={report.operating_point}
              />
              {Object.entries(report.shifts).map(([key, value]) => (
                <ShiftRow
                  key={key}
                  name={
                    key === 'darker_0.65'
                      ? 'Reduced brightness × 0.65'
                      : key === 'brighter_1.35'
                        ? 'Increased brightness × 1.35'
                        : 'Gaussian blur · radius 2 px'
                  }
                  auc={value.image_auroc}
                  point={value.operating_point}
                />
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <div className="scope-note">
        <BookOpen size={18} />
        <p>
          Results describe the MVTec AD bottle category only. The bootstrap interval conditions on
          this fitted model. It excludes training and calibration uncertainty; perfect ranking on a
          small test set does not imply zero deployment error.
        </p>
      </div>
    </>
  );
}
function Stat({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="stat-card">
      <span className="metric-label">{label}</span>
      <strong>{value}</strong>
      <p>{sub}</p>
    </div>
  );
}
function MetricBar({
  label,
  value,
  primary = false,
}: {
  label: string;
  value: number;
  primary?: boolean;
}) {
  return (
    <div className={`method-bar ${primary ? 'primary' : ''}`}>
      <div>
        <span>{label}</span>
        <strong>{percent(value)}</strong>
      </div>
      <span className="bar-track">
        <i style={{ width: percent(value) }} />
      </span>
    </div>
  );
}
function ShiftRow({ name, auc, point }: { name: string; auc: number; point: OperatingPoint }) {
  return (
    <tr>
      <td>{name}</td>
      <td>{percent(auc)}</td>
      <td>{percent(point.recall)}</td>
      <td>
        {point.fp} <span className="muted">({percent(point.false_positive_rate)})</span>
      </td>
      <td>{point.fn}</td>
    </tr>
  );
}

export function ModelPage({ model }: { model: Model }) {
  const stages = [
    [
      'Decode & normalize',
      `PNG/JPEG input → RGB → ${model.input_size} × ${model.input_size}. ImageNet channel normalization. No center crop.`,
    ],
    [
      'Extract deep features',
      'Frozen ResNet-18 layers 2 and 3. Local average pooling and multi-scale concatenation. No gradient training.',
    ],
    [
      'Compare with normal memory',
      `${model.bank_size} representative patches selected from ${model.candidate_count.toLocaleString()} candidates. Euclidean nearest-neighbor distance.`,
    ],
    [
      'Score & localize',
      'Mean of the highest 1% patch distances. Upsampled, smoothed distance map for visual inspection.',
    ],
    [
      'Calibrate & review',
      'Normal-only split-conformal threshold. A human records the final assessment; no physical actions are executed.',
    ],
  ];
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <span /> PROVENANCE / MODEL CARD
          </div>
          <h1>
            Nothing behind the curtain<span className="orange">.</span>
          </h1>
          <p>The method, the data, and the boundaries of this model.</p>
        </div>
        <span className="dataset-tag">
          <span className="status-dot" />
          Active model
        </span>
      </div>
      <div className="model-layout">
        <section className="panel-card pipeline">
          <div className="section-label">
            <span>FROM PIXELS TO EVIDENCE</span>
            <Layers3 size={16} />
          </div>
          <h2>A small, inspectable perception pipeline.</h2>
          <p>
            Inspired by PatchCore. Uses a smaller backbone, candidate sampling, and an unweighted
            image score; this is not a reproduction of the paper's reported results.
          </p>
          <div className="pipeline-stages">
            {stages.map(([title, body], i) => (
              <div key={title}>
                <span>{String(i + 1).padStart(2, '0')}</span>
                <section>
                  <h3>{title}</h3>
                  <p>{body}</p>
                </section>
              </div>
            ))}
          </div>
        </section>
        <section className="panel-card identity">
          <div className="section-label">
            <span>ARTIFACT IDENTITY</span>
            <Fingerprint size={18} />
          </div>
          <h2>Versioned. Verifiable.</h2>
          <dl>
            <dt>Model ID</dt>
            <dd>
              <code>{model.model_id}</code>
            </dd>
            <dt>Created</dt>
            <dd>{date(model.created_at)}</dd>
            <dt>Feature encoder</dt>
            <dd>ResNet-18 / ImageNet-1K V1</dd>
            <dt>Memory dimensions</dt>
            <dd>
              {model.bank_size} × {model.feature_dimension}
            </dd>
            <dt>Reproducibility seed</dt>
            <dd>{model.seed}</dd>
            <dt>Fitting time</dt>
            <dd>{model.fit_seconds.toFixed(1)} seconds</dd>
            <dt>Runtime</dt>
            <dd>
              Python {model.environment.python} / PyTorch {model.environment.torch}
            </dd>
            <dt>Dataset license</dt>
            <dd>{model.data_license}</dd>
          </dl>
        </section>
      </div>
      <section className="panel-card artifact-card">
        <div className="section-label">
          <span>INTEGRITY / SHA-256</span>
          <ShieldCheck size={16} />
        </div>
        <h2>Every model file has a fingerprint.</h2>
        <p>
          The serving process verifies these checksums before loading the model. Repeated
          inspections retain their original model identity and threshold.
        </p>
        {Object.entries(model.files).map(([name, hash]) => (
          <div className="hash-row" key={name}>
            <span>
              <Check size={14} />
              {name}
            </span>
            <code>{hash}</code>
          </div>
        ))}
      </section>
      <div className="scope-grid">
        <div>
          <h3>Intended use</h3>
          <p>
            Research, learning, and inspection workflow prototyping for the MVTec AD bottle
            category. CPU inference, local data storage, and manual review.
          </p>
        </div>
        <div>
          <h3>Known limits</h3>
          <p>
            Unrelated objects can receive misleading scores. Heatmaps are coarse evidence maps.
            Illumination, alignment, and camera shifts require fresh calibration and testing.
          </p>
        </div>
        <div>
          <h3>Research attribution</h3>
          <p>
            <a href="https://arxiv.org/abs/2106.08265" target="_blank" rel="noreferrer">
              PatchCore · Roth et al.
            </a>
            <br />
            <a
              href="https://www.mvtec.com/research-teaching/datasets/mvtec-ad"
              target="_blank"
              rel="noreferrer"
            >
              MVTec AD · Bergmann et al.
            </a>
            <br />
            Dataset is for non-commercial use.
          </p>
        </div>
      </div>
    </>
  );
}

export function HistoryPage({ onOpen }: { onOpen: (value: Inspection) => void }) {
  const [offset, setOffset] = useState(0);
  const history = useQuery({
    queryKey: ['history', offset],
    queryFn: () =>
      api<{ items: Inspection[]; total: number }>(`/inspections?limit=20&offset=${offset}`),
  });
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <span /> TRACEABILITY / INSPECTION LOG
          </div>
          <h1>
            Every finding has a record<span className="orange">.</span>
          </h1>
          <p>Image, model version, threshold, and human review. Kept together.</p>
        </div>
        <span className="dataset-tag">
          <Database size={14} />
          {history.data?.total ?? '—'} inspections
        </span>
      </div>
      {history.error ? (
        <p role="alert" className="error-message">
          {history.error.message}
        </p>
      ) : history.isPending ? (
        <div className="empty-state">
          <span className="spinner" />
        </div>
      ) : !history.data?.items.length ? (
        <div className="empty-state">
          <Clock3 size={35} />
          <h2>A clean inspection log.</h2>
          <p>Run your first inspection to create a traceable record.</p>
        </div>
      ) : (
        <section className="panel-card history-card">
          <div className="history-header">
            <span>INSPECTION / INPUT</span>
            <span>MODEL FINDING</span>
            <span>DISTANCE</span>
            <span>HUMAN REVIEW</span>
            <span />
          </div>
          {history.data.items.map((item) => (
            <button className="history-row" key={item.id} onClick={() => onOpen(item)}>
              <span className="history-input">
                <img src={item.images.source} alt="" />
                <span>
                  <strong>{item.name}</strong>
                  <small>
                    {date(item.created_at)} · {item.id.slice(0, 8)}
                  </small>
                </span>
              </span>
              <span className={`badge ${item.flagged ? 'warning' : 'normal'}`}>
                {item.flagged ? 'Review recommended' : 'Normal range'}
              </span>
              <span className="history-score">
                {item.score.toFixed(3)}
                <small>limit {item.threshold.toFixed(3)}</small>
              </span>
              <span className="review-status">
                {item.reviews.at(-1)?.label || 'Awaiting review'}
              </span>
              <ArrowRight size={17} />
            </button>
          ))}
          <div className="pagination">
            <span>
              {offset + 1}–{Math.min(offset + 20, history.data.total)} of {history.data.total}
            </span>
            <button
              className="button secondary"
              disabled={offset === 0}
              onClick={() => setOffset(offset - 20)}
            >
              <ChevronLeft size={14} />
              Previous
            </button>
            <button
              className="button secondary"
              disabled={offset + 20 >= history.data.total}
              onClick={() => setOffset(offset + 20)}
            >
              Next
              <ChevronRight size={14} />
            </button>
          </div>
        </section>
      )}
    </>
  );
}
