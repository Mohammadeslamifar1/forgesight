import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowDownToLine,
  ArrowRight,
  Check,
  CircleCheck,
  Clock3,
  ImagePlus,
  ScanLine,
  ShieldCheck,
  SlidersHorizontal,
  TriangleAlert,
  Upload,
  X,
} from 'lucide-react';
import { api, date, post } from './api';
import type { Inspection, Model, Sample } from './types';

type Props = {
  model: Model;
  result: Inspection | null;
  setResult: (result: Inspection | null) => void;
};

export default function Workbench({ model, result, setResult }: Props) {
  const client = useQueryClient();
  const samples = useQuery({ queryKey: ['samples'], queryFn: () => api<Sample[]>('/samples') });
  const [selected, setSelected] = useState(result?.sample_id || 'broken_large-000');
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState('');
  const [view, setView] = useState<'compare' | 'source' | 'heatmap'>('compare');
  const [divider, setDivider] = useState(50);
  const [inputError, setInputError] = useState('');
  const [gallery, setGallery] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const inspection = useMutation({
    mutationFn: () =>
      file
        ? api<Inspection>(`/inspect/upload?name=${encodeURIComponent(file.name)}`, {
            method: 'POST',
            body: file,
            headers: { 'Content-Type': file.type || 'application/octet-stream' },
          })
        : post<Inspection>('/inspect/sample', { sample_id: selected }),
    onSuccess: (value) => {
      setResult(value);
      setView('compare');
      setDivider(50);
      void client.invalidateQueries({ queryKey: ['history'] });
    },
  });
  useEffect(() => {
    if (!file) {
      setPreview('');
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  const sample = samples.data?.find((s) => s.id === selected);
  const needsOriginalUpload = Boolean(result && !result.sample_id && !file);
  const source = result?.images.source || preview || sample?.image;
  const choose = (id: string) => {
    setSelected(id);
    setFile(null);
    setResult(null);
    setInputError('');
    inspection.reset();
    setGallery(false);
  };
  const upload = (chosen?: File) => {
    if (!chosen) return;
    if (!['image/png', 'image/jpeg'].includes(chosen.type) || chosen.size > 8 * 1024 * 1024) {
      setInputError('Choose a PNG or JPEG image smaller than 8 MB.');
      return;
    }
    setFile(chosen);
    setResult(null);
    setInputError('');
    inspection.reset();
  };
  const starter = ['good-000', 'broken_large-000', 'broken_small-000', 'contamination-000'];
  const error = inputError || inspection.error?.message || samples.error?.message;
  return (
    <>
      <div className="studio-grid">
        <section className="viewer-card" aria-label="Image inspection">
          <div className="card-toolbar">
            <div className="card-title">
              <ScanLine size={17} />
              <strong>Inspection canvas</strong>
              <span className="count-chip">01</span>
            </div>
            <div className="segmented" aria-label="Image view">
              {(['compare', 'source', 'heatmap'] as const).map((mode) => (
                <button
                  key={mode}
                  className={view === mode ? 'selected' : ''}
                  aria-pressed={view === mode}
                  onClick={() => setView(mode)}
                  disabled={!result && mode !== 'source'}
                >
                  {mode === 'compare' ? 'Compare' : mode === 'source' ? 'Original' : 'Heatmap'}
                </button>
              ))}
            </div>
          </div>
          <div className="image-stage">
            <div className="stage-topline">
              <span>
                <span className="status-dot" /> {result ? 'ANALYSIS COMPLETE' : 'READY TO INSPECT'}
              </span>
              <span>
                {model.input_size} × {model.input_size} MODEL INPUT
              </span>
            </div>
            <div className="image-frame">
              <span className="corner tl" />
              <span className="corner tr" />
              <span className="corner bl" />
              <span className="corner br" />
              {source ? (
                <div className="image-square">
                  <img
                    src={result && view === 'heatmap' ? result.images.heatmap : source}
                    alt={
                      view === 'heatmap' && result
                        ? 'Anomaly distance heatmap'
                        : 'Part selected for inspection'
                    }
                  />
                  {result && view === 'compare' && (
                    <>
                      <img
                        className="overlay-image"
                        src={result.images.overlay}
                        alt="Anomaly overlay"
                        style={{ clipPath: `inset(0 0 0 ${divider}%)` }}
                      />
                      <div className="comparison-line" style={{ left: `${divider}%` }}>
                        <span>
                          <ChevronHandles />
                        </span>
                      </div>
                    </>
                  )}
                </div>
              ) : (
                <div className="canvas-empty">
                  <ImagePlus size={44} />
                  <p>Select or upload a part</p>
                </div>
              )}
              {inspection.isPending && (
                <div className="processing">
                  <div className="scan-beam" />
                  <span>
                    <span className="spinner" /> Inspecting visual features…
                  </span>
                </div>
              )}
            </div>
            <div className="stage-caption">
              <span>
                {result?.name || file?.name || selected}
                <span className="muted-light">
                  {file || result?.name.includes('.') ? '' : '.png'}
                </span>
              </span>
              <span>
                {result ? 'SOURCE' : 'INPUT'} <ArrowRight size={12} />{' '}
                {result ? 'ANOMALY EVIDENCE' : 'DEEP PATCH MEMORY'}
              </span>
            </div>
            {result && view === 'compare' && (
              <div className="compare-slider">
                <span>Original</span>
                <input
                  type="range"
                  min="5"
                  max="95"
                  value={divider}
                  aria-label="Compare original and anomaly overlay"
                  onChange={(e) => setDivider(Number(e.target.value))}
                />
                <span>Overlay</span>
              </div>
            )}
          </div>
          <div className="viewer-bottom">
            <span>
              <SlidersHorizontal size={14} />{' '}
              {result
                ? 'Fixed heatmap scale across inspections'
                : 'Select a sample, then run inspection'}
            </span>
            <div className="heat-legend">
              <span>Typical</span>
              <i />
              <span>Unusual</span>
            </div>
          </div>
          <div className="sample-tray">
            <div className="section-label">
              <span>EXPLORE THE BENCHMARK</span>
              <button onClick={() => setGallery(!gallery)} disabled={inspection.isPending}>
                {gallery ? 'Close gallery' : `All ${samples.data?.length || '—'} samples`}{' '}
                <ArrowRight size={12} />
              </button>
            </div>
            <div className="sample-grid">
              {starter.map((id) => {
                const item = samples.data?.find((s) => s.id === id);
                return (
                  item && (
                    <button
                      key={id}
                      className={`sample-card ${!file && selected === id ? 'chosen' : ''}`}
                      onClick={() => choose(id)}
                      disabled={inspection.isPending}
                    >
                      <img
                        src={item.image}
                        alt={`${item.defect.replaceAll('_', ' ')} benchmark sample`}
                      />
                      <span>
                        {item.defect === 'good'
                          ? 'Normal reference'
                          : item.defect.replaceAll('_', ' ')}
                        {!file && selected === id && <Check size={12} />}
                      </span>
                    </button>
                  )
                );
              })}
            </div>
            {gallery && (
              <div className="gallery">
                <label htmlFor="sample-select">Select any held-out test image</label>
                <select
                  id="sample-select"
                  value={selected}
                  onChange={(e) => choose(e.target.value)}
                >
                  {samples.data?.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.id}
                    </option>
                  ))}
                </select>
                <p>Names reveal benchmark labels. They are never inputs to the model.</p>
              </div>
            )}
          </div>
        </section>
        <aside className="inspection-panel">
          <section className="panel-card input-panel">
            <div className="section-label">
              <span>01 / INPUT</span>
              <span className="tiny-badge">BOTTLE MODEL</span>
            </div>
            <h2>A closer look.</h2>
            <p>Choose a benchmark sample or bring your own bottle image.</p>
            <button
              className="upload-zone"
              onClick={() => fileInput.current?.click()}
              disabled={inspection.isPending}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                if (!inspection.isPending) upload(event.dataTransfer.files[0]);
              }}
            >
              <span className="upload-icon">
                <Upload size={19} />
              </span>
              <strong>{file ? file.name : 'Drop an image here'}</strong>
              <span>
                {file
                  ? 'Click to choose a different image'
                  : 'or click to browse · PNG, JPG · 8 MB max'}
              </span>
            </button>
            <input
              className="sr-only"
              ref={fileInput}
              type="file"
              accept="image/png,image/jpeg"
              aria-label="Upload inspection image"
              onChange={(e) => {
                upload(e.target.files?.[0]);
                e.target.value = '';
              }}
            />
            {file && (
              <button
                className="text-button"
                disabled={inspection.isPending}
                onClick={() => {
                  setFile(null);
                  setResult(null);
                }}
              >
                <X size={13} /> Use benchmark sample
              </button>
            )}
            {error && (
              <div role="alert" className="error-message">
                {error}
              </div>
            )}
            <button
              className="button primary run-button"
              disabled={inspection.isPending || (!file && !sample) || needsOriginalUpload}
              onClick={() => inspection.mutate()}
            >
              {inspection.isPending ? <span className="spinner" /> : <ScanLine size={17} />}
              {inspection.isPending
                ? 'Inspecting…'
                : needsOriginalUpload
                  ? 'Choose an input to inspect'
                  : 'Run inspection'}
              <ArrowRight size={16} />
            </button>
            <div className="privacy-note">
              <ShieldCheck size={13} /> Images stay on this machine.
            </div>
          </section>
          <section
            className={`panel-card result-panel ${result?.flagged ? 'flagged' : ''}`}
            aria-live="polite"
          >
            <div className="section-label">
              <span>02 / MODEL FINDING</span>
              {result && <span className="tiny-badge">{result.inference_ms.toFixed(0)} MS</span>}
            </div>
            {!result ? (
              <>
                <div className="await-icon">
                  <FocusCorners />
                </div>
                <h3>Evidence is one click away.</h3>
                <p>The model compares image patches with a memory of normal appearance.</p>
              </>
            ) : (
              <>
                <div className={`finding ${result.flagged ? 'warning' : 'normal'}`}>
                  {result.flagged ? <TriangleAlert size={23} /> : <CircleCheck size={23} />}
                  <div>
                    <h3>{result.flagged ? 'Review recommended' : 'Within normal range'}</h3>
                    <p>
                      {result.flagged
                        ? 'Appearance exceeds the calibrated threshold.'
                        : 'No score exceedance detected.'}
                    </p>
                  </div>
                </div>
                <div className="score-value">
                  <strong>{result.score.toFixed(3)}</strong>
                  <span>ANOMALY DISTANCE</span>
                </div>
                <div className="score-meter">
                  <div
                    style={{
                      width: `${Math.min((result.score / (result.threshold * 2)) * 100, 100)}%`,
                    }}
                  />
                  <span className="threshold-marker" />
                </div>
                <div className="meter-labels">
                  <span>0</span>
                  <span>Threshold {result.threshold.toFixed(3)}</span>
                  <span>{(result.threshold * 2).toFixed(2)}+</span>
                </div>
                <div className="result-facts">
                  <div>
                    <span>Decision rule</span>
                    <strong>Score &gt; threshold</strong>
                  </div>
                  <div>
                    <span>Model version</span>
                    <strong>{result.model_id.slice(-8)}</strong>
                  </div>
                </div>
                <p className="score-disclaimer">
                  A distance score, not a probability of a defect. Heatmaps show unusual regions;
                  inspect the original before deciding.
                </p>
                <a
                  className="button secondary full-width"
                  href={`/api/inspections/${result.id}/export`}
                >
                  <ArrowDownToLine size={15} />
                  Export inspection record
                </a>
              </>
            )}
          </section>
        </aside>
      </div>
      {result && <ReviewPanel result={result} update={setResult} />}
      <div className="scope-note">
        <ShieldCheck size={17} />
        <p>
          <strong>A focused model. A clear boundary.</strong> Calibrated for this bottle dataset.
          New products, viewpoints, and lighting require validation. No equipment is controlled by
          this application.
        </p>
      </div>
    </>
  );
}

