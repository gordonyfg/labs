/**
 * FlyRun 3D: Drosophila-inspired Temple Runner
 * Real-time 3D endless runner using game-state heuristics and reward-modulated sparse features.
 */

// ==========================================
// 1. GLOBAL CONSTANTS & CONFIGURATION
// ==========================================
const runOptions = new URLSearchParams(window.location.search);
const learningEnabled = runOptions.get('learning') !== 'off';
const isolatedRun = runOptions.has('seed') || runOptions.get('fresh') === '1';
const obstacleRandom = runOptions.has('seed') ? pseudoRandom(Number(runOptions.get('seed')) || 1) : Math.random;
const LANES = [-3.2, 0.0, 3.2]; // Left, Center, Right
const LANE_NAMES = ['LEFT', 'CENTER', 'RIGHT'];
const CRUISE_SPEED = 24.0; // Nominal cruising velocity (units / sec)
const MIN_SPEED = 3.0;     // Minimum aerodynamic hover / crawl velocity
let forwardSpeed = CRUISE_SPEED;
let isBraking = false;

const GRAVITY = -45.0;
const JUMP_IMPULSE = 16.5; // Tuned for apex at t = 0.367s (Y ~ 3.0m)
const SLIDE_DURATION = 0.55; // seconds

// Biological Chitin & Neuromuscular Health (Homeostasis)
const MAX_HEALTH = 100.0;
let flyHealth = MAX_HEALTH;
const HEALTH_RECOVERY_RATE = 8.0; // +8.0% health per second safe flight
let invulnerableTimer = 0.0;     // Grace period after sustaining damage

let currentLane = 1; // 0=Left, 1=Center, 2=Right
let targetX = LANES[currentLane];
let characterY = 0.0;
let velocityY = 0.0;
let isJumping = false;
let isSliding = false;
let slideTimer = 0.0;

let distanceTraveled = 0.0;
let obstaclesCleared = 0;
let isGameOver = false;
let flyBrainMode = true; // Auto-pilot ON by default
let trainingEpisode = 1;
let bestDistance = 0;
let respawnCountdownTimer = null;

// ==========================================
// 2. MAIN 3D THREE.JS RUNNER SCENE
// ==========================================
const container = document.getElementById('canvas-container');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x060913);
scene.fog = new THREE.FogExp2(0x060913, 0.015);

const camera = new THREE.PerspectiveCamera(65, window.innerWidth / window.innerHeight, 0.1, 200);
camera.position.set(0, 4.2, 7.5);
camera.lookAt(0, 1.5, -12.0);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
container.appendChild(renderer.domElement);

// Lighting
const ambientLight = new THREE.AmbientLight(0x38bdf8, 0.35);
scene.add(ambientLight);

const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
dirLight.position.set(10, 20, 10);
dirLight.castShadow = true;
dirLight.shadow.mapSize.width = 1024;
dirLight.shadow.mapSize.height = 1024;
scene.add(dirLight);

// Temple Pathway Platform
const trackWidth = 11.0;
const trackSegmentLength = 120.0;
const trackGroup = new THREE.Group();
scene.add(trackGroup);

function createTrackSegment(zPos) {
  const segGroup = new THREE.Group();
  segGroup.position.z = zPos;

  // Main Stone Floor
  const floorGeo = new THREE.BoxGeometry(trackWidth, 0.5, trackSegmentLength);
  const floorMat = new THREE.MeshStandardMaterial({
    color: 0x1e293b,
    roughness: 0.85,
    metalness: 0.15,
  });
  const floor = new THREE.Mesh(floorGeo, floorMat);
  floor.position.y = -0.25;
  floor.receiveShadow = true;
  segGroup.add(floor);

  // Lane Guide Stripes
  for (let x of [-1.6, 1.6]) {
    const stripeGeo = new THREE.BoxGeometry(0.12, 0.05, trackSegmentLength);
    const stripeMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8, opacity: 0.25, transparent: true });
    const stripe = new THREE.Mesh(stripeGeo, stripeMat);
    stripe.position.set(x, 0.02, 0);
    segGroup.add(stripe);
  }

  // Side Pillars & Torches
  for (let z = -trackSegmentLength / 2; z < trackSegmentLength / 2; z += 15) {
    for (let side of [-1, 1]) {
      const pillarGeo = new THREE.BoxGeometry(0.8, 6.0, 0.8);
      const pillarMat = new THREE.MeshStandardMaterial({ color: 0x0f172a });
      const pillar = new THREE.Mesh(pillarGeo, pillarMat);
      pillar.position.set(side * (trackWidth / 2 + 0.6), 3.0, z);
      pillar.castShadow = true;
      segGroup.add(pillar);

      // Glowing Torch Light
      const torchLight = new THREE.PointLight(0xf59e0b, 0.6, 18);
      torchLight.position.set(side * (trackWidth / 2 + 0.2), 4.2, z);
      segGroup.add(torchLight);
    }
  }

  return segGroup;
}

// Instantiate 2 looping segments
const segments = [
  createTrackSegment(0),
  createTrackSegment(-trackSegmentLength)
];
segments.forEach(s => trackGroup.add(s));

// ==========================================
// 3. 3D FLY RUNNER CHARACTER
// ==========================================
const playerGroup = new THREE.Group();
playerGroup.position.set(0, 0.8, 0);
scene.add(playerGroup);

// Low-poly Fly Body
const thoraxGeo = new THREE.SphereGeometry(0.55, 12, 10);
const flyMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.4, metalness: 0.6 });
const thorax = new THREE.Mesh(thoraxGeo, flyMat);
thorax.scale.set(0.9, 0.9, 1.3);
thorax.castShadow = true;
playerGroup.add(thorax);

// Compound Eyes (Red/Orange multi-faceted)
const eyeGeo = new THREE.SphereGeometry(0.3, 10, 10);
const eyeMat = new THREE.MeshStandardMaterial({
  color: 0xd97706,
  emissive: 0x78350f,
  roughness: 0.2,
  metalness: 0.8,
});
const leftEye = new THREE.Mesh(eyeGeo, eyeMat);
leftEye.position.set(-0.35, 0.22, -0.45);
playerGroup.add(leftEye);

const rightEye = leftEye.clone();
rightEye.position.set(0.35, 0.22, -0.45);
playerGroup.add(rightEye);

// Transparent Translucent Wings
const wingGeo = new THREE.BoxGeometry(0.9, 0.02, 1.4);
const wingMat = new THREE.MeshStandardMaterial({
  color: 0x38bdf8,
  transparent: true,
  opacity: 0.55,
  roughness: 0.1,
});
const leftWing = new THREE.Mesh(wingGeo, wingMat);
leftWing.position.set(-0.6, 0.45, 0.2);
leftWing.rotation.z = Math.PI * 0.08;
playerGroup.add(leftWing);

const rightWing = new THREE.Mesh(wingGeo, wingMat);
rightWing.position.set(0.6, 0.45, 0.2);
rightWing.rotation.z = -Math.PI * 0.08;
playerGroup.add(rightWing);

// ==========================================
// 4. PROCEDURAL OBSTACLES
// ==========================================
const obstacles = [];
const OBSTACLE_TYPES = ['HURDLE', 'ARCH', 'MONOLITH'];

function spawnObstacle(zDistance) {
  const type = OBSTACLE_TYPES[Math.floor(obstacleRandom() * OBSTACLE_TYPES.length)];
  const laneIdx = Math.floor(obstacleRandom() * 3);
  const laneX = LANES[laneIdx];

  const obsGroup = new THREE.Group();
  obsGroup.userData = {
    type: type,
    lane: laneIdx,
    z: zDistance,
    cleared: false,
    box: new THREE.Box3()
  };
  obsGroup.position.set(0, 0, zDistance);

  if (type === 'HURDLE') {
    // Low stone bar across lane (Requires JUMP)
    const geo = new THREE.BoxGeometry(2.4, 0.75, 0.6);
    const mat = new THREE.MeshStandardMaterial({ color: 0xef4444, emissive: 0x7f1d1d, roughness: 0.5 });
    const hurdle = new THREE.Mesh(geo, mat);
    hurdle.position.set(laneX, 0.38, 0);
    hurdle.castShadow = true;
    obsGroup.add(hurdle);
    obsGroup.userData.bounds = { x: laneX, yMin: 0.0, yMax: 0.85, width: 2.2, depth: 0.8 };
  } else if (type === 'ARCH') {
    // High ancient archway across lane (Requires SLIDE)
    const archMat = new THREE.MeshStandardMaterial({ color: 0x8b5cf6, emissive: 0x4c1d95, roughness: 0.5 });
    // Top crossbar
    const topBar = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.8, 0.6), archMat);
    topBar.position.set(laneX, 1.8, 0);
    topBar.castShadow = true;
    obsGroup.add(topBar);

    // Spikes hanging down
    const spikeMat = new THREE.MeshStandardMaterial({ color: 0xd946ef, emissive: 0x701a75 });
    const spikes = new THREE.Mesh(new THREE.ConeGeometry(0.2, 0.6, 6), spikeMat);
    spikes.rotation.x = Math.PI;
    spikes.position.set(laneX, 1.2, 0);
    obsGroup.add(spikes);

    obsGroup.userData.bounds = { x: laneX, yMin: 0.9, yMax: 2.6, width: 2.2, depth: 0.8 };
  } else if (type === 'MONOLITH') {
    // Tall stone column (Requires LANE SWITCH)
    const geo = new THREE.BoxGeometry(2.2, 3.8, 1.0);
    const mat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, emissive: 0x78350f, roughness: 0.6 });
    const monolith = new THREE.Mesh(geo, mat);
    monolith.position.set(laneX, 1.9, 0);
    monolith.castShadow = true;
    obsGroup.add(monolith);
    obsGroup.userData.bounds = { x: laneX, yMin: 0.0, yMax: 3.8, width: 2.0, depth: 1.0 };
  }

  scene.add(obsGroup);
  obstacles.push(obsGroup);
}

// Initial obstacle spawner
for (let i = 0; i < 6; i++) {
  spawnObstacle(-35.0 - i * 32.0);
}

// ==========================================
// 4B. BIOLOGICAL MUSHROOM BODY CONNECTOME
// ==========================================
// 24 Sensory Projection Neurons (PNs):
//   PN 0-2:   Hurdle proximity (Left, Center, Right)
//   PN 3-5:   Arch proximity (Left, Center, Right)
//   PN 6-8:   Monolith proximity (Left, Center, Right)
//   PN 9-11:  Downstream secondary hazard (Left, Center, Right, 20-55m)
//   PN 12:    Haltere lateral velocity Vx Left (0..1)
//   PN 13:    Haltere lateral velocity Vx Right (0..1)
//   PN 14:    Airborne mechanoreceptor (Jumping)
//   PN 15:    Ducking mechanoreceptor (Sliding)
//   PN 16-18: LC4 Looming expansion rate (Left, Center, Right)
//   PN 19:    T4/T5 Optomotor horizontal flow Leftward
//   PN 20:    T4/T5 Optomotor horizontal flow Rightward
//   PN 21-23: Position one-hot (Lane 0, Lane 1, Lane 2)
const NUM_PN = 24;

