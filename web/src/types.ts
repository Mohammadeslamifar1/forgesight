export interface Calibration {
  method: string;
  alpha: number;
  count: number;
  threshold: number;
  scores: number[];
}
export interface Model {
  model_id: string;
  created_at: string;
  method: string;
  backbone: string;
  category: string;
  input_size: number;
  bank_size: number;
  feature_dimension: number;
  candidate_count: number;
  seed: number;
  fit_count: number;
  calibration: Calibration;
  data_license: string;
  dataset_revision: string;
  split_sha256: string;
  fit_seconds: number;
  environment: { python: string; torch: string; device: string };
  files: Record<string, string>;
}
export interface Sample {
  id: string;
  defect: string;
  anomalous: boolean;
  image: string;
}
export interface Review {
  id: string;
  created_at: string;
  label: 'normal' | 'defect' | 'uncertain';
  note: string;
}
export interface Inspection {
  id: string;
  created_at: string;
  name: string;
  sample_id: string | null;
  model_id: string;
  score: number;
  threshold: number;
  flagged: boolean;
  normal_tail_rank: number;
  inference_ms: number;
  original_size: number[];
  images: { source: string; heatmap: string; overlay: string };
  reviews: Review[];
}
export interface OperatingPoint {
  tp: number;
  fp: number;
  tn: number;
  fn: number;
  precision: number | null;
  recall: number | null;
  false_positive_rate: number | null;
  f1: number;
}
export interface Benchmark {
  model_id: string;
  test_count: number;
  normal_count: number;
  defect_count: number;
  threshold: number;
  image_auroc: number;
  image_average_precision: number;
  pixel_auroc: number;
  pixel_average_precision: number;
  operating_point: OperatingPoint;
  image_auroc_ci95: { low: number; high: number };
  baseline: { image_auroc: number; image_average_precision: number };
  latency_ms: { median: number; p95: number; device: string };
  roc_curve: { fpr: number; tpr: number }[];
  shifts: Record<string, { image_auroc: number; operating_point: OperatingPoint }>;
  samples: { id: string; score: number; anomalous: boolean; defect: string; flagged: boolean }[];
}
