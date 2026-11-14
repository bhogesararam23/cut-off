// Every word a user sees, in one place. Values in {braces} are filled at runtime from the data files.
// Wording rules: "likely blocked", "possibly cut off", "candidate landslide". Never "confirmed",
// "blocked" alone, or "detected all".

/** Replace {name} placeholders. Unknown or missing values become an en dash, never a made-up number. */
export function fill(template: string, values: Record<string, string | number | null | undefined>): string {
  return template.replace(/\{(\w+)\}/g, (_, key: string) => {
    const v = values[key];
    return v === null || v === undefined ? '–' : String(v);
  });
}

export const C = {
  meta: {
    title: "Cut Off: NISAR radar finds the roads Panama's landslides blocked",
  },
  topBar: {
    title: 'Cut Off',
    subtitle: '{name} · {date}',
    pairLabel: 'Radar pair',
    pairOption: 'Track {track} {direction} · {before} → {after}',
    about: 'About',
  },
  mockBanner: 'MOCK DATA: not real results. This screen uses made-up data while the real radar processing finishes.',
  swipe: {
    before: 'Before: {date}',
    after: 'After: {date}',
    afterHours: 'After: {date}, {hours} hours after the quake',
    handle: 'Drag to compare before and after radar images',
  },
  layers: {
    radar: 'Radar before / after',
    change: 'Radar change (red = drop)',
    landslides: 'Candidate landslides',
    roads: 'Roads',
    communities: 'Communities',
    unknown: "Can't see (radar shadow)",
  },
  legend: {
    title: 'Legend',
    radar: 'Radar HV brightness: bright = dense forest, dark = bare ground or water',
    change: 'Red = radar signal dropped (possible landslide). Blue = signal rose.',
    landslide: 'Candidate landslide (darker = seen by more radar passes)',
    roads: {
      blocked: 'Likely blocked',
      at_risk: 'At risk (within 100 m)',
      clear: 'Clear of detected landslides',
      unknown: "Unknown (radar can't see)",
    },
    communities: { cut_off: 'Possibly cut off', reachable: 'Reachable', unknown: 'Unknown' },
    grey: "Radar can't see here (slope faces away or is hidden)",
    epicentre: 'Epicentre',
  },
  overview: {
    heading: 'What the radar found',
    // The two durations are worked out from the data (first pass after the quake, and the earlier pass compared with it).
    story:
      "Clouds and forest hid Panama's landslides from normal satellites. NISAR's radar sees through both. Its first pass came {hours} hours after the quake. We compared it with a pass {days} days earlier and looked for forest that suddenly lost its radar signal.",
    cards: {
      landslides: 'candidate landslides',
      area: 'of slopes stripped',
      roads: 'of road likely blocked',
      communities: 'communities possibly cut off',
    },
    howSure:
      'How sure are we? On check points we never tuned on, it found {detection_rate}% of mapped landslides and wrongly flagged {false_alarm_rate}% of intact forest points.',
    noValidation: 'Accuracy check not run yet.',
    footnote: 'All results are from radar processed in advance. This is a research demo, not an official warning.',
    notAvailable: 'Not available yet',
  },
  landslides: {
    heading: 'Candidate landslides',
    filterLabel: 'Show confidence:',
    filters: { all: 'All', medium: 'Medium and high', high: 'High only' },
    sortLabel: 'Sort by:',
    sorts: { size: 'Size', confidence: 'Confidence', passes: 'Radar passes' },
    row: '{id} · {area} · seen in {pairs_seen} of {pairs_visible} passes',
    empty: 'No landslides match this filter.',
    confidenceHelp:
      'High: seen in at least 2 passes and in all but at most one pass that could see it. Medium: seen in at least 2 passes. Low: seen in 1 pass.',
  },
  access: {
    heading: 'Who may have been cut off',
    intro:
      'We joined the landslides to the open road map. A road is "likely blocked" if a landslide touches it. A community is "possibly cut off" if every mapped road from it to a town ({hubs}) crosses a likely-blocked road.',
    groups: { cut_off: 'Possibly cut off ({n})', unknown: 'Unknown ({n})', reachable: 'Reachable ({n})' },
    row: '{name} · {place} · {reason}',
    roadsSummary: 'Roads: {blocked_km} km likely blocked · {at_risk_km} km at risk · {clear_km} km clear · {unknown_km} km unknown',
    realityHeading: 'What was reported on the ground',
    realityText:
      'News reports said Arenas, El Cacao and Quebro were cut off when roads collapsed, and 22 bridges were damaged. By 16 October, 92% of roads affected by structural collapses had reopened. Our map is about the first days, before crews cleared them. It cannot see collapsed bridges or road subsidence.',
    hubs: ['Chitré', 'Las Tablas', 'Tonosí', 'Macaracas', 'Santiago'],
    empty: 'No communities have been assessed yet.',
  },
  evidence: {
    heading: 'How we checked',
    // The total number of marked points is not in the data files, so the sentence leaves it out.
    method:
      'We hand-marked points on Sentinel-2 photos from before and after the quake: real landslide scars and untouched forest. We split them in half at random. We tuned on one half and tested once on the other half, which we never looked at while tuning.',
    results:
      'Test half: {n_test_landslide} landslides, {n_test_forest} forest points. Found {detection_rate}%. False alarms {false_alarm_rate}%. AUC {auc} (0.5 = guessing, 1.0 = perfect).',
    noValidation: 'Validation not run yet',
    chart1Title: 'Bigger landslides are easier to see',
    chart1Summary: 'Detection rate was {small}% for small, {medium}% for medium and {large}% for large scars.',
    chart2Title: 'Radar signal at landslides vs intact forest',
    chart2Summary: 'Before the quake both lines sit together. After it, the signal at landslides drops by about {drop} dB while forest stays flat.',
    chartEmpty: 'Nothing to chart yet.',
    baselineHeading: 'Does it flag change when nothing happened?',
    baselineText: 'We ran the same method on two passes before the quake (20 Sep vs 2 Oct). It flagged {baseline}% of forested slopes, against {post}% after the quake.',
    context:
      'For comparison, a 2022 study using C-band radar (Sentinel-1) reached an AUC of about 0.83 in its best case and 0.62–0.68 in a simulated rapid response (Handwerger et al., 2022).',
    link: 'Read the full method',
  },
  why: {
    heading: 'Why radar sees landslides under clouds',
    p1: 'Radar sends its own microwaves, so it works at night and through cloud. NISAR uses L-band, with a wavelength of about 24 cm, long enough to pass through leaves and bounce around inside the forest.',
    p2: 'When the signal bounces among branches it changes direction (polarisation): it goes out horizontal (H) and some comes back vertical (V). That HV signal is strong over forest and weak over bare soil.',
    p3: 'A landslide strips the forest off a slope. The HV signal there drops sharply. We look for those drops on steep, forested slopes.',
    diagramForest: 'Forest: many bounces, strong HV',
    diagramScar: 'Landslide scar: one bounce, weak HV',
    quote: '"At least dual-polarimetry (e.g., HH and HV) is required" to detect landslides with L-band radar. (Ohki et al., 2020)',
  },
  limits: {
    heading: "What this can't tell you",
    items: [
      'It misses landslides narrower than about 3 pixels (roughly 30–60 m).',
      'Slopes facing away from the radar, or hidden behind ridges, are unknown (grey).',
      '"Likely blocked" is inferred from a landslide touching the road. Nobody saw the blockage. Collapsed bridges and sinking roads are not detected.',
      'The road map comes from OpenStreetMap volunteers. Missing roads mean missing routes.',
      "The radar data is PROVISIONAL: NISAR's science team has not finished calibrating it.",
      'Other things can lower the signal: logging, fields being cleared, very wet ground, radio interference. Using several passes cuts these down but not to zero.',
      'Most roads reopened within a week. This shows the first days, not today.',
      'This is a research demo built in 48 hours, not an official product or warning.',
    ],
  },
  timeline: { heading: 'Timeline', footer: 'Times in UTC.', empty: 'No timeline entries.' },
  popups: {
    landslide: {
      title: 'Candidate landslide {id}',
      area: 'Area: {area}',
      hv: 'Radar HV: {before} → {after} dB ({dhv} dB)',
      slope: 'Slope: {slope}°',
      seen: 'Seen in {pairs_seen} of {pairs_visible} passes that could see it',
      confidence: 'Confidence: {confidence}',
    },
    road: { unnamed: 'Unnamed road', type: 'Type: {highway}', nearest: 'Nearest landslide: {distance} m' },
    status: {
      blocked: 'Likely blocked',
      at_risk: 'At risk',
      clear: 'Clear of detected landslides',
      unknown: 'Unknown',
      cut_off: 'Possibly cut off',
      reachable: 'Reachable',
    },
  },
  about: {
    heading: 'About Cut Off',
    body: 'Cut Off was built for the NASA Space Apps Challenge 2026, challenge "Dancing with the SARs". It uses radar from NISAR, a joint mission of NASA and the Indian Space Research Organisation (ISRO). Everything is open source under the Apache 2.0 licence.',
    code: 'Code',
    method: 'Method',
    disclaimer: 'NASA does not endorse this project.',
    si: 'We used AI coding assistants to help write code and text. Every number comes from our own processing; every claim is cited. See our AI-use log',
    close: 'Close',
  },
  credits:
    'Radar: NASA-ISRO NISAR L2 GCOV (PROVISIONAL), via NASA ASF DAAC. Basemap: NASA GIBS. Roads and places: © OpenStreetMap contributors (ODbL). Check images: contains modified Copernicus Sentinel data 2026. Elevation: Copernicus DEM GLO-30.',
  errors: {
    file: 'Could not load {file}. The rest of the app still works.',
    map: 'Map failed to load. Try refreshing.',
  },
  tabs: {
    overview: 'Overview',
    landslides: 'Landslides',
    access: 'Access',
    evidence: 'Evidence',
    why: 'Why radar',
    limits: 'Limits',
    timeline: 'Timeline',
  },
} as const;

export type TabId = keyof typeof C.tabs;
export const TAB_ORDER: TabId[] = ['overview', 'landslides', 'access', 'evidence', 'why', 'limits', 'timeline'];