// 128 Kenyon Cells with sparse random calyx divergence:
const NUM_KC = 128;
const KC_INPUT_DEGREE = 5; // Each KC samples 5 random PNs (Caron et al., Nature 2012)

// 4 Mushroom Body Output Neurons (MBONs):
//   MBON 0: STEER_LEFT
//   MBON 1: STEER_RIGHT
//   MBON 2: JUMP
//   MBON 3: SLIDE
const NUM_ACTIONS = 4;
const ACTION_NAMES = ['LEFT', 'RIGHT', 'JUMP', 'SLIDE'];

// Deterministic pseudo-random generator for identical Calyx connectivity across sessions
function pseudoRandom(seed) {
  let s = seed % 2147483647;
  if (s <= 0) s += 2147483646;
  return function() {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

// Sparse Random Calyx Projection Matrix: PN -> KC
const pn_to_kc_indices = [];
const pn_to_kc_weights = [];
const calyxRand = pseudoRandom(424242);

for (let k = 0; k < NUM_KC; k++) {
  const chosenPNs = [];
  while (chosenPNs.length < KC_INPUT_DEGREE) {
    const idx = Math.floor(calyxRand() * NUM_PN);
    if (!chosenPNs.includes(idx)) chosenPNs.push(idx);
  }
  pn_to_kc_indices.push(chosenPNs);
  // Normalized excitatory weights
  const weights = [];
  let wSum = 0;
  for (let j = 0; j < KC_INPUT_DEGREE; j++) {
    const w = 0.5 + calyxRand() * 0.5;
    weights.push(w);
    wSum += w;
  }
  pn_to_kc_weights.push(weights.map(w => w / wSum));
}

let currentDopamine = 0.0;
let meanAssociativeWeight = 0.35;
let lastActiveKCCount = 0;
let lastKC = new Float32Array(NUM_KC);

// Plastic Synaptic Weights Matrix W_ak (4 Actions x 128 Kenyon Cells = 512 synapses)
const kc_weights = Array.from({ length: NUM_ACTIONS }, () => new Float32Array(NUM_KC).fill(0.35));
const kc_eligibility = Array.from({ length: NUM_ACTIONS }, () => new Float32Array(NUM_KC).fill(0.0));

function updateMBDopamine(dopamineBurst, reason) {
  currentDopamine = dopamineBurst;
  const eta = learningEnabled && flyBrainMode ? 0.08 : 0.0; // Plasticity learning rate

  // Reward-modulated associative update (no spike-timing rule): delta_W = eta * Dopamine * Eligibility
  let sumW = 0;
  for (let a = 0; a < NUM_ACTIONS; a++) {
    for (let k = 0; k < NUM_KC; k++) {
      kc_weights[a][k] += eta * dopamineBurst * kc_eligibility[a][k];
      kc_weights[a][k] = Math.max(0.02, Math.min(1.95, kc_weights[a][k]));
      sumW += kc_weights[a][k];
    }
  }
  meanAssociativeWeight = sumW / (NUM_ACTIONS * NUM_KC);

  // Update UI readouts
  const dopValEl = document.getElementById('dopamine-val');
  const dopBarEl = document.getElementById('dopamine-bar');
  const stdpEl = document.getElementById('stat-stdp-weight');

  if (dopValEl) {
    dopValEl.innerText = (dopamineBurst > 0 ? '+' : '') + dopamineBurst.toFixed(2) + (dopamineBurst > 0 ? ' (reward)' : ' (penalty)');
    dopValEl.style.color = dopamineBurst > 0 ? '#34d399' : '#ef4444';
  }
  if (dopBarEl) {
    const pct = Math.max(5, Math.min(95, 50 + dopamineBurst * 45));
    dopBarEl.style.width = pct + '%';
    dopBarEl.style.background = dopamineBurst > 0 ? '#34d399' : '#ef4444';
  }
  if (stdpEl) {
    stdpEl.innerText = 'W = ' + meanAssociativeWeight.toFixed(3);
  }
}

// ==========================================
// 4C. SESSION DATA PERSISTENCE & TELEMETRY
// ==========================================
const STORAGE_KEY = 'flyrun_training_session_v2';
let sessionHistory = []; // Array of { episode, distance, cleared, weight, crash }

// Failure Diagnostics & Kinematics State
let lastJumpTime = 0;
let lastJumpDistZ = 0;
let lastJumpImpulse = 0;
let lastSlideTime = 0;
let lastLaneChangeTime = 0;

let failureStats = {
  total: 0,
  HURDLE: 0,
  ARCH: 0,
  MONOLITH: 0,
  causes: {}
};
let failureHistory = [];

function loadSession() {
  if (isolatedRun) return;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const data = JSON.parse(raw);
      if (data && typeof data.episode === 'number') {
        trainingEpisode = data.episode;
        bestDistance = data.bestDistance || 0;
        if (Array.isArray(data.kc_weights) && data.kc_weights.length === NUM_ACTIONS) {
          for (let a = 0; a < NUM_ACTIONS; a++) {
            if (Array.isArray(data.kc_weights[a]) || ArrayBuffer.isView(data.kc_weights[a])) {
              for (let k = 0; k < NUM_KC; k++) {
                if (typeof data.kc_weights[a][k] === 'number') {
                  kc_weights[a][k] = data.kc_weights[a][k];
                }
              }
            }
          }
        }
        sessionHistory = Array.isArray(data.history) ? data.history : [];
        if (data.failureStats && typeof data.failureStats.total === 'number') {
          failureStats = data.failureStats;
        }
        if (Array.isArray(data.failureHistory)) {
          failureHistory = data.failureHistory;
        }
        let sumW = 0;
        for (let a = 0; a < NUM_ACTIONS; a++) {
          for (let k = 0; k < NUM_KC; k++) {
            sumW += kc_weights[a][k];
          }
        }
        meanAssociativeWeight = sumW / (NUM_ACTIONS * NUM_KC);

        const epEl = document.getElementById('stat-episode');
        if (epEl) epEl.innerText = trainingEpisode;
        const bestEl = document.getElementById('stat-best');
        if (bestEl) bestEl.innerText = bestDistance + ' m';
        const stdpEl = document.getElementById('stat-stdp-weight');
        if (stdpEl) stdpEl.innerText = 'W = ' + meanAssociativeWeight.toFixed(3);
      }
    }
  } catch (e) {
    console.warn('Could not load session from localStorage:', e);
  }
}

