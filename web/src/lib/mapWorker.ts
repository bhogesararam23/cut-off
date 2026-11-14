// MapLibre runs tile work in a web worker. Bundlers cannot find that file by themselves,
// so tell MapLibre where the copy shipped with the app lives. Import this once before creating a map.
import { setWorkerUrl } from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';

setWorkerUrl(workerUrl);
