import type { BBox } from './types.ts';

type Pt = [number, number];

function ring(coords: unknown): Pt[] {
  return coords as Pt[];
}

/** A point on or near a feature, used to place its popup and fly the map to it. */
export function representativePoint(geometry: { type: string; coordinates: unknown }): Pt {
  const c = geometry.coordinates as never;
  switch (geometry.type) {
    case 'Point':
      return c as Pt;
    case 'LineString': {
      const line = ring(c);
      return line[Math.floor(line.length / 2)];
    }
    case 'MultiLineString': {
      const line = ring((c as unknown[])[0]);
      return line[Math.floor(line.length / 2)];
    }
    case 'Polygon':
      return centroid(ring((c as unknown[])[0]));
    case 'MultiPolygon':
      return centroid(ring(((c as unknown[][])[0] as unknown[])[0]));
    default:
      throw new Error(`unsupported geometry ${geometry.type}`);
  }
}

/** Mean of the ring's distinct vertices. Good enough for small, compact shapes. */
export function centroid(points: Pt[]): Pt {
  const pts = points.length > 1 && points[0][0] === points[points.length - 1][0] && points[0][1] === points[points.length - 1][1] ? points.slice(0, -1) : points;
  const n = pts.length || 1;
  return [pts.reduce((s, p) => s + p[0], 0) / n, pts.reduce((s, p) => s + p[1], 0) / n];
}

/** The bounding box grown by `by` degrees on every side. */
export function expandBBox(b: BBox, by: number): BBox {
  return [b[0] - by, b[1] - by, b[2] + by, b[3] + by];
}