function saveSession() {
  if (isolatedRun) return;
  try {
    const data = {
      episode: trainingEpisode,
      bestDistance: bestDistance,
      kc_weights: kc_weights.map(row => Array.from(row)),
      history: sessionHistory.slice(-50),
      failureStats: failureStats,
      failureHistory: failureHistory.slice(-50)
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch (e) {
    console.warn('Could not save session to localStorage:', e);
  }
}

function resetSession() {
  try {
    if (!isolatedRun) localStorage.removeItem(STORAGE_KEY);
  } catch (e) {}

  trainingEpisode = 0;
  bestDistance = 0;
  sessionHistory = [];
  failureStats = { total: 0, HURDLE: 0, ARCH: 0, MONOLITH: 0, causes: {} };
  failureHistory = [];

  for (let a = 0; a < NUM_ACTIONS; a++) {
    kc_weights[a].fill(0.35);
    kc_eligibility[a].fill(0.0);
  }
  meanAssociativeWeight = 0.35;
  currentDopamine = 0.0;

  const bestEl = document.getElementById('stat-best');
  if (bestEl) bestEl.innerText = '0 m';
  const stdpEl = document.getElementById('stat-stdp-weight');
  if (stdpEl) stdpEl.innerText = 'W = 0.350';
  const dopValEl = document.getElementById('dopamine-val');
  if (dopValEl) {
    dopValEl.innerText = '0.00';
    dopValEl.style.color = '#94a3b8';
  }
  const dopBarEl = document.getElementById('dopamine-bar');
  if (dopBarEl) {
    dopBarEl.style.width = '50%';
    dopBarEl.style.background = '#64748b';
  }

  currentEpisodeMilestones = [];
  nextMilestoneDist = 250;
  flightBlackBox.length = 0;
  lastRecordedIncident = null;
  const bbBtn = document.getElementById('btn-blackbox');
  if (bbBtn) {
    bbBtn.innerText = '✈ Black Box';
    bbBtn.style.color = '#38bdf8';
    bbBtn.style.borderColor = 'rgba(14, 165, 233, 0.4)';
  }

  resetGame();
  drawTelemetryChart();
}

// In-flight progress checkpoints during active episode
let currentEpisodeMilestones = [];
let nextMilestoneDist = 250;
let lastChartUpdateTime = 0;

// Telemetry Chart Rendering
const chartCanvas = document.getElementById('telemetry-canvas');
const chartCtx = chartCanvas ? chartCanvas.getContext('2d') : null;

function drawTelemetryChart() {
  if (!chartCtx || !chartCanvas) return;
  const w = chartCanvas.width;
  const h = chartCanvas.height;

  chartCtx.clearRect(0, 0, w, h);
  chartCtx.fillStyle = '#030712';
  chartCtx.fillRect(0, 0, w, h);

  // Background Grid Lines
  chartCtx.strokeStyle = 'rgba(255, 255, 255, 0.07)';
  chartCtx.lineWidth = 1;
  chartCtx.beginPath();
  chartCtx.moveTo(0, Math.round(h * 0.33));
  chartCtx.lineTo(w, Math.round(h * 0.33));
  chartCtx.moveTo(0, Math.round(h * 0.66));
  chartCtx.lineTo(w, Math.round(h * 0.66));
  chartCtx.stroke();

  // Combine past completed runs with current live run
  let points = [];
  let isLiveOnly = false;

  if (sessionHistory.length === 0) {
    isLiveOnly = true;
    points = [
      { distance: 0, weight: 0.350 },
      ...currentEpisodeMilestones,
      { distance: Math.max(1, Math.floor(distanceTraveled)), weight: parseFloat(meanAssociativeWeight.toFixed(3)), live: true }
    ];
  } else {
    // Up to last 19 completed + current live run
    const recent = sessionHistory.slice(-19);
    points = [
      ...recent,
      { distance: Math.max(1, Math.floor(distanceTraveled)), weight: parseFloat(meanAssociativeWeight.toFixed(3)), live: true }
    ];
  }

  const n = points.length;
  let maxDist = 50;
  let totalDist = 0;
  for (let pt of points) {
    if (pt.distance > maxDist) maxDist = pt.distance;
    totalDist += pt.distance;
  }

  // Update footer text
  const rangeEl = document.getElementById('telemetry-ep-range');
  if (rangeEl) {
    if (isLiveOnly) {
      rangeEl.innerText = `Ep ${trainingEpisode} (Live ${Math.floor(distanceTraveled)}m)`;
    } else {
      const firstEp = sessionHistory[Math.max(0, sessionHistory.length - 19)].episode;
      rangeEl.innerText = `Ep ${firstEp}-${trainingEpisode} (Live)`;
    }
  }
  const avgEl = document.getElementById('telemetry-avg-dist');
  if (avgEl) {
    avgEl.innerText = `Max: ${maxDist}m | W=${meanAssociativeWeight.toFixed(3)}`;
  }

  const padLeft = 14;
  const padRight = 14;
  const padTop = 10;
  const padBottom = 12;
  const plotW = w - padLeft - padRight;
  const plotH = h - padTop - padBottom;

  // 1. Draw Distance Curve (Cyan #38bdf8)
  chartCtx.strokeStyle = '#38bdf8';
  chartCtx.lineWidth = 2;
  chartCtx.beginPath();
  for (let i = 0; i < n; i++) {
    const x = padLeft + (n > 1 ? (i / (n - 1)) * plotW : plotW / 2);
    const normY = points[i].distance / maxDist;
    const y = padTop + plotH - normY * plotH;
    if (i === 0) chartCtx.moveTo(x, y);
    else chartCtx.lineTo(x, y);
  }
  chartCtx.stroke();

  // Area fill under Distance curve
  chartCtx.lineTo(padLeft + plotW, padTop + plotH);
  chartCtx.lineTo(padLeft, padTop + plotH);
  chartCtx.closePath();
  chartCtx.fillStyle = 'rgba(56, 189, 248, 0.12)';
  chartCtx.fill();

  // 2. Draw Weight Convergence Curve (Purple #c084fc)
  chartCtx.strokeStyle = '#c084fc';
  chartCtx.lineWidth = 1.6;
  chartCtx.beginPath();
  for (let i = 0; i < n; i++) {
    const x = padLeft + (n > 1 ? (i / (n - 1)) * plotW : plotW / 2);
    const normW = Math.max(0, Math.min(1, (points[i].weight - 0.15) / 0.85));
    const y = padTop + plotH - normW * plotH;
    if (i === 0) chartCtx.moveTo(x, y);
    else chartCtx.lineTo(x, y);
  }
  chartCtx.stroke();

  // Draw data point circles for Distance & pulsing cursor for live point
  for (let i = 0; i < n; i++) {
    const x = padLeft + (n > 1 ? (i / (n - 1)) * plotW : plotW / 2);
    const normY = points[i].distance / maxDist;
    const y = padTop + plotH - normY * plotH;
    const isLive = points[i].live;
    chartCtx.fillStyle = isLive ? '#34d399' : '#38bdf8';
    chartCtx.beginPath();
    chartCtx.arc(x, y, isLive ? 4.0 : 2.0, 0, Math.PI * 2);
    chartCtx.fill();
    if (isLive) {
      chartCtx.strokeStyle = 'rgba(52, 211, 153, 0.6)';
      chartCtx.lineWidth = 2;
      chartCtx.stroke();
    }
  }
}

// ==========================================
// 4D. 10 Hz FLIGHT DATA RECORDER (BLACK BOX)
// ==========================================
const BLACK_BOX_CAPACITY = 50; // 50 samples * 100ms = 5.0 seconds
const flightBlackBox = [];
let lastBlackBoxSampleTime = 0;
let lastRecordedIncident = null;
let lastActionTaken = 'NONE';
let lastValences = [0, 0, 0];

function sampleFlightBlackBox(nowTime, curAction, nearestObsInLane, nearestDistInLane) {
  if (nowTime - lastBlackBoxSampleTime < 100) return;
  lastBlackBoxSampleTime = nowTime;

  const pns = (typeof getSensoryProjectionNeurons === 'function') ? getSensoryProjectionNeurons() : null;
  flightBlackBox.push({
    time: parseFloat((nowTime / 1000).toFixed(2)),
    distance: Math.floor(distanceTraveled),
    speed: parseFloat(forwardSpeed.toFixed(1)),
    lane: currentLane,
    posX: parseFloat(playerGroup.position.x.toFixed(2)),
    posY: parseFloat(characterY.toFixed(2)),
    hp: Math.round(flyHealth),
    action: curAction || lastActionTaken || 'NONE',
    isBraking: isBraking,
    isJumping: isJumping,
    isSliding: isSliding,
    valences: [
      parseFloat((lastValences[0] || 0).toFixed(2)),
      parseFloat((lastValences[1] || 0).toFixed(2)),
      parseFloat((lastValences[2] || 0).toFixed(2)),
      parseFloat((lastValences[3] || 0).toFixed(2))
    ],
    kcActive: lastActiveKCCount,
    kc: pns ? [
      parseFloat(pns[0 + currentLane].toFixed(2)),
      parseFloat(pns[3 + currentLane].toFixed(2)),
      parseFloat(pns[6 + currentLane].toFixed(2))
    ] : [0, 0, 0],
    obsAhead: nearestObsInLane ? {
      type: nearestObsInLane.userData.type,
      dist: parseFloat(nearestDistInLane.toFixed(1))
    } : null
  });

  if (flightBlackBox.length > BLACK_BOX_CAPACITY) {
    flightBlackBox.shift();
  }
}

function recordFlightIncident(type, obs, damage, remainingHealth, cause, causeDetail) {
  const obsType = obs ? (obs.userData ? obs.userData.type : String(obs)) : (cause || 'UNKNOWN');
  const incidentRecord = {
    episode: trainingEpisode,
    incidentType: type, // 'DAMAGE' or 'CRASH'
    obstacleType: obsType,
    cause: cause || (type === 'DAMAGE' ? 'NON_FATAL_COLLISION' : 'LETHAL_HEALTH_DEPLETION'),
    causeDetail: causeDetail || `Impact on ${obsType} (-${damage} HP -> ${remainingHealth}% HP)`,
    distance: Math.floor(distanceTraveled),
    damage: damage,
    remainingHealth: remainingHealth,
    speedAtImpact: parseFloat(forwardSpeed.toFixed(1)),
    timestamp: Date.now(),
    blackBox: [...flightBlackBox]
  };
  lastRecordedIncident = incidentRecord;

  // Send via WebSocket to Python bridge
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'INCIDENT_EVENT', payload: incidentRecord }));
  }

  // Update Black Box button badge in HUD
  const bbBtn = document.getElementById('btn-blackbox');
  if (bbBtn) {
    bbBtn.innerText = `✈ Black Box (${type === 'CRASH' ? '💥 CRASH' : '⚠️ HIT'})`;
    bbBtn.style.color = type === 'CRASH' ? '#f87171' : '#f59e0b';
    bbBtn.style.borderColor = type === 'CRASH' ? 'rgba(239, 68, 68, 0.6)' : 'rgba(245, 158, 11, 0.6)';
  }
}

function renderBlackBoxModal(incident) {
  const modal = document.getElementById('blackbox-modal');
  if (!modal) return;

  const data = incident || lastRecordedIncident || {
    incidentType: 'LIVE_SNAPSHOT',
    obstacleType: 'NONE',
    distance: Math.floor(distanceTraveled),
    damage: 0,
    remainingHealth: Math.round(flyHealth),
    blackBox: [...flightBlackBox]
  };

  const badgeEl = document.getElementById('bb-status-badge');
  const summaryEl = document.getElementById('bb-summary');
  const tbodyEl = document.getElementById('bb-tbody');

  if (badgeEl) {
    badgeEl.innerText = `${data.incidentType}: ${data.obstacleType} @ ${data.distance}m`;
    badgeEl.style.background = data.incidentType === 'CRASH' ? '#ef4444' : (data.incidentType === 'DAMAGE' ? '#f59e0b' : '#0284c7');
    badgeEl.style.color = '#ffffff';
  }

  if (summaryEl) {
    summaryEl.innerHTML = `<strong>Incident Summary:</strong> Ep ${trainingEpisode} | Type: <code>${data.incidentType}</code> | Obstacle: <strong>${data.obstacleType}</strong> | Distance: <strong>${data.distance}m</strong> | Damage: <strong>-${data.damage} HP</strong> (Remaining: <strong>${data.remainingHealth}%</strong>)<br>5-second pre-event decision trajectory (${data.blackBox.length} samples at 10 Hz):`;
  }

  if (tbodyEl) {
    tbodyEl.innerHTML = '';
    const bb = data.blackBox || [];
    if (bb.length === 0) {
      tbodyEl.innerHTML = '<tr><td colspan="8" style="padding: 16px; text-align: center; color: #64748b;">No trajectory samples recorded yet.</td></tr>';
    } else {
      const lastTime = bb[bb.length - 1].time;
      for (let i = bb.length - 1; i >= 0; i--) {
        const pt = bb[i];
        const offsetS = (pt.time - lastTime).toFixed(2);
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
        if (i === bb.length - 1) tr.style.background = 'rgba(239, 68, 68, 0.15)';

        const actBadge = pt.action === 'NONE' ? '<span style="color:#64748b;">NONE</span>' :
          (pt.action === 'JUMP' ? '<span style="color:#facc15;font-weight:bold;">JUMP</span>' :
          (pt.action === 'SLIDE' ? '<span style="color:#c084fc;font-weight:bold;">SLIDE</span>' :
          `<span style="color:#38bdf8;font-weight:bold;">${pt.action}</span>`));

        const brakeTag = pt.isBraking ? ' <span style="color:#f59e0b;font-size:9px;">[BRAKE]</span>' : '';
        const obsTag = pt.obsAhead ? `${pt.obsAhead.type} (${pt.obsAhead.dist}m)` : '-';

        tr.innerHTML = `
          <td style="padding: 5px 10px; color: ${i === bb.length - 1 ? '#ef4444' : '#94a3b8'};">${offsetS}s</td>
          <td style="padding: 5px 10px;">${pt.distance}m</td>
          <td style="padding: 5px 10px; color: ${pt.isBraking ? '#f59e0b' : '#e2e8f0'};">${pt.speed}m/s${brakeTag}</td>
          <td style="padding: 5px 10px;">Lane ${pt.lane} (X=${pt.posX})</td>
          <td style="padding: 5px 10px;">${actBadge}</td>
          <td style="padding: 5px 10px; color: #a855f7;">[${pt.valences.join(', ')}]</td>
          <td style="padding: 5px 10px; color: #38bdf8;">[${pt.kc.join(', ')}]</td>
          <td style="padding: 5px 10px; color: #f87171;">${obsTag}</td>
        `;
        tbodyEl.appendChild(tr);
      }
    }
  }

  modal.style.display = 'flex';
}

