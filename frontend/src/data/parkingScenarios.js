const parallel = {
  id: 'parallel',
  title: 'Parallel parking',
  subtitle: 'Reverse into a curbside space',
  description: 'Ease into a space between two vehicles, then finish parallel to the curb.',
  layout: {
    kind: 'parallel',
    targetCenter: [0, -1.55],
    targetYaw: Math.PI / 2,
    parkedCars: [
      { position: [4.1, -2.15], rotation: Math.PI / 2, color: '#728d98' },
      { position: [-4.1, -2.15], rotation: Math.PI / 2, color: '#b77954' },
    ],
  },
  steps: [
    {
      title: 'Approach and signal',
      instruction: 'Signal, then stop 2–3 feet parallel to the vehicle ahead. The guide uses the rear tire and that vehicle’s rear bumper as a reference.',
      direction: 'Forward',
      steering: 'Wheels straight',
      durationMs: 3800,
      motion: {
        from: [-6.5, 1.9], control1: [-3.8, 1.9], control2: [0.6, 1.9], to: [3.65, 1.9],
        direction: 'forward',
      },
    },
    {
      title: 'Check, then reverse toward the space',
      instruction: 'Check traffic behind and your path. Reverse slowly, steering toward the space; pause when your side mirror reaches the parked car’s rear-bumper reference.',
      direction: 'Reverse',
      steering: 'Steer toward the space',
      durationMs: 2100,
      motion: {
        from: [3.65, 1.9], control1: [2.55, 1.9], control2: [1.72, -0.15], to: [1.7, -1.1],
        direction: 'reverse',
      },
    },
    {
      title: 'Counter-steer and straighten',
      instruction: 'Continue backing slowly while steering the opposite way. Use quick checks to the front and rear until the wheels are straight.',
      direction: 'Reverse',
      steering: 'Steer away from the space, then straighten',
      durationMs: 2100,
      motion: {
        from: [1.7, -1.1], control1: [1.68, -1.42], control2: [0.55, -1.55], to: [0, -1.55],
        direction: 'reverse',
      },
    },
    {
      title: 'Center and finish',
      instruction: 'Finish centered between the vehicles. The Georgia DDS guide describes the wheels 6–12 inches from the curb.',
      direction: 'Stopped',
      steering: 'Wheels straight',
      durationMs: 900,
    },
  ],
  safety: 'Practice in a level, empty lot first. Signal, check mirrors before slowing, scan the full path and all four corners, and keep the vehicle at a slow controlled speed.',
  mistakes: [
    'Skipping the traffic and path check before reversing.',
    'Turning too quickly or failing to counter-steer and straighten.',
    'Stopping too close to another vehicle or leaving the car far from the curb.',
  ],
  recognition: 'The car is parallel to the curb, centered between the vehicles, with straight wheels and the guide’s 6–12 inch wheel-to-curb spacing.',
  source: 'Georgia DDS 2024–2025 Parent/Teen Driving Guide, “Parking,” PDF pp. 21–22.',
  sourceNote: 'The guide asks learners to practice in a large, level lot free of obstacles and to use reference points and commentary driving.',
};

const perpendicular = {
  id: 'perpendicular',
  title: 'Straight / 90° parking',
  subtitle: 'Pull forward into a standard space',
  description: 'Approach a marked 90-degree space, turn in at low speed, and center the vehicle.',
  layout: {
    kind: 'perpendicular',
    targetCenter: [0, 3.45],
    targetYaw: 0,
    parkedCars: [
      { position: [-2.85, 2.3], rotation: 0, color: '#728d98' },
      { position: [2.85, 2.3], rotation: 0, color: '#b77954' },
    ],
  },
  steps: [
    {
      title: 'Signal and set up',
      instruction: 'Signal and establish the guide’s 5–6 foot approach distance. Use a vehicle reference point to judge when to begin the turn.',
      direction: 'Forward',
      steering: 'Wheels straight',
      durationMs: 1900,
      motion: {
        from: [-1.65, -5.2], control1: [-1.65, -3.8], control2: [-1.2, -2.3], to: [-1.2, -1.2],
        direction: 'forward',
      },
    },
    {
      title: 'Turn toward the center',
      instruction: 'Check traffic and your path, then turn at a controlled speed toward the center of the space. Straighten the wheels as the car aligns.',
      direction: 'Forward',
      steering: 'Turn into the space, then straighten',
      durationMs: 2800,
      motion: {
        from: [-1.2, -1.2], control1: [-1.2, 0.3], control2: [0, 1.65], to: [0, 3.45],
        direction: 'forward',
      },
    },
    {
      title: 'Stop centered',
      instruction: 'Finish centered between the lines. The guide places the front bumper 3–6 inches from the curb or end of the space.',
      direction: 'Stopped',
      steering: 'Wheels straight',
      durationMs: 900,
    },
  ],
  safety: 'Signal before turning, check traffic and the full path of travel, watch all four corners, and steer at a controlled speed.',
  mistakes: [
    'Starting the turn before judging the space and approach reference.',
    'Turning too fast or focusing on only one corner of the vehicle.',
    'Finishing crooked, off-center, or too close to the end of the space.',
  ],
  recognition: 'The car sits centered between the parallel lines, faces straight into the bay, and has the guide’s 3–6 inch front-bumper clearance.',
  source: 'Georgia DDS 2024–2025 Parent/Teen Driving Guide, “Perpendicular Parking,” PDF pp. 21–22.',
  sourceNote: 'The guide describes a forward entry into a 90-degree space and recommends practice in a large, level lot free of obstacles.',
};

