// Colours, basemap and layer ids for the map. Colour is never the only signal: blocked roads are dashed
// and cut-off communities have a ring.
import type { MapOptions } from 'maplibre-gl';

export const GIBS_TILES =
  'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg';
export const GIBS_MAX_ZOOM = 8; // the tiles stop here; the map zooms further by stretching them
export const BOUNDS_MARGIN_DEG = 0.5; // how far past the data box the map may be moved
export const FIT_PADDING_PX = 40;
export const FLY_MIN_ZOOM = 12;
export const FLY_MS = 800;

export const COLORS = {
  ink: '#0B1E3A',
  amber: '#E8A33D',
  landslide: '#D1495B',
  landslideOutline: '#7A1F2D',
  unknown: '#6B7280',
  roads: { blocked: '#E8A33D', at_risk: '#E8A33D', clear: '#8A8F98', unknown: '#C4C7CC' },
  communities: { cut_off: '#0B1E3A', reachable: '#0B1E3A', unknown: '#8A8F98' },
  epicentre: '#0B1E3A',
} as const;

export const LAYER_IDS = {
  hv: 'hv',
  change: 'hv-change',
  unknown: 'unknown',
  landslides: 'landslides',
  landslidesOutline: 'landslides-outline',
  roads: 'roads',
  roadsBlocked: 'roads-blocked',
  roadsRisk: 'roads-risk',
  roadsCasing: 'roads-casing',
  communities: 'communities',
  communitiesRing: 'communities-ring',
  communitiesTriangle: 'communities-triangle',
} as const;

export const SOURCE_IDS = {
  hv: 'hv',
  change: 'hv-change',
  unknown: 'unknown',
  landslides: 'landslides',
  roads: 'roads',
  communities: 'communities',
} as const;

/** Layers that respond to clicks, top-most first. */
export const CLICKABLE = [LAYER_IDS.communities, LAYER_IDS.landslides, LAYER_IDS.roadsBlocked, LAYER_IDS.roadsRisk, LAYER_IDS.roads] as const;

export const BASE_STYLE: NonNullable<MapOptions['style']> = {
  version: 8 as const,
  sources: {
    gibs: {
      type: 'raster' as const,
      tiles: [GIBS_TILES],
      tileSize: 256,
      maxzoom: GIBS_MAX_ZOOM,
      attribution: 'Imagery: NASA GIBS',
    },
  },
  layers: [{ id: 'gibs', type: 'raster' as const, source: 'gibs' }],
};