// ==========================================
// 5. 3D CONNECTOME BRAIN HUD INSET
// ==========================================
const brainCanvas = document.getElementById('brain-canvas');
const bw = brainCanvas.clientWidth || 226;
const bh = brainCanvas.clientHeight || 140;

const brainScene = new THREE.Scene();
const brainCamera = new THREE.PerspectiveCamera(50, bw / bh, 0.1, 50);
brainCamera.position.set(0, 0, 8.5);

let brainRenderer = null;
try {
  brainRenderer = new THREE.WebGLRenderer({ canvas: brainCanvas, alpha: true, antialias: true });
  brainRenderer.setSize(bw, bh);
} catch (e) {
  console.warn("Second WebGL context for brain HUD not supported; skipping brain canvas:", e);
}

// Generate Fruit Fly Brain Point Cloud (Optic lobes + Central brain ~1200 particles)
const brainParticleCount = 1200;
const brainPositions = new Float32Array(brainParticleCount * 3);
const brainColors = new Float32Array(brainParticleCount * 3);

for (let i = 0; i < brainParticleCount; i++) {
  // Model bilobed drosophila morphology
  const isLeftEye = i < 450;
  const isRightEye = i >= 450 && i < 900;
  const isCentral = i >= 900;

  let x, y, z;
  if (isLeftEye) {
    // Left optic lobe
    x = -2.2 + (Math.random() - 0.5) * 1.5;
    y = (Math.random() - 0.5) * 2.2;
    z = (Math.random() - 0.5) * 1.6;
    brainColors[i * 3 + 0] = 0.2;
    brainColors[i * 3 + 1] = 0.7;
    brainColors[i * 3 + 2] = 0.9;
  } else if (isRightEye) {
    // Right optic lobe
    x = 2.2 + (Math.random() - 0.5) * 1.5;
    y = (Math.random() - 0.5) * 2.2;
    z = (Math.random() - 0.5) * 1.6;
    brainColors[i * 3 + 0] = 0.2;
    brainColors[i * 3 + 1] = 0.7;
    brainColors[i * 3 + 2] = 0.9;
  } else {
    // Central complex / Mushroom Body
    x = (Math.random() - 0.5) * 1.8;
    y = -0.4 + (Math.random() - 0.5) * 2.0;
    z = (Math.random() - 0.5) * 1.8;
    brainColors[i * 3 + 0] = 0.6;
    brainColors[i * 3 + 1] = 0.3;
    brainColors[i * 3 + 2] = 0.9;
  }

  brainPositions[i * 3 + 0] = x;
  brainPositions[i * 3 + 1] = y;
  brainPositions[i * 3 + 2] = z;
}

const brainGeo = new THREE.BufferGeometry();
brainGeo.setAttribute('position', new THREE.BufferAttribute(brainPositions, 3));
brainGeo.setAttribute('color', new THREE.BufferAttribute(brainColors, 3));

const brainMat = new THREE.PointsMaterial({
  size: 0.16,
  vertexColors: true,
  transparent: true,
  opacity: 0.85,
  blending: THREE.AdditiveBlending,
});
const brainCloud = new THREE.Points(brainGeo, brainMat);
brainScene.add(brainCloud);

// Giant Fiber marker (Gold central pulses)
const gfPulseGeo = new THREE.SphereGeometry(0.35, 12, 12);
const gfPulseMat = new THREE.MeshBasicMaterial({ color: 0xeab308, wireframe: true });
const gfPulse = new THREE.Mesh(gfPulseGeo, gfPulseMat);
gfPulse.position.set(0, -0.5, 0);
brainScene.add(gfPulse);

// ==========================================
// 6. COMPOUND EYE 48x48 CANVAS RENDERER
// ==========================================
const eyeCanvas = document.getElementById('eye-canvas');
const eyeCtx = eyeCanvas ? eyeCanvas.getContext('2d') : null;

function updateEyeCanvas(nearestObs, nearestDist) {
  if (!eyeCtx) return;

  try {
    const W = 48;
    const H = 48;
    const cx = 24;
    const cy = 23;

    // 1. Deep space / corridor background
    eyeCtx.fillStyle = '#090d16';
    eyeCtx.fillRect(0, 0, W, H);

    // 2. Converging corridor ground & lane guidelines
    const flyX = (playerGroup && playerGroup.position) ? playerGroup.position.x : 0.0;
    const flyY = (playerGroup && playerGroup.position) ? playerGroup.position.y : 0.8;

    // Ground plane below horizon
    const groundGrad = eyeCtx.createLinearGradient(0, cy, 0, H);
    groundGrad.addColorStop(0, '#0c1524');
    groundGrad.addColorStop(1, '#111e33');
    eyeCtx.fillStyle = groundGrad;
    eyeCtx.fillRect(0, cy, W, H - cy);

    // Converging lane dividers to vanishing point (cx, cy)
    eyeCtx.strokeStyle = 'rgba(56, 189, 248, 0.22)';
    eyeCtx.lineWidth = 1;
    const leftDividerX = cx + ((-1.6 - flyX) / 8.0) * 26.0;
    const rightDividerX = cx + ((1.6 - flyX) / 8.0) * 26.0;
    eyeCtx.beginPath();
    eyeCtx.moveTo(cx, cy);
    eyeCtx.lineTo(leftDividerX, H);
    eyeCtx.moveTo(cx, cy);
    eyeCtx.lineTo(rightDividerX, H);
    eyeCtx.stroke();

    // Moving floor optic flow lines (motion texture moving towards camera)
    eyeCtx.strokeStyle = 'rgba(56, 189, 248, 0.12)';
    const floorPhase = (distanceTraveled * 0.8) % 6;
    for (let f = 0; f < 3; f++) {
      const floorY = cy + 4 + ((f * 6 + floorPhase) % 18);
      const spread = ((floorY - cy) / (H - cy)) * 16.0;
      eyeCtx.beginPath();
      eyeCtx.moveTo(cx - spread, floorY);
      eyeCtx.lineTo(cx + spread, floorY);
      eyeCtx.stroke();
    }

    // 3. Lateral Peripheral Walls: Streaming Optomotor Motion Gratings (T4/T5 input)
    const flowSpeed = (typeof forwardSpeed !== 'undefined') ? forwardSpeed : 24.0;
    const wallPhase = (distanceTraveled * 1.2) % 12;
    const alpha = Math.min(1.0, Math.max(0.2, 0.8 * (flowSpeed / 24.0)));
    eyeCtx.fillStyle = `rgba(56, 189, 248, ${alpha * 0.75})`;
    for (let s = 0; s < 4; s++) {
      const yPos = Math.floor(((s * 12 + wallPhase) % (H + 8)) - 4);
      // Left ommatidia motion stripe (cols 0..3)
      eyeCtx.fillRect(0, yPos, 4, 6);
      // Right ommatidia motion stripe (cols 44..47)
      eyeCtx.fillRect(44, yPos, 4, 6);
    }

    // 4. Multi-Obstacle Retinotopic Projection (Painter's Algorithm: Far to Near)
    const visibleObs = [];
    if (typeof obstacles !== 'undefined' && Array.isArray(obstacles)) {
      for (let i = 0; i < obstacles.length; i++) {
        const obs = obstacles[i];
        if (!obs || !obs.position || !obs.userData) continue;
        const distZ = -obs.position.z;
        if (distZ > 1.2 && distZ < 85.0) {
          visibleObs.push({ obs: obs, distZ: distZ });
        }
      }
    }
    visibleObs.sort((a, b) => b.distZ - a.distZ); // Far to near

    let maxLoomingContrast = 0.0;

    for (let i = 0; i < visibleObs.length; i++) {
      const item = visibleObs[i];
      const obs = item.obs;
      const distZ = item.distZ;
      const type = obs.userData.type || 'MONOLITH';
      const laneIdx = (obs.userData.lane !== undefined) ? obs.userData.lane : 1;
      const obsLaneX = (typeof LANES !== 'undefined' && LANES[laneIdx] !== undefined) ? LANES[laneIdx] : 0.0;

      // Compute continuous relative 3D offset
      const relX = obsLaneX - flyX;
      const relZ = distZ;

      // Perspective projection onto 48x48 grid (Focal length ~26 pixels)
      const px = cx + (relX / relZ) * 26.0;

      if (type === 'MONOLITH') {
        // Tall rectangular column (y from ground 0.0 to 3.8m, center ~1.9m)
        const relY = 1.9 - flyY;
        const py = cy - (relY / relZ) * 26.0;
        const pw = Math.max(2, Math.min(22, (2.2 / relZ) * 26.0));
        const ph = Math.max(3, Math.min(38, (3.8 / relZ) * 26.0));

        const x0 = Math.round(px - pw / 2);
        const y0 = Math.round(py - ph / 2);
        eyeCtx.fillStyle = '#f59e0b'; // Amber monolith body
        eyeCtx.fillRect(x0, y0, Math.round(pw), Math.round(ph));
        if (pw >= 4 && ph >= 6) {
          eyeCtx.fillStyle = '#78350f'; // Dark looming core
          eyeCtx.fillRect(x0 + 1, y0 + 1, Math.round(pw - 2), Math.round(ph - 2));
        }

        if (laneIdx === currentLane && distZ < 35.0) {
          maxLoomingContrast = Math.max(maxLoomingContrast, (35.0 - distZ) / 35.0);
        }
      } else if (type === 'HURDLE') {
        // Low horizontal stone bar across lane (y=0.38m, width=2.4m, height=0.75m)
        const relY = 0.38 - flyY;
        const py = cy - (relY / relZ) * 26.0;
        const pw = Math.max(2, Math.min(24, (2.4 / relZ) * 26.0));
        const ph = Math.max(2, Math.min(10, (0.75 / relZ) * 26.0));

        const x0 = Math.round(px - pw / 2);
        const y0 = Math.round(py - ph / 2);
        eyeCtx.fillStyle = '#ef4444'; // Red hurdle
        eyeCtx.fillRect(x0, y0, Math.round(pw), Math.round(ph));
        eyeCtx.fillStyle = '#fca5a5'; // Bright top contrast edge
        eyeCtx.fillRect(x0, y0, Math.round(pw), 1);

        if (laneIdx === currentLane && distZ < 35.0) {
          maxLoomingContrast = Math.max(maxLoomingContrast, (35.0 - distZ) / 35.0);
        }
      } else if (type === 'ARCH') {
        // High arch crossbar with opening underneath (y=1.8m, width=2.6m, height=0.8m)
        const relY = 1.8 - flyY;
        const py = cy - (relY / relZ) * 26.0;
        const pw = Math.max(3, Math.min(26, (2.6 / relZ) * 26.0));
        const ph = Math.max(2, Math.min(8, (0.8 / relZ) * 26.0));

        const x0 = Math.round(px - pw / 2);
        const y0 = Math.round(py - ph / 2);
        eyeCtx.fillStyle = '#c084fc'; // Purple arch crossbar
        eyeCtx.fillRect(x0, y0, Math.round(pw), Math.round(ph));

        // Downward spikes
        const spikeH = Math.max(1, Math.min(5, (0.5 / relZ) * 26.0));
        eyeCtx.fillStyle = '#ec4899';
        eyeCtx.fillRect(Math.round(px - 1), y0 + Math.round(ph), 2, Math.round(spikeH));

        // Side pillars
        const pillarH = Math.max(2, Math.min(20, (1.8 / relZ) * 26.0));
        eyeCtx.fillStyle = 'rgba(192, 132, 252, 0.6)';
        eyeCtx.fillRect(x0, y0, 1, Math.round(pillarH));
        eyeCtx.fillRect(x0 + Math.round(pw) - 1, y0, 1, Math.round(pillarH));

        if (laneIdx === currentLane && distZ < 35.0) {
          maxLoomingContrast = Math.max(maxLoomingContrast, (35.0 - distZ) / 35.0);
        }
      }
    }

    // 5. Looming Expansion Warning Halo (LC4 Activation Feedback)
    if (maxLoomingContrast > 0.4) {
      const haloAlpha = (maxLoomingContrast - 0.4) * 1.5;
      eyeCtx.strokeStyle = `rgba(239, 68, 68, ${haloAlpha * 0.8})`;
      eyeCtx.lineWidth = 1;
      eyeCtx.strokeRect(5, 3, 38, 42);
    }

    // 6. Biological Compound Eye Vignette (Curved Cornea)
    eyeCtx.fillStyle = '#020617';
    eyeCtx.fillRect(0, 0, 3, 1);
    eyeCtx.fillRect(0, 1, 2, 1);
    eyeCtx.fillRect(0, 2, 1, 1);
    eyeCtx.fillRect(45, 0, 3, 1);
    eyeCtx.fillRect(46, 1, 2, 1);
    eyeCtx.fillRect(47, 2, 1, 1);
    eyeCtx.fillRect(0, 47, 3, 1);
    eyeCtx.fillRect(0, 46, 2, 1);
    eyeCtx.fillRect(0, 45, 1, 1);
    eyeCtx.fillRect(45, 47, 3, 1);
    eyeCtx.fillRect(46, 46, 2, 1);
    eyeCtx.fillRect(47, 45, 1, 1);

    // 7. Update UI HUD Labels
    const eyeBadgeEl = document.getElementById('eye-looming-badge');
    const eyeStatusEl = document.getElementById('eye-status');
    if (eyeBadgeEl) {
      if (maxLoomingContrast > 0.75) {
        eyeBadgeEl.innerText = 'CRITICAL';
        eyeBadgeEl.style.background = 'rgba(239, 68, 68, 0.25)';
        eyeBadgeEl.style.color = '#ef4444';
      } else if (maxLoomingContrast > 0.3) {
        eyeBadgeEl.innerText = 'LOOMING';
        eyeBadgeEl.style.background = 'rgba(245, 158, 11, 0.25)';
        eyeBadgeEl.style.color = '#f59e0b';
      } else {
        eyeBadgeEl.innerText = 'CLEAR';
        eyeBadgeEl.style.background = 'rgba(34, 197, 94, 0.2)';
        eyeBadgeEl.style.color = '#4ade80';
      }
    }
    if (eyeStatusEl) {
      eyeStatusEl.innerText = `Flow: ${flowSpeed.toFixed(1)} m/s | Loom: ${maxLoomingContrast.toFixed(2)}`;
    }
  } catch (err) {
    console.error('Error in updateEyeCanvas:', err);
  }
}

