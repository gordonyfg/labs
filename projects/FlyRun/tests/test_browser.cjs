const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const controller = require('../sim/web_runner/controller_utils.js');
const source = fs.readFileSync(path.join(__dirname, '../sim/web_runner/game.js'), 'utf8');
function functionSource(name, nextMarker) {
  const start = source.indexOf('function ' + name + '(');
  return source.slice(start, source.indexOf(nextMarker, start));
}
function obstacle(type, x, dz) {
  return {position: {z: -dz}, userData: {type, lane: x < 0 ? 0 : x > 0 ? 2 : 1,
    bounds: {x, width: 1.5, depth: 1}}};
}

test('eligibility decay follows elapsed time at 30, 60 and 144 FPS', () => {
  for (const fps of [30, 60, 144]) {
    const e = [new Float32Array([1])];
    for (let frame = 0; frame < fps; frame++) controller.decayEligibility(e, 1/fps);
    assert.ok(Math.abs(e[0][0] - Math.exp(-1)) < 1e-6);
  }
});
test('sparse code caps tied activity and allows silence', () => {
  const code = controller.sparseCode(new Float32Array(128).fill(1), 9, 1);
  assert.equal(code.filter(x => x > 0).length, 9);
  assert.equal(controller.sparseCode(new Float32Array(128), 9, 1).filter(x => x > 0).length, 0);
});
test('turning ignores obstacles outside the swept path', () => {
  assert.equal(controller.transitionAction([obstacle('HURDLE', 3.2, 5)], -2, 0, false, false), null);
});
test('nearest posture wins regardless of obstacle order', () => {
  const hazards = [obstacle('HURDLE', 0, 9), obstacle('ARCH', -3.2, 5)];
  assert.equal(controller.transitionAction(hazards, -3.2, 0, false, false), 'SLIDE');
  assert.equal(controller.transitionAction(hazards.reverse(), -3.2, 0, false, false), 'SLIDE');
  assert.equal(controller.transitionAction(hazards, -3.2, 0, true, false), null);
});
test('actual policy does not jump for an unrelated lane while turning', () => {
  const ctx = {Float32Array, Math, FlyRunController:controller, document:{getElementById:()=>({})},
    forwardSpeed:24, obstacles:[obstacle('HURDLE',3.2,5)],
    getSensoryProjectionNeurons:()=>[], stepMushroomBodyNetwork:()=>({kc:new Float32Array(128),valences:[0,0,0,0]}),
    lastLaneDecisionTime:0, playerGroup:{position:{x:-2}}, targetX:0, currentLane:1,
    isJumping:false, isSliding:false};
  vm.createContext(ctx);
  vm.runInContext(functionSource('stepBrowserController', '// Action Dispatcher'),ctx);
  const result = ctx.stepBrowserController(null,999,1000);
  assert.equal(result.action, 'NONE');
  assert.equal(result.secondaryAction, null);
});
test('rejected repeated jump requests never receive extra learning credit', () => {
  const traces = Array.from({length:4},()=>new Float32Array(128));
  const ctx = {performance:{now:()=>1000}, isGameOver:false, currentLane:1, LANES:[-3.2,0,3.2],
    isJumping:false, isSliding:false, JUMP_IMPULSE:16.5, SLIDE_DURATION:0.55,
    flyBrainMode:true, learningEnabled:true, FlyRunController:controller,
    kc_eligibility:traces, lastKC:new Float32Array(128).fill(1)};
  vm.createContext(ctx);
  vm.runInContext(functionSource('handleAction', '// =========================================='),ctx);
  assert.equal(ctx.handleAction('JUMP'), true);
  const tagged = traces[2][0];
  assert.equal(ctx.handleAction('JUMP'), false);
  assert.equal(traces[2][0], tagged);
  assert.equal(ctx.handleAction('SLIDE'), false);
  assert.equal(traces[3][0], 0);
});
