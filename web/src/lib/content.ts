// Every word a user sees, in one place. Values in {braces} are filled at runtime from the data files.
// Wording rules: "likely blocked", "possibly cut off", "candidate landslide". Never "confirmed",
// "blocked" alone, or "found N landslides".

/** Replace {name} placeholders. Unknown or missing values become an en dash, never a made-up number. */
export function fill(template: string, values: Record<string, string | number | null | undefined>): string {
  return template.replace(/\{(\w+)\}/g, (_, key: string) => {
    const v = values[key];
    return v === null || v === undefined ? '–' : String(v);
  });
}

/** Said beside every place the accuracy numbers appear. */
const SPLIT_NOTE =
  'This is a random split of points within one study area, labelled from optical imagery and checked by eye. It is not independent geographic validation and not field validation; nearby points may share conditions.';

/** How radar is described everywhere. */
const RADAR_NOTE =
  'Radar can collect images through cloud and at night. This analysis looks for changes in the radar signal over forested slopes. Vegetation, soil moisture, viewing geometry and other factors also change the signal, so a change is a lead, not a confirmed landslide.';

export const C = {
  topBar: {
    title: 'Cut Off',
    pairLabel: 'Radar pair',
    pairOption: 'Track {track} {direction} · {before} → {after}',
  },
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
    radar: 'Radar HV brightness: bright = dense forest, dark = bare ground, water or shadow',
    change: 'Red = radar signal dropped (a lead). Blue = signal rose.',
    landslide: 'Candidate landslide (darker = flagged by more radar passes)',
    roads: {
      blocked: 'Likely blocked',
      at_risk: 'At risk (within 100 m)',
      clear: 'Clear of candidate landslides',
      unknown: "Unknown (radar can't see)",
    },
    communities: { cut_off: 'Possibly cut off', reachable: 'Reachable', unknown: 'Unknown' },
    grey: "Radar can't see here (slope faces away or is hidden)",
    epicentre: 'Epicentre',
  },
  landslides: {
    heading: 'Candidate landslides',
    filterLabel: 'Show:',
    filters: { all: 'All candidates', medium: 'Flagged in 2 or more passes', high: 'Flagged in nearly every pass that could see them' },
    sortLabel: 'Sort by:',
    sorts: { size: 'Size', confidence: 'Repeat support', passes: 'Passes' },
    row: '{id} · {area} · flagged in {pairs_seen} of {pairs_visible} passes',
    empty: 'No candidates match this filter.',
    showing: 'Showing the first {shown} of {total}.',
    supportLabels: { high: 'Seen in many passes', medium: 'Seen in 2 passes', low: 'Seen in 1 pass' },
    supportHelp:
      'These count how many radar passes flagged a candidate. They are not the probability that a landslide happened. The held-out AUC of {auc} says how well the method ranks the check points, not how likely any one candidate is to be real.',
  },
  access: {
    heading: 'Who may have been cut off',
    intro:
      'We joined the candidate landslides to the open road map. A road is "likely blocked" if a candidate landslide touches it. A community is "possibly cut off" if every mapped road from it to a town ({hubs}) crosses a likely-blocked road.',
    groups: { cut_off: 'Possibly cut off ({n})', unknown: 'Unknown ({n})', reachable: 'Reachable ({n})' },
    realityHeading: 'What was reported on the ground',
    realityText:
      'News reports said Arenas, El Cacao and Quebro were cut off when roads collapsed, and 22 bridges were damaged. By 16 October, 92% of roads affected by structural collapses had reopened. Our map is about the first days, before crews cleared them. It cannot see collapsed bridges or road subsidence.',
    realitySourceLabel: 'Source: Newsroom Panama, 17 Oct 2026',
    realitySourceUrl: 'https://newsroompanama.com/2026/10/17/2351-landslides-at-least-were-caused-by-the-earthquake-in-panama/',
    hubs: ['Chitré', 'Las Tablas', 'Tonosí', 'Macaracas', 'Santiago'],
    empty: 'No communities have been assessed yet.',
  },
  timeline: { heading: 'Timeline', footer: 'Times in UTC.', empty: 'No timeline entries.' },
  popups: {
    landslide: {
      title: 'Candidate landslide {id}',
      area: 'Area: {area}',
      hv: 'Radar HV: {before} → {after} dB ({dhv} dB)',
      slope: 'Slope: {slope}°',
      seen: 'Flagged in {pairs_seen} of {pairs_visible} passes that could see it',
      confidence: 'Repeat support: {confidence}',
    },
    road: {
      unnamed: 'Unnamed road',
      type: 'Type: {highway}',
      nearest: 'Nearest candidate landslide: {distance} m',
      ids: 'Candidate landslides nearby: {ids}',
    },
    community: { hub: 'Nearest town: {hub}', population: ', population {n}' },
    close: 'Close',
    status: {
      blocked: 'Likely blocked',
      at_risk: 'At risk',
      clear: 'Clear of candidate landslides',
      unknown: 'Unknown',
      cut_off: 'Possibly cut off',
      reachable: 'Reachable',
    },
  },
  errors: {
    file: 'Could not load {file}. The rest of the page still works.',
    map: 'Map failed to load. Try refreshing.',
  },
  tabs: {
    happened: 'What happened',
    slopes: 'Candidate landslides',
    roads: 'Which roads',
    access: 'Who may be cut off',
    sure: 'How sure are we',
    limits: 'Limitations',
  },
  header: {
    label: 'NISAR GCOV · {maturity} · passes {before} → {after}',
    nav: { overview: 'Overview', map: 'Map', sure: 'Accuracy', method: 'Method', data: 'Credits', repo: 'Code' },
  },
  page: {
    title: 'Candidate landslides, roads likely blocked and communities possibly cut off after the 9 October 2026 Panama earthquake',
    summary:
      'A research demo. We looked for changes in NISAR L-band radar images taken before and after the magnitude 7.7 earthquake, joined the changes to the OpenStreetMap road network, and checked the result against hand-marked points.',
    provisional: 'PROVISIONAL radar data',
    notWarning: 'The radar data are PROVISIONAL. This is not an official warning.',
    quakeSource: 'Earthquake: magnitude 7.7, 9 Oct 2026, USGS event us6000u18k',
    quakeUrl: 'https://earthquake.usgs.gov/earthquakes/eventpage/us6000u18k',
    referenceLabel: 'Copernicus EMS EMSR934',
    factsHeading: 'Key facts',
    facts: {
      landslides: { label: 'candidate landslides', meaning: 'Patches of forested slope where the radar signal dropped. Leads, not confirmed.' },
      roads: { label: 'of road likely blocked', meaning: 'Road within 10 m of a candidate landslide. Nobody saw the blockage.' },
      communities: { label: 'communities possibly cut off', meaning: 'Every mapped road to a main town crosses a likely-blocked stretch.' },
      detection: { label: 'of held-out landslide points found', meaning: 'Of {n} hand-marked landslide points set aside before scoring; {false_alarm}% of {n_forest} forest points were flagged.' },
    },
    notAvailable: 'not available',
    source: 'Source: {file}',
    readFirst:
      'How to read these numbers. Each candidate is a lead to verify. On the held-out half of the hand-marked points the method found {detection}% of the landslide points, with AUC {auc} (0.5 is guessing, 1.0 is perfect).',
    splitNote: SPLIT_NOTE,
    baselineFails:
      'The detector flags as much change without an earthquake as with one at this setting, so single detections are weak evidence.',
    openMap: 'Open the map',
    jumpAccuracy: 'How sure are we?',
  },
  toc: {
    heading: 'On this page',
    items: [
      { id: 'top', label: 'Overview' },
      { id: 'figure-1', label: 'Optical and radar' },
      { id: 'terms', label: 'Terms' },
      { id: 'map', label: 'Map' },
      { id: 'sure', label: 'Accuracy' },
      { id: 'method', label: 'Method' },
      { id: 'limits', label: 'Limitations' },
      { id: 'data', label: 'Data and credits' },
    ],
  },
  figure1: {
    title: 'Figure 1. The study area after the earthquake, in optical and radar images',
    seeing:
      'What you are seeing: on the left, a Sentinel-2 optical image made from two dates, with cloud masked out where possible. On the right, NISAR HV radar brightness on {date}. Dark areas on the radar image are bare ground, water or radar shadow; they are not all landslides.',
    altOptical: 'Optical image of the study area after the quake (Sentinel-2)',
    altRadar: 'Radar HV image of the same area after the quake (NISAR, {date})',
    capOptical: 'Optical after the quake',
    capRadar: 'Radar after the quake, {date}',
    credit: 'Credit: Contains modified Copernicus Sentinel data 2026, processed by the team. NISAR data: NASA-ISRO, distributed by ASF DAAC (PROVISIONAL).',
  },
  terms: {
    heading: 'Terms',
    items: [
      { term: 'L-band', text: 'Radar with a wavelength of about 24 cm, as on NISAR.' },
      { term: 'HV', text: 'The cross-polarised radar signal: sent horizontally, received vertically. Over forest it is usually brighter than over bare ground.' },
      { term: 'dB (decibel)', text: 'A log scale for signal strength. A drop of 3 dB is about half the power.' },
      { term: 'PROVISIONAL', text: 'Data released before the NISAR science team has finished calibrating and checking them. Values may change.' },
      { term: 'Candidate landslide', text: 'A patch of at least 3 neighbouring 20 m pixels where the radar signal dropped. A lead to verify, not a confirmed landslide.' },
      { term: 'Pre-event baseline', text: 'Ordinary change between two passes before the quake (20 Sep to 2 Oct 2026). Rain, soil moisture, farming and vegetation can change over 12 days.' },
      { term: 'Held-out point split', text: 'Half of the hand-marked points were set aside and not used to choose the settings. They are a random split inside one study area, so they are not independent geographic validation.' },
      { term: 'AUC', text: 'The chance that a randomly chosen landslide point scores higher than a randomly chosen forest point. 0.5 is guessing, 1.0 is perfect.' },
    ],
  },
  explorer: {
    heading: 'Map',
    stepLabel: 'Step {n} of {total}',
    compare: 'Compare',
    modes: { radar: 'Radar before | after', optical: 'Optical before | after', mixed: 'Optical after | Radar after' },
    opacity: 'Radar layer opacity',
    opticalBefore: 'Optical before',
    opticalAfter: 'Optical after',
    happened: 'A magnitude 7.7 earthquake struck the Azuero peninsula. The star marks the epicentre; the grey image is the radar view of the study area.',
    epicentre: 'Epicentre: {lat}° N, {lon}° W',
    slopes: 'Red-orange shapes are candidate landslides: forested slopes where the radar signal dropped. Darker shapes were flagged by more passes.',
    roadsIntro: 'A road is "likely blocked" if a candidate landslide lies within 10 m of it, and "at risk" within 100 m.',
    downloads: 'Download the data',
    odbl: 'Roads and communities are derived from OpenStreetMap and are shared under the ODbL licence.',
    search: 'Search communities',
    sureShort:
      'On the held-out half of the check points the method found {detection}% of {n_land} landslide points and flagged {false_alarm}% of {n_forest} forest points. AUC {auc}.',
    sureLink: 'See the full accuracy section',
    print: 'Print briefing',
  },
  sure: {
    heading: 'How sure are we?',
    p1: 'Check points were marked on Sentinel-2 images from before and after the quake: fresh landslide scars and untouched forest. An AI tool suggested candidates from the change in vegetation greenness and every point was checked by eye. The radar was never used to pick them. The points file was committed before any scoring.',
    p2: 'The points were split in half at random. The method settings were chosen on one half only. The other half was held out and then scored twice: first on the original method, then after the method was revised using the tuning half only. Both results are shown.',
    splitNote: SPLIT_NOTE,
    tableCaption: 'Held-out half: the two scorings',
    original: 'First scoring: original method',
    revised: 'Second scoring: revised method',
    detection: 'Landslide points found',
    falseAlarm: 'Forest points flagged',
    auc: 'AUC',
    threshold: 'Drop threshold',
    of: '{k} of {n}',
    aucNote:
      'The two AUC values use different scoring rules: the first reads one pass at the point; the revised one averages four passes, each taking the strongest drop within one pixel (20 m) of the point. See the method.',
    baselineHeading: 'Pre-event baseline',
    baselineText:
      'Ordinary change between two passes before the quake (20 Sep to 2 Oct 2026; rain, soil moisture, farming and vegetation can change over 12 days). With the same method this flagged {baseline}% of forested slopes, against {post}% in a pair spanning the quake from the same track.',
    baselineFails:
      'The detector flags as much change without an earthquake as with one at this setting, so single detections are weak evidence.',
    chart1Title: 'Detection by landslide size',
    chart1Scored: '{size}: found {rate}% (n = {n})',
    chart1TooFew: '{size}: n = {n}, too few to score',
    chartEmpty: 'Nothing to chart yet.',
    noValidation: 'Accuracy check not run yet.',
    figure2: 'Figure 2. Share of held-out landslide points found, by size',
    figure2Seeing: 'What you are seeing: bars show the share of held-out landslide points of each size that had a candidate within 20 m. n is the number of points. Groups with fewer than 5 points get no rate.',
    figure2Credit: 'Credit: hand-marked check points on Sentinel-2 images (Contains modified Copernicus Sentinel data 2026); scoring by the team, see docs/method.md.',
  },
  method: {
    heading: 'Method',
    radarHeading: 'What the radar can and cannot show',
    radarNote: RADAR_NOTE,
    steps: [
      { title: 'Radar change', text: 'For each before/after pair we take the change in the HV signal, in dB, on a 20 m grid after smoothing speckle.' },
      { title: 'Local reference', text: "We subtract each pair's own local mean change over a {window_m} m window, so slow, region-wide shifts (such as wetter soil) are not counted as landslides." },
      { title: 'Slope and forest mask', text: 'Only slopes of at least 10° that were bright forest before count. Slopes the radar cannot see (shadow, layover) are marked unknown.' },
      { title: 'Agreement and objects', text: 'Flagged pixels from up to four pairs are combined (two passes must agree where two can see). Patches under 3 pixels are dropped; each remaining connected patch is one candidate landslide.' },
      { title: 'Roads and communities', text: 'Candidates are joined to OpenStreetMap roads; a community is possibly cut off if every route to a main town is likely blocked.' },
    ],
    full: 'Read the full method',
  },
  limits: {
    heading: 'Limitations',
    items: [
      'Most check-point landslides are small (under 100 m wide), close to the 20 m radar pixel, and many are missed.',
      'The revised method found well under half of the held-out landslide points. Treat every candidate as a lead to verify.',
      'Forest check points were picked as clearly intact forest, so the false-alarm rate is probably lower than it would be across all forest.',
      'Candidates flagged by only one radar pass are weaker leads. The counts of candidates, blocked road and cut-off communities all rise and fall with the detection threshold.',
      'Slopes facing away from the radar, or hidden behind ridges, are unknown (grey).',
      '"Likely blocked" is inferred from a candidate landslide touching the road. Nobody saw the blockage. Collapsed bridges and sinking roads are not detected.',
      'The road map comes from OpenStreetMap volunteers. Missing roads mean missing routes.',
      "The radar data are PROVISIONAL: NISAR's science team has not finished calibrating them.",
      'Other things can lower the signal: logging, fields being cleared, very wet ground, radio interference. Using several passes cuts these down but not to zero.',
      'This shows the first days after the quake, not later road repairs.',
      'This is a research demo, not an official product or warning.',
    ],
  },
  footer: {
    disclaimer: 'Built for the NASA International Space Apps Challenge 2026. Not affiliated with or endorsed by NASA or ISRO.',
    credits: [
      'NISAR L2 GCOV data (PROVISIONAL) distributed by NASA’s Alaska Satellite Facility DAAC (ASF DAAC)',
      'Copernicus DEM GLO-30',
      'Contains modified Copernicus Sentinel data 2026 (Sentinel-2), processed by the team',
      '© OpenStreetMap contributors (ODbL)',
      'Basemap: NASA GIBS',
      'Event reference: Copernicus EMS EMSR934',
    ],
    licence:
      'The project code is licensed under Apache 2.0. Datasets and third-party material keep their own terms (OpenStreetMap is ODbL; Copernicus data has its own terms).',
    ai: 'AI tools assisted with code and labelling; all results were checked by the team. Sources and AI use are documented in the linked logs.',
    aiLink: 'AI-use log',
    repo: 'Code repository',
    dataHeading: 'Data and credits',
  },
} as const;

export type TabId = keyof typeof C.tabs;
export const TAB_ORDER: TabId[] = ['happened', 'slopes', 'roads', 'access', 'sure', 'limits'];