// ==========================================
// 7. INCIDENT LOGGER & BROWSER AUTOPILOT
// ==========================================
let ws = null;
let isWsConnected = false;

function initWebSocket() {
  // If running on HTTPS (e.g. GitHub Pages) or external host, run purely in standalone browser mode
  if (window.location.protocol === 'https:' || (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1')) {
    isWsConnected = false;
    const statusEl = document.getElementById('bridge-status');
    if (statusEl) {
      statusEl.innerText = '● STANDALONE AUTOPILOT';
      statusEl.style.color = '#38bdf8';
    }
    return;
  }

  try {
    ws = new WebSocket('ws://localhost:8765');
    ws.onopen = () => {
      isWsConnected = true;
      const statusEl = document.getElementById('bridge-status');
      if (statusEl) {
        statusEl.innerText = '● INCIDENT LOGGER CONNECTED';
        statusEl.style.color = '#10b981';
      }
    };
    ws.onclose = () => {
      isWsConnected = false;
      const statusEl = document.getElementById('bridge-status');
      if (statusEl) {
        statusEl.innerText = '● LOCAL CONTROLLER';
        statusEl.style.color = '#38bdf8';
      }
      setTimeout(initWebSocket, 4000);
    };
  } catch (e) {
    isWsConnected = false;
  }
}
initWebSocket();

// Function to compute 24-Channel Sensory Projection Neurons (PNs)
// PN 0-2: Ground Hurdle proximity in Left, Center, Right lane (0.0 -> 1.0 within 38m)
// PN 3-5: Overhead Arch proximity in Left, Center, Right lane (0.0 -> 1.0 within 38m)
// PN 6-8: Tall Monolith proximity in Left, Center, Right lane (0.0 -> 1.0 within 38m)
// PN 9-11: Downstream secondary hazards in Left, Center, Right lane (20m to 55m)
// PN 12-13: Haltere lateral velocity (Leftward, Rightward)
// PN 14-15: Mechanoreceptors (Airborne jumping, Ducking sliding)
// PN 16-18: Lobula LC4 Looming expansion rate across Left, Center, Right hemifields
// PN 19-20: T4/T5 Optomotor horizontal motion flow (Leftward, Rightward drift)
// PN 21-23: Spatial position one-hot (Lane 0, 1, 2)
function getSensoryProjectionNeurons() {
  const pn = new Float32Array(NUM_PN);
  const curV = Math.max(1.0, forwardSpeed);

  // 1. Obstacle Geometry, Distance & Downstream Hazards (PN 0-11, 16-18)
  for (const obs of obstacles) {
    if (obs.userData.cleared) continue;
    const dz = -obs.position.z;
    const lane = obs.userData.lane;
    if (lane < 0 || lane > 2) continue;

    // Primary Lead Obstacle Zone (0.5m to 38.0m)
    if (dz > 0.5 && dz < 38.0) {
      const prox = (38.0 - dz) / 38.0;
      if (obs.userData.type === 'HURDLE') {
        pn[0 + lane] = Math.max(pn[0 + lane], prox);
      } else if (obs.userData.type === 'ARCH') {
        pn[3 + lane] = Math.max(pn[3 + lane], prox);
      } else if (obs.userData.type === 'MONOLITH') {
        pn[6 + lane] = Math.max(pn[6 + lane], prox);
      }

      // Visual Feature Detectors: LC4 Looming Optical Expansion Rate (PN 16-18)
      const looming = Math.min(1.0, (curV * 10.0) / Math.max(3.0, dz * dz));
      pn[16 + lane] = Math.max(pn[16 + lane], looming);
    }

    // Secondary Downstream Hazard Zone (20.0m to 55.0m)
    if (dz >= 20.0 && dz < 55.0) {
      const downProx = (55.0 - dz) / 35.0;
      pn[9 + lane] = Math.max(pn[9 + lane], downProx);
    }
  }

  // 2. Haltere Gyroscopic Proprioception & Ego-Motion (PN 12-15)
  const lateralDiff = targetX - playerGroup.position.x;
  if (lateralDiff < -0.05) {
    pn[12] = Math.min(1.0, Math.abs(lateralDiff) / 1.6); // Moving Left
  } else if (lateralDiff > 0.05) {
    pn[13] = Math.min(1.0, Math.abs(lateralDiff) / 1.6); // Moving Right
  }
  pn[14] = isJumping ? Math.min(1.0, Math.max(0.2, characterY / 2.0)) : 0.0;
  pn[15] = isSliding ? 1.0 : 0.0;

  // 3. Optomotor Horizontal Motion Flow (PN 19-20)
  if (lateralDiff < -0.05) {
    pn[19] = Math.min(1.0, Math.abs(lateralDiff) / 1.6);
  } else if (lateralDiff > 0.05) {
    pn[20] = Math.min(1.0, Math.abs(lateralDiff) / 1.6);
  }

  // 4. Spatial Position One-Hot (PN 21-23)
  if (currentLane >= 0 && currentLane <= 2) {
    pn[21 + currentLane] = 1.0;
  }

  return pn;
}

// Mushroom Body Network Step:
// 128 Kenyon Cells with Sparse Random Calyx Projection & APL Feedback Inhibition (~7% Sparsity)
function stepMushroomBodyNetwork(pns) {
  // 1. Dendritic integration across K=5 random PN inputs per KC
  const rawExcitation = new Float32Array(NUM_KC);
  let aplDrive = 0.0;
  for (let k = 0; k < NUM_KC; k++) {
    const indices = pn_to_kc_indices[k];
    const weights = pn_to_kc_weights[k];
    let sum = 0.0;
    for (let j = 0; j < KC_INPUT_DEGREE; j++) {
      sum += weights[j] * pns[indices[j]];
    }
    rawExcitation[k] = sum;
    aplDrive += sum;
  }

  // 2. APL (Anterior Paired Lateral) GABAergic Feedback Inhibition
  // Explicit top-k approximation; ties cannot exceed the nine-cell cap.
  const kc = FlyRunController.sparseCode(rawExcitation, 9, 1.0 + 0.08 * aplDrive);
  const activeCount = kc.reduce((n, value) => n + (value > 0 ? 1 : 0), 0);
  lastActiveKCCount = activeCount;

  // Update HUD sparsity readout
  const kcEl = document.getElementById('stat-kc-sparse');
  if (kcEl) {
    kcEl.innerText = `${activeCount} / ${NUM_KC}`;
  }

  // 3. MBON Efferent Readout (4 Actions: LEFT=0, RIGHT=1, JUMP=2, SLIDE=3)
  const valences = [0.0, 0.0, 0.0, 0.0];
  for (let a = 0; a < NUM_ACTIONS; a++) {
    let sumVal = 0.0;
    const wRow = kc_weights[a];
    for (let k = 0; k < NUM_KC; k++) {
      if (kc[k] > 0) {
        sumVal += (wRow[k] - 0.30) * kc[k];
      }
    }
    valences[a] = sumVal;
  }

  return { kc, valences };
}

// Cooldown to prevent high-frequency erratic lane switching
let lastLaneDecisionTime = 0;

// Embedded browser controller (heuristic policy + sparse associative readout):
// Integrates 24 PNs, 128 KCs with APL, 4 MBONs, and Giant Fiber / Optomotor Safety Reflexes
function stepBrowserController(nearestObsInLane, distZ, nowTime) {
  let action = 'NONE';
  let customImpulse = 0.0;
  let isLooming = false;
  let isGiantFiberFired = false;
  let isOptomotorFired = false;
  let shouldBrake = false;

  const curV = Math.max(1.0, forwardSpeed);

  // Compute nearest obstacle distance and type across all 3 lanes
  const laneNearestDist = [999.0, 999.0, 999.0];
  const laneNearestType = [null, null, null];
  for (const obs of obstacles) {
    if (obs.userData.cleared) continue;
    const dz = -obs.position.z;
    if (dz > 0.3 && dz < 45.0) {
      const l = obs.userData.lane;
      if (dz < laneNearestDist[l]) {
        laneNearestDist[l] = dz;
        laneNearestType[l] = obs.userData.type;
      }
    }
  }

  // Step the 24-PN / 128-KC / 4-MBON Mushroom Body Network
  const pns = getSensoryProjectionNeurons();
  const { kc, valences } = stepMushroomBodyNetwork(pns);
  lastValences = valences;
  lastKC = kc;

  const canSwitchLanes = (nowTime - lastLaneDecisionTime) > 300 && Math.abs(playerGroup.position.x - targetX) < 0.40;
  const isTurning = Math.abs(playerGroup.position.x - targetX) > 0.25;
  let secondaryAction = null;

  const canSteerLeft = currentLane > 0;
  const canSteerRight = currentLane < 2;

  // 1. ANTICIPATORY GOAL-DIRECTED NAVIGATION & EMERGENCY LOOMING REFLEX
  if (nearestObsInLane && distZ > 0.3 && distZ < 35.0) {
    const obsType = nearestObsInLane.userData.type;
    isLooming = true;
    const tau = distZ / curV; // Biologically perceived time-to-collision

    // Strict safety conditions for adjacent lanes
    const isLeftSafe = canSteerLeft && (laneNearestDist[currentLane - 1] > 20.0) && (laneNearestDist[currentLane - 1] > distZ + 4.0);
    const isRightSafe = canSteerRight && (laneNearestDist[currentLane + 1] > 20.0) && (laneNearestDist[currentLane + 1] > distZ + 4.0);

    if (obsType === 'HURDLE' || obsType === 'ARCH') {
      const isHurdle = obsType === 'HURDLE';
      const mbonActionIdx = isHurdle ? 2 : 3; // 2=JUMP, 3=SLIDE
      const clearanceValence = valences[mbonActionIdx];

      // Biological Energy & Risk Minimization:
      // If an adjacent lane is strictly safe and MBON steering valence strongly prefers dodging, steer!
      let preferSteer = null;
      if (isLeftSafe && isRightSafe) {
        preferSteer = valences[0] >= valences[1] ? 'LEFT' : 'RIGHT';
      } else if (isLeftSafe) {
        preferSteer = 'LEFT';
      } else if (isRightSafe) {
        preferSteer = 'RIGHT';
      }

      const steerValence = preferSteer === 'LEFT' ? valences[0] : (preferSteer === 'RIGHT' ? valences[1] : -999);

      if (preferSteer && canSwitchLanes && distZ >= 15.0 && tau > 0.60 && (steerValence > clearanceValence + 0.15)) {
        action = preferSteer;
        lastLaneDecisionTime = nowTime;
      } else {
        // BALLISTIC ESCAPE REFLEX / MBON VERTICAL DISPATCH:
        if (isHurdle) {
          // Giant Fiber Escape Jump at parabolic apex (tau <= 0.38s, distZ <= 9.0m, or high JUMP valence)
          if (tau <= 0.38 || distZ <= 9.0 || (clearanceValence > 0.45 && distZ <= 12.0 && tau <= 0.50)) {
            action = 'JUMP';
            customImpulse = 16.5;
            isGiantFiberFired = true;
          }
        } else {
          // Looming slide crouch (tau <= 0.46s, distZ <= 11.0m, or high SLIDE valence)
          if (tau <= 0.46 || distZ <= 11.0 || (clearanceValence > 0.45 && distZ <= 13.0 && tau <= 0.55)) {
            action = 'SLIDE';
            isGiantFiberFired = true;
          }
        }

        // If trapped with no safe alternative, air-brake to widen reaction window before jump/slide
        if (!isLeftSafe && !isRightSafe && !isJumping && !isSliding && distZ > 12.0 && tau < 0.65) {
          shouldBrake = true;
        }
      }

      // Reflex Safety Net: Ensure escape posture is armed even if mid-turn or steering
      if (obsType === 'ARCH' && (tau <= 0.46 || distZ <= 10.5)) {
        if (action !== 'SLIDE' && !isSliding) secondaryAction = 'SLIDE';
      } else if (obsType === 'HURDLE' && (tau <= 0.38 || distZ <= 8.5)) {
        if (action !== 'JUMP' && !isJumping) secondaryAction = 'JUMP';
      }
    } else if (obsType === 'MONOLITH') {
      isOptomotorFired = true;
      // Monolith cannot be jumped or slid under. Must evade via lateral steering!
      const scoreLeft = canSteerLeft ? (laneNearestDist[currentLane - 1] + valences[0] * 5.0) : -999;
      const scoreRight = canSteerRight ? (laneNearestDist[currentLane + 1] + valences[1] * 5.0) : -999;

      const altCongested = (!isLeftSafe && !isRightSafe) || (distZ < 14.0);
      if (tau < 0.65 || altCongested || isTurning) {
        shouldBrake = true;
      }

      if (canSwitchLanes) {
        if (scoreLeft > scoreRight && scoreLeft > 0) {
          action = 'LEFT';
          lastLaneDecisionTime = nowTime;
        } else if (scoreRight > scoreLeft && scoreRight > 0) {
          action = 'RIGHT';
          lastLaneDecisionTime = nowTime;
        } else if (distZ < 10.0) {
          // Absolute emergency evasion at < 10m
          if (canSteerLeft && canSteerRight) {
            action = laneNearestDist[currentLane - 1] >= laneNearestDist[currentLane + 1] ? 'LEFT' : 'RIGHT';
          } else if (canSteerLeft) {
            action = 'LEFT';
          } else if (canSteerRight) {
            action = 'RIGHT';
          }
          lastLaneDecisionTime = nowTime;
        }
      }
    }
  }

  // Dual-reflex protection during lane transition:
  // If mid-turn, air-brake and check any impending hazards across all lanes
  if (isTurning) {
    shouldBrake = true;
    const posture = FlyRunController.transitionAction(
      obstacles, playerGroup.position.x, targetX, isJumping, isSliding);
    if (posture) {
      // The imminent swept-path hazard wins over an incompatible posture.
      if (action === 'JUMP' || action === 'SLIDE') action = posture;
      secondaryAction = action === posture ? null : posture;
    } else {
      secondaryAction = null;
    }
  }

  // Air-brake if approaching obstacle while turning to stabilize lateral lane change
  if (nearestObsInLane && distZ < 14.0 && isTurning) {
    shouldBrake = true;
  }

  // Strictly preserve ballistic momentum: NEVER brake while jumping or sliding
  if (isJumping || isSliding || action === 'JUMP' || action === 'SLIDE' || secondaryAction === 'JUMP' || secondaryAction === 'SLIDE') {
    shouldBrake = false;
  }

  isBraking = shouldBrake;

  // 2. MUSHROOM BODY VOLUNTARY VALENCE STEERING (Safe Lane Seeking)
  if (action === 'NONE' && canSwitchLanes) {
    const leftAdvantage = canSteerLeft && laneNearestDist[currentLane - 1] > 25.0 && (valences[0] > 0.20) && (valences[0] > valences[1]);
    const rightAdvantage = canSteerRight && laneNearestDist[currentLane + 1] > 25.0 && (valences[1] > 0.20) && (valences[1] > valences[0]);

    if (leftAdvantage) {
      action = 'LEFT';
      lastLaneDecisionTime = nowTime;
    } else if (rightAdvantage) {
      action = 'RIGHT';
      lastLaneDecisionTime = nowTime;
    }
  }

  // Update UI Indicators
  document.getElementById('ind-lc4').className = isLooming ? 'indicator-dot active-lc4' : 'indicator-dot';
  document.getElementById('ind-gf').className = isGiantFiberFired ? 'indicator-dot active-gf' : 'indicator-dot';
  document.getElementById('ind-opto').className = isOptomotorFired ? 'indicator-dot active-optomotor' : 'indicator-dot';

  lastActionTaken = action;
  return { action, customImpulse, secondaryAction };
}

// Action Dispatcher
function handleAction(act, customImpulse, currentDistZ) {
  if (isGameOver) return false;
  const nowT = performance.now();
  if (act === 'LEFT' && currentLane > 0) {
    currentLane--;
    targetX = LANES[currentLane];
    lastLaneChangeTime = nowT;
  } else if (act === 'RIGHT' && currentLane < 2) {
    currentLane++;
    targetX = LANES[currentLane];
    lastLaneChangeTime = nowT;
  } else if (act === 'JUMP' && !isJumping && !isSliding) {
    isJumping = true;
    velocityY = customImpulse || JUMP_IMPULSE;
    lastJumpTime = nowT;
    lastJumpDistZ = typeof currentDistZ === 'number' ? currentDistZ : 15.0;
    lastJumpImpulse = velocityY;
  } else if (act === 'SLIDE' && !isSliding && !isJumping) {
    isSliding = true;
    slideTimer = SLIDE_DURATION;
    lastSlideTime = nowT;
  } else {
    return false;
  }
  // Only actions actually accepted by the dispatcher get credit.
  if (flyBrainMode && learningEnabled) FlyRunController.tagAction(kc_eligibility, act, lastKC);
  return true;
}

// ==========================================
// 8. KEYBOARD CONTROLS & UI EVENT LISTENERS
// ==========================================
window.addEventListener('keydown', (e) => {
  if (isGameOver && (e.code === 'Space' || e.code === 'Enter')) {
    resetGame();
    return;
  }
  if (e.code === 'ArrowLeft' || e.code === 'KeyA') handleAction('LEFT');
  if (e.code === 'ArrowRight' || e.code === 'KeyD') handleAction('RIGHT');
  if (e.code === 'ArrowUp' || e.code === 'KeyW' || e.code === 'Space') handleAction('JUMP');
  if (e.code === 'ArrowDown' || e.code === 'KeyS') handleAction('SLIDE');
});

const modeBtn = document.getElementById('btn-mode');
modeBtn.addEventListener('click', () => {
  flyBrainMode = !flyBrainMode;
  document.getElementById('stat-latency').innerText = '—';
  kc_eligibility.forEach(row => row.fill(0));
  lastKC.fill(0);
  if (flyBrainMode) {
    modeBtn.classList.add('active');
    modeBtn.innerHTML = '<span>🪰 Fly Brain Mode (Auto-Pilot)</span>';
  } else {
    modeBtn.classList.remove('active');
    modeBtn.innerHTML = '<span>🎮 Manual Mode (You Play)</span>';
  }
});

document.getElementById('btn-restart').addEventListener('click', () => {
  resetGame();
});

function resetGame() {
  if (respawnCountdownTimer) {
    clearInterval(respawnCountdownTimer);
    respawnCountdownTimer = null;
  }

  kc_eligibility.forEach(row => row.fill(0));
  lastKC.fill(0);
  lastLaneDecisionTime = 0;
  currentDopamine = 0;
  trainingEpisode++;
  const epEl = document.getElementById('stat-episode');
  if (epEl) epEl.innerText = trainingEpisode;

  currentLane = 1;
  targetX = LANES[1];
  characterY = 0.0;
  velocityY = 0.0;
  isJumping = false;
  isSliding = false;
  distanceTraveled = 0.0;
  obstaclesCleared = 0;
  const clrEl = document.getElementById('stat-cleared');
  if (clrEl) clrEl.innerText = '0';
  isGameOver = false;

  // Reset biological health & speed
  flyHealth = MAX_HEALTH;
  forwardSpeed = CRUISE_SPEED;
  isBraking = false;
  invulnerableTimer = 0.0;

  const healthEl = document.getElementById('stat-health');
  if (healthEl) healthEl.innerText = '100%';
  const healthBar = document.getElementById('health-bar');
  if (healthBar) {
    healthBar.style.width = '100%';
    healthBar.style.background = '#22c55e';
  }
  const brakeBadge = document.getElementById('brake-badge');
  if (brakeBadge) brakeBadge.style.display = 'none';
  const speedEl = document.getElementById('stat-speed');
  if (speedEl) speedEl.innerText = '24.0 m/s';
  const overlay = document.getElementById('damage-overlay');
  if (overlay) overlay.style.background = 'rgba(239, 68, 68, 0)';

  obstacles.forEach(o => scene.remove(o));
  obstacles.length = 0;
  for (let i = 0; i < 6; i++) {
    spawnObstacle(-35.0 - i * 32.0);
  }

  const bestEl = document.getElementById('stat-best');
  if (bestEl) bestEl.innerText = bestDistance + ' m';

  currentEpisodeMilestones = [];
  nextMilestoneDist = 250;
  flightBlackBox.length = 0;
  lastRecordedIncident = null;

  document.getElementById('game-over-modal').style.display = 'none';
  saveSession();
  drawTelemetryChart();
}

// ==========================================
// 9. MAIN GAME LOOP
// ==========================================
let lastTime = performance.now();

function animate() {
  requestAnimationFrame(animate);

  const now = performance.now();
  const dt = Math.min(0.05, (now - lastTime) / 1000.0);
  lastTime = now;

  if (!isGameOver) {
    FlyRunController.decayEligibility(kc_eligibility, dt);
    // 0. Dynamic Aerodynamic Velocity (Forward Cruise vs Looming Air-Brake)
    const isGliding = Math.abs(playerGroup.position.x - targetX) > 0.25;
    if (isBraking) {
      forwardSpeed = Math.max(MIN_SPEED, forwardSpeed - 45.0 * dt);
    } else if (isGliding && forwardSpeed > 15.0) {
      // Turn-coordinated aerodynamic deceleration: stabilize lateral velocity
      forwardSpeed = Math.max(15.0, forwardSpeed - 28.0 * dt);
    } else {
      forwardSpeed = Math.min(CRUISE_SPEED, forwardSpeed + 22.0 * dt);
    }

    const brakeBadge = document.getElementById('brake-badge');
    if (brakeBadge) brakeBadge.style.display = isBraking ? 'inline-block' : 'none';
    const speedEl = document.getElementById('stat-speed');
    if (speedEl) speedEl.innerText = forwardSpeed.toFixed(1) + ' m/s';

    // Update invulnerability flash & homeostatic health recovery
    if (invulnerableTimer > 0.0) {
      invulnerableTimer -= dt;
      if (invulnerableTimer <= 0.0) {
        const overlay = document.getElementById('damage-overlay');
        if (overlay) overlay.style.background = 'rgba(239, 68, 68, 0)';
      }
    } else {
      // Homeostatic recovery when flying cleanly (+8% per second)
      if (flyHealth < MAX_HEALTH && !isGameOver) {
        flyHealth = Math.min(MAX_HEALTH, flyHealth + HEALTH_RECOVERY_RATE * dt);
      }
    }

    // Update Health UI
    const healthVal = Math.round(flyHealth);
    const healthEl = document.getElementById('stat-health');
    if (healthEl) healthEl.innerText = healthVal + '%';
    const healthBar = document.getElementById('health-bar');
    if (healthBar) {
      healthBar.style.width = healthVal + '%';
      healthBar.style.background = healthVal > 55 ? '#22c55e' : (healthVal > 25 ? '#f59e0b' : '#ef4444');
    }

    // 1. Advance World Distance
    const deltaDist = forwardSpeed * dt;
    distanceTraveled += deltaDist;
    document.getElementById('stat-dist').innerText = Math.floor(distanceTraveled) + ' m';

    // In-flight progress checkpoints & live chart updates
    if (distanceTraveled >= nextMilestoneDist) {
      currentEpisodeMilestones.push({
        distance: Math.floor(distanceTraveled),
        weight: parseFloat(meanAssociativeWeight.toFixed(3))
      });
      nextMilestoneDist += 250;
      drawTelemetryChart();
    } else if (now - lastChartUpdateTime > 400) {
      lastChartUpdateTime = now;
      drawTelemetryChart();
    }

    // 2. Loop Track Segments
    segments.forEach(seg => {
      seg.position.z += deltaDist;
      if (seg.position.z > trackSegmentLength) {
        seg.position.z -= trackSegmentLength * 2;
      }
    });

    // 3. Move & Recycle Obstacles
    let nearestObsInLane = null;
    let nearestDistInLane = 999.0;
    let nearestObsGlobal = null;
    let nearestDistGlobal = 999.0;

    for (let i = obstacles.length - 1; i >= 0; i--) {
      const obs = obstacles[i];
      obs.position.z += deltaDist;

      const distZ = -obs.position.z;
      if (distZ > 0) {
        if (distZ < nearestDistGlobal) {
          nearestDistGlobal = distZ;
          nearestObsGlobal = obs;
        }
        if (obs.userData.lane === currentLane && distZ < nearestDistInLane) {
          nearestDistInLane = distZ;
          nearestObsInLane = obs;
        }
      }

      // Check if cleared
      if (obs.position.z > 2.0 && !obs.userData.cleared) {
        obs.userData.cleared = true;
        obstaclesCleared++;
        document.getElementById('stat-cleared').innerText = obstaclesCleared;
        // SURVIVAL REWARD: Successful obstacle clearance delivers +0.75 PAM Dopamine!
        if (!obs.userData.collided) updateMBDopamine(0.75, 'Obstacle Cleared');
      }

      // Despawn and respawn far ahead
      if (obs.position.z > 20.0) {
        scene.remove(obs);
        obstacles.splice(i, 1);
        spawnObstacle(-160.0 - obstacleRandom() * 20.0);
      }
    }


    // Smooth Dopamine Decay towards neutral
    if (Math.abs(currentDopamine) > 0.01) {
      currentDopamine *= Math.exp(-dt / 0.325);
      const dopValEl = document.getElementById('dopamine-val');
      const dopBarEl = document.getElementById('dopamine-bar');
      if (dopValEl && dopBarEl) {
        dopValEl.innerText = (currentDopamine > 0 ? '+' : '') + currentDopamine.toFixed(2);
        const pct = Math.max(5, Math.min(95, 50 + currentDopamine * 45));
        dopBarEl.style.width = pct + '%';
        if (Math.abs(currentDopamine) < 0.06) {
          dopBarEl.style.background = '#64748b';
          dopValEl.style.color = '#94a3b8';
        }
      }
    }

    // 4. Autonomous Fly Brain Autopilot Step
    let stepAct = 'NONE';
    let stepImpulse = 0.0;
    if (flyBrainMode) {
      const controlStart = performance.now();
      const stepRes = stepBrowserController(nearestObsInLane, nearestDistInLane, now);
      document.getElementById('stat-latency').innerText = (performance.now() - controlStart).toFixed(2) + ' ms';
      stepAct = stepRes.action;
      stepImpulse = stepRes.customImpulse;
      if (stepAct !== 'NONE') {
        handleAction(stepAct, stepImpulse, nearestDistInLane);
      }
      if (stepRes.secondaryAction) {
        handleAction(stepRes.secondaryAction, stepImpulse, nearestDistInLane);
        if (stepAct === 'NONE') stepAct = stepRes.secondaryAction;
        else stepAct = `${stepAct}+${stepRes.secondaryAction}`;
      }
    }

    // 4B. 10 Hz Rolling Black Box Recorder
    sampleFlightBlackBox(now, stepAct, nearestObsInLane, nearestDistInLane);

    // 5. Update Compound Eye Visualization
    updateEyeCanvas(nearestObsInLane || nearestObsGlobal, nearestObsInLane ? nearestDistInLane : nearestDistGlobal);

    // 6. Smooth Character Lane Transition (X position)
    playerGroup.position.x += (targetX - playerGroup.position.x) * 16.0 * dt;

    // 7. Jump Physics (Y position)
    if (isJumping) {
      velocityY += GRAVITY * dt;
      characterY += velocityY * dt;
      if (characterY <= 0.0) {
        characterY = 0.0;
        velocityY = 0.0;
        isJumping = false;
      }
    }

    // 8. Slide Physics
    if (isSliding) {
      slideTimer -= dt;
      playerGroup.scale.set(1.2, 0.45, 1.2); // Crouch flat
      if (slideTimer <= 0.0) {
        isSliding = false;
        playerGroup.scale.set(1.0, 1.0, 1.0);
      }
    } else {
      playerGroup.scale.set(1.0, 1.0, 1.0);
    }
    playerGroup.position.y = 0.8 + characterY;

    // Wing flapping animation
    const wingFlap = Math.sin(now * 0.035) * 0.25;
    leftWing.rotation.z = Math.PI * 0.08 + wingFlap;
    rightWing.rotation.z = -Math.PI * 0.08 - wingFlap;

    // 9. Collision Detection & Biological Damage System
    for (let obs of obstacles) {
      const b = obs.userData.bounds;
      const dz = Math.abs(obs.position.z);
      if (dz < (b.depth / 2.0 + 0.5)) {
        const dx = Math.abs(playerGroup.position.x - b.x);
        if (dx < (b.width / 2.0 + 0.35)) {
          let collisionOccurred = false;
          let dmg = 0;

          if (obs.userData.type === 'HURDLE' && characterY < 0.6) {
            collisionOccurred = true;
            dmg = 35.0;
          } else if (obs.userData.type === 'ARCH' && !isSliding) {
            collisionOccurred = true;
            dmg = 35.0;
          } else if (obs.userData.type === 'MONOLITH') {
            collisionOccurred = true;
            dmg = 50.0;
          }

          if (collisionOccurred) obs.userData.collided = true;
          if (collisionOccurred && invulnerableTimer <= 0.0) {
            flyHealth = Math.max(0.0, flyHealth - dmg);
            invulnerableTimer = 0.55; // 550ms invulnerability grace period
            forwardSpeed = Math.max(MIN_SPEED, forwardSpeed * 0.40); // Impact deceleration

            // Deliver negative PPL1 dopamine punishment proportional to damage
            updateMBDopamine(-1.4 * (dmg / 35.0), 'Obstacle Damage');

            // Flash screen red
            const overlay = document.getElementById('damage-overlay');
            if (overlay) overlay.style.background = 'rgba(239, 68, 68, 0.45)';

            // Record Black Box incident!
            recordFlightIncident('DAMAGE', obs, dmg, Math.round(flyHealth));

            // If health is depleted, episode ends in fatal crash!
            if (flyHealth <= 0.0) {
              triggerGameOver(obs);
              break;
            }
          }
        }
      }
    }
  }

  // Rotate 3D Drosophila Brain Point Cloud HUD
  brainCloud.rotation.y += 0.015;
  brainCloud.rotation.x = Math.sin(now * 0.001) * 0.15;
  gfPulse.scale.setScalar(1.0 + Math.sin(now * 0.008) * 0.15);
  if (brainRenderer) {
    brainRenderer.render(brainScene, brainCamera);
  }

  // Render Main 3D Temple Runner
  renderer.render(scene, camera);
}

function triggerGameOver(obs) {
  if (isGameOver) return;
  isGameOver = true;
  // Collision damage already delivered punishment; do not punish twice.

  const nowTime = performance.now();
  const obsType = obs ? (obs.userData ? obs.userData.type : String(obs)) : 'UNKNOWN';
  let cause = 'COLLISION';
  let causeDetail = '';

  if (obsType === 'HURDLE') {
    const timeSinceJump = lastJumpTime > 0 ? (nowTime - lastJumpTime) / 1000.0 : 999.0;
    if (isSliding) {
      cause = 'HURDLE_SLIDE_LOCKED';
      causeDetail = 'Sliding locked out jump takeoff';
    } else if (timeSinceJump < 0.22) {
      cause = 'HURDLE_LATE_TAKEOFF';
      causeDetail = `Late takeoff (${Math.round(timeSinceJump * 1000)}ms ago, Y=${characterY.toFixed(2)}m < 0.6m)`;
    } else if (isJumping && velocityY < -5.0) {
      cause = 'HURDLE_EARLY_TAKEOFF';
      causeDetail = `Jumped too early at ${lastJumpDistZ.toFixed(1)}m; clipped hurdle on descent (Vy=${velocityY.toFixed(1)}m/s, Y=${characterY.toFixed(2)}m)`;
    } else if (lastJumpTime > 0 && (!isJumping || timeSinceJump > 0.55)) {
      cause = 'HURDLE_EARLY_LANDING';
      causeDetail = `Jumped too early at ${lastJumpDistZ.toFixed(1)}m; landed before hurdle`;
    } else if (Math.abs(playerGroup.position.x - targetX) > 0.45) {
      cause = 'HURDLE_LANE_STRADDLE';
      causeDetail = 'Straddling between lanes during lane transition';
    } else {
      cause = 'HURDLE_NO_JUMP';
      causeDetail = 'No jump initiated before impact';
    }
  } else if (obsType === 'ARCH') {
    if (isJumping) {
      cause = 'ARCH_JUMP_LOCKED';
      causeDetail = 'Airborne from jump; slide was locked out';
    } else {
      cause = 'ARCH_NO_SLIDE';
      causeDetail = 'Slide was not initiated in time';
    }
  } else if (obsType === 'MONOLITH') {
    if (Math.abs(playerGroup.position.x - targetX) > 0.45) {
      cause = 'MONOLITH_MID_TRANSITION';
      causeDetail = 'Mid-lane transition not finished in time';
    } else {
      cause = 'MONOLITH_STEER_FAILURE';
      causeDetail = 'Failed to steer out of monolith lane';
    }
  }

  // Update failure statistics
  failureStats.total++;
  failureStats[obsType] = (failureStats[obsType] || 0) + 1;
  failureStats.causes[cause] = (failureStats.causes[cause] || 0) + 1;

  const currentDist = Math.floor(distanceTraveled);
  if (currentDist > bestDistance) {
    bestDistance = currentDist;
  }
  const bestEl = document.getElementById('stat-best');
  if (bestEl) bestEl.innerText = bestDistance + ' m';

  // Record Fatal Crash Black Box incident!
  recordFlightIncident('CRASH', obs, 100.0, 0, cause, causeDetail);

  // Build failure event record
  const crashRecord = {
    episode: trainingEpisode,
    distance: currentDist,
    obstacleType: obsType,
    cause: cause,
    causeDetail: causeDetail,
    characterY: parseFloat(characterY.toFixed(3)),
    velocityY: parseFloat(velocityY.toFixed(2)),
    isJumping: isJumping,
    isSliding: isSliding,
    timeSinceJump: parseFloat(((nowTime - lastJumpTime) / 1000).toFixed(3)),
    takeoffDist: parseFloat(lastJumpDistZ.toFixed(2)),
    weight: parseFloat(meanAssociativeWeight.toFixed(3))
  };
  failureHistory.push(crashRecord);

  // Send to Python WebSocket bridge
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'CRASH_EVENT', payload: crashRecord }));
  }

  // Record completed episode into session history & persist
  sessionHistory.push({
    episode: trainingEpisode,
    distance: currentDist,
    cleared: obstaclesCleared,
    weight: parseFloat(meanAssociativeWeight.toFixed(3)),
    crash: { obstacle: obsType, cause: cause }
  });
  saveSession();
  drawTelemetryChart();

  const modalEl = document.getElementById('game-over-modal');
  const scoreEl = document.getElementById('game-over-score');
  const countdownEl = document.getElementById('countdown-num');

  // Populate Failure Diagnosis in Game Over Modal
  const causeTitleEl = document.getElementById('crash-cause-title');
  const causeDetailEl = document.getElementById('crash-cause-detail');
  const statsBarEl = document.getElementById('crash-stats-bar');

  if (causeTitleEl) {
    causeTitleEl.innerText = `💥 Collision: ${obsType} (${cause})`;
  }
  if (causeDetailEl) {
    causeDetailEl.innerText = causeDetail;
  }
  if (statsBarEl && failureStats.total > 0) {
    const hPct = Math.round(((failureStats.HURDLE || 0) / failureStats.total) * 100);
    const aPct = Math.round(((failureStats.ARCH || 0) / failureStats.total) * 100);
    const mPct = Math.round(((failureStats.MONOLITH || 0) / failureStats.total) * 100);
    statsBarEl.innerText = `Failure History (${failureStats.total} runs): 💥 Hurdle ${hPct}% | 🏹 Arch ${aPct}% | 🗿 Monolith ${mPct}%`;
  }

  modalEl.style.display = 'flex';
  scoreEl.innerText = 'Distance: ' + currentDist + ' m (Best: ' + bestDistance + ' m)';

  // 3-second countdown before auto-continuing training
  let secondsLeft = 3;
  if (countdownEl) countdownEl.innerText = secondsLeft;

  if (respawnCountdownTimer) {
    clearInterval(respawnCountdownTimer);
    respawnCountdownTimer = null;
  }

  respawnCountdownTimer = setInterval(() => {
    secondsLeft--;
    if (countdownEl) {
      countdownEl.innerText = secondsLeft;
    }
    if (secondsLeft <= 0) {
      clearInterval(respawnCountdownTimer);
      respawnCountdownTimer = null;
      resetGame();
    }
  }, 1000);
}