const reverse = {
  id: 'reverse',
  title: 'Reverse parking',
  subtitle: 'Back into a perpendicular space',
  description: 'Start in a clear aisle with the rear aimed toward the bay, then back slowly into the marked space.',
  layout: {
    kind: 'perpendicular',
    targetCenter: [0, 3.45],
    targetYaw: 0,
    startPosition: [2, -1.8],
    startYaw: Math.PI,
    parkedCars: [
      { position: [-2.85, 2.3], rotation: 0, color: '#728d98' },
      { position: [2.85, 2.3], rotation: 0, color: '#b77954' },
    ],
  },
  steps: [
    {
      title: 'Start in the clear aisle',
      instruction: 'Begin with the nose facing away from the bay and the rear aimed toward it. Check the aisle, traffic, and full path behind you before shifting to reverse.',
      direction: 'Stopped',
      steering: 'Wheels straight',
      durationMs: 1200,
    },
    {
      title: 'Reverse into the space',
      instruction: 'Shift to reverse only after stopping. Back slowly while steering toward the center; keep checking behind and along the full path.',
      direction: 'Reverse',
      steering: 'Steer toward the space, then unwind',
      durationMs: 3000,
      motion: {
        from: [2, -1.8], control1: [2, 0], control2: [0, 1.7], to: [0, 3.45],
        direction: 'reverse',
      },
    },
    {
      title: 'Stop centered',
      instruction: 'Stop when aligned within the lines. This reverse-in path is a practice variation; the Georgia DDS guide’s perpendicular-entry steps describe pulling forward into the space.',
      direction: 'Stopped',
      steering: 'Wheels straight',
      durationMs: 900,
    },
  ],
  safety: 'This is a low-speed spatial-awareness demonstration, not an official Georgia reverse-in sequence. Practice only in a clear, level lot with an instructor; check traffic and the entire path before every movement.',
  mistakes: [
    'Reversing before checking behind and along the full path.',
    'Beginning the maneuver without enough clear aisle around the vehicle.',
    'Assuming the forward-entry reference points in the DDS guide are interchangeable with a reverse-in setup.',
  ],
  recognition: 'The vehicle is fully inside the bay, centered between both lines, aligned with the space, and stopped with the path clear.',
  source: 'Georgia DDS 2024–2025 Parent/Teen Driving Guide, “Perpendicular Parking,” PDF pp. 21–22 (forward-entry guidance).',
  sourceNote: 'The guide does not prescribe this reverse-in setup; the animation is labeled as a practice variation rather than an official DDS procedure.',
};

const angle = {
  id: 'angle',
  title: 'Angle parking',
  subtitle: 'Pull forward into a diagonal space',
  description: 'Signal, approach the diagonal bay, and turn toward its center at a slow controlled speed.',
  layout: {
    kind: 'angle',
    targetCenter: [-1.595, 3.06],
    targetYaw: -0.48,
    bayAngle: -0.48,
    parkedCars: [
      { position: [-2.85, 2.3], rotation: 0, color: '#728d98' },
      { position: [2.85, 2.3], rotation: 0, color: '#b77954' },
    ],
  },
  steps: [
    {
      title: 'Signal and approach',
      instruction: 'Signal and approach about 3–4 feet from the space. Move slowly until the steering wheel reaches the first pavement line.',
      direction: 'Forward',
      steering: 'Wheels straight',
      durationMs: 1800,
      motion: {
        from: [0, -5.2], control1: [0, -3.9], control2: [0, -2.4], to: [0, -1.2],
        direction: 'forward',
      },
    },
    {
      title: 'Turn toward the target',
      instruction: 'Locate the center of the space, check traffic and the path, then steer toward that target at a slow controlled speed.',
      direction: 'Forward',
      steering: 'Turn into the diagonal space',
      durationMs: 2700,
      motion: {
        from: [0, -1.2], control1: [0, -0.1], control2: [-1.13, 2.17], to: [-1.595, 3.06],
        direction: 'forward',
      },
    },
    {
      title: 'Straighten and finish',
      instruction: 'Steer toward the center to straighten the wheels. Stop with the front bumper 3–6 inches from the curb or end of the bay.',
      direction: 'Stopped',
      steering: 'Wheels straight',
      durationMs: 900,
    },
  ],
  safety: 'Signal, check traffic and the full path before turning, scan all four corners, and keep the vehicle at a slow controlled speed.',
  mistakes: [
    'Approaching too close to the space or turning before checking the path.',
    'Aiming at a line instead of the center target.',
    'Failing to straighten the wheels or stopping too close to the end.',
  ],
  recognition: 'The car follows the diagonal lines, sits centered within them, and stops with the guide’s 3–6 inch front-bumper clearance.',
  source: 'Georgia DDS 2024–2025 Parent/Teen Driving Guide, “Angle Parking,” PDF pp. 21–22.',
  sourceNote: 'The guide’s sequence uses a reference point, a center target, slow controlled steering, and a 3–6 inch front-bumper clearance.',
};

export const parkingScenarios = [parallel, perpendicular, reverse, angle];

export function getParkingScenario(scenarioId) {
  const scenario = parkingScenarios.find(({ id }) => id === scenarioId);
  if (!scenario) throw new RangeError(`Unknown parking scenario: ${scenarioId}`);
  return scenario;
}
