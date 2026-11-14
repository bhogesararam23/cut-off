import { ready, useData } from '../../lib/DataContext.tsx';
import { FileError } from '../FileError.tsx';
import { Skeleton } from '../Skeleton.tsx';
import { DetectionBySize } from './DetectionBySize.tsx';
import { HvTimeSeries } from './HvTimeSeries.tsx';

/** Both Evidence charts. Loaded on demand so the charting library is not part of the first page load. */
export default function EvidenceCharts() {
  const { stats, timeseries, event } = useData();
  const validation = ready(stats)?.validation ?? null;
  const series = ready(timeseries);
  const e = ready(event);

  return (
    <div className="space-y-5">
      {validation && <DetectionBySize bySize={validation.by_size} />}
      {timeseries.status === 'loading' && <Skeleton className="h-56" />}
      {timeseries.status === 'error' && <FileError file={timeseries.file} />}
      {series && e && <HvTimeSeries series={series} quakeIso={e.time_utc} />}
    </div>
  );
}