function ChevronHandles() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M5 4 2 8l3 4M11 4l3 4-3 4" fill="none" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}
function FocusCorners() {
  return <ScanLine size={25} strokeWidth={1.3} />;
}

function ReviewPanel({
  result,
  update,
}: {
  result: Inspection;
  update: (value: Inspection) => void;
}) {
  const [label, setLabel] = useState<'normal' | 'defect' | 'uncertain'>('uncertain');
  const [note, setNote] = useState('');
  const client = useQueryClient();
  const review = useMutation({
    mutationFn: () => post<Inspection>(`/inspections/${result.id}/reviews`, { label, note }),
    onSuccess: (value) => {
      update(value);
      setNote('');
      void client.invalidateQueries({ queryKey: ['history'] });
    },
  });
  useEffect(() => {
    setNote('');
    review.reset();
  }, [result.id]);
  return (
    <section className="review-card">
      <div>
        <div className="eyebrow">03 / HUMAN JUDGMENT</div>
        <h2>Close the loop.</h2>
        <p>
          Your review is recorded alongside the model finding. It does not retrain or change the
          model.
        </p>
        <div className="review-log">
          {result.reviews.map((item) => (
            <div key={item.id}>
              <Clock3 size={14} />
              <span>
                <strong>{item.label}</strong> · {date(item.created_at)}
                <p>{item.note}</p>
              </span>
            </div>
          ))}
        </div>
      </div>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          review.mutate();
        }}
      >
        <fieldset>
          <legend>Your assessment</legend>
          <div className="assessment-options">
            {(['normal', 'defect', 'uncertain'] as const).map((value) => (
              <label key={value} className={label === value ? 'checked' : ''}>
                <input
                  type="radio"
                  name="assessment"
                  checked={label === value}
                  value={value}
                  onChange={() => setLabel(value)}
                />
                {value === 'normal'
                  ? 'Acceptable'
                  : value === 'defect'
                    ? 'Defect observed'
                    : 'Needs investigation'}
              </label>
            ))}
          </div>
        </fieldset>
        <label className="field-label" htmlFor="review-note">
          Review rationale
        </label>
        <textarea
          id="review-note"
          placeholder="What did you observe in the image?"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          minLength={5}
          maxLength={1000}
          required
          rows={2}
        />
        {review.error && (
          <p role="alert" className="error-message">
            {review.error.message}
          </p>
        )}
        <button
          type="submit"
          className="button dark"
          disabled={review.isPending || note.trim().length < 5}
        >
          <Check size={15} />
          {review.isPending ? 'Saving…' : 'Record review'}
        </button>
      </form>
    </section>
  );
}