// Top-Left "New Session" Button Handler
const newSessionBtn = document.getElementById('btn-new-session');
if (newSessionBtn) {
  newSessionBtn.addEventListener('click', () => {
    if (confirm('Start a new training session? This will reset all learned synaptic weights to baseline.')) {
      resetSession();
    }
  });
}

// Window resize handler
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);

  if (brainRenderer && brainCanvas.clientWidth && brainCanvas.clientHeight) {
    brainCamera.aspect = brainCanvas.clientWidth / brainCanvas.clientHeight;
    brainCamera.updateProjectionMatrix();
    brainRenderer.setSize(brainCanvas.clientWidth, brainCanvas.clientHeight);
  }
});

// Black Box Inspector Modal Handlers
const bbBtn = document.getElementById('btn-blackbox');
if (bbBtn) {
  bbBtn.addEventListener('click', () => {
    renderBlackBoxModal(lastRecordedIncident);
  });
}
const bbCloseBtn = document.getElementById('btn-close-blackbox');
if (bbCloseBtn) {
  bbCloseBtn.addEventListener('click', () => {
    const modal = document.getElementById('blackbox-modal');
    if (modal) modal.style.display = 'none';
  });
}
const bbSnapBtn = document.getElementById('btn-snapshot-bb');
if (bbSnapBtn) {
  bbSnapBtn.addEventListener('click', () => {
    renderBlackBoxModal({
      incidentType: 'LIVE_SNAPSHOT',
      obstacleType: 'MANUAL_CAPTURE',
      distance: Math.floor(distanceTraveled),
      damage: 0,
      remainingHealth: Math.round(flyHealth),
      blackBox: [...flightBlackBox]
    });
  });
}

// Load any existing session from browser storage and render initial telemetry
loadSession();
drawTelemetryChart();

// Start loop
animate();
