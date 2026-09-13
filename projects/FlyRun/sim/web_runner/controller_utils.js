/* Pure controller primitives, shared by gameplay and the Node regression tests. */
(function (root) {
  'use strict';
  const api = {
    decayEligibility(rows, dtSeconds, tauSeconds = 1.0) {
      if (!(dtSeconds >= 0) || !(tauSeconds > 0)) throw new RangeError('Invalid trace timing');
      const decay = Math.exp(-dtSeconds / tauSeconds);
      for (const row of rows) for (let k = 0; k < row.length; k++) row[k] *= decay;
    },
    tagAction(rows, action, kc) {
      const index = ['LEFT', 'RIGHT', 'JUMP', 'SLIDE'].indexOf(action);
      if (index >= 0) for (let k = 0; k < kc.length; k++) rows[index][k] += 0.35 * kc[k];
    },
    transitionAction(obstacles, fromX, toX, jumping, sliding) {
      // Match the collision detector's horizontal player half-width. Consider
      // the whole lateral segment and resolve posture by nearest collision face.
      const relevant = obstacles.filter(obs => {
        const b = obs.userData.bounds;
        const dz = -obs.position.z;
        return !obs.userData.cleared && b && dz > 0 && dz < 11 &&
          b.x + b.width / 2 + 0.35 > Math.min(fromX, toX) &&
          b.x - b.width / 2 - 0.35 < Math.max(fromX, toX);
      }).sort((a, b) => (-a.position.z - a.userData.bounds.depth / 2) -
                             (-b.position.z - b.userData.bounds.depth / 2) ||
                             a.userData.type.localeCompare(b.userData.type));
      if (jumping || sliding) return null;
      for (const obs of relevant) {
        if (obs.userData.type === 'HURDLE') return 'JUMP';
        if (obs.userData.type === 'ARCH') return 'SLIDE';
      }
      return null;
    },
    sparseCode(excitation, limit, divisor) {
      const winners = Array.from(excitation, (v, i) => i)
        .sort((a, b) => excitation[b] - excitation[a] || a - b).slice(0, limit);
      const kc = new Float32Array(excitation.length);
      for (const k of winners) if (excitation[k] > 0.04) kc[k] = Math.min(1, excitation[k] / divisor);
      return kc;
    },
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.FlyRunController = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
