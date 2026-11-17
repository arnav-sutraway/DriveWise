import { useEffect, useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Line, OrbitControls } from '@react-three/drei';
import { getParkingScenario, parkingScenarios } from '../data/parkingScenarios.js';
import {
  getParkingDuration,
  getParkingFrame,
  getParkingStepIndex,
  getParkingStepStart,
  sampleParkingPath,
} from '../logic/parkingAnimation.js';
import VehicleModel from './VehicleModel.jsx';

const VEHICLE_WIDTH = 1.18;
const VEHICLE_LENGTH = 2.3;
const BAY_WIDTH = 2.5;
const BAY_DEPTH = 5.2;
const BAY_CENTER_Z = 2.1;
const BAY_OFFSETS = [-2.85, 0, 2.85];

function ParkingLine({ position, size, color = '#f3f5ed' }) {
  return (
    <mesh position={position} receiveShadow>
      <boxGeometry args={size} />
      <meshStandardMaterial color={color} roughness={0.9} />
    </mesh>
  );
}

function StaticVehicle({ vehicle }) {
  return (
    <group position={[vehicle.position[0], 0, vehicle.position[1]]} rotation={[0, vehicle.rotation, 0]}>
      <VehicleModel
        color={vehicle.color}
        width={VEHICLE_WIDTH}
        length={VEHICLE_LENGTH}
        wheels
      />
    </group>
  );
}

function ParkingLot({ scenario }) {
  const { layout } = scenario;
  const bayAngle = layout.bayAngle ?? 0;
  const targetFill = (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.012, 0]}>
      <planeGeometry args={[BAY_WIDTH - 0.12, BAY_DEPTH - 0.12]} />
      <meshBasicMaterial color="#dcae59" transparent opacity={0.17} depthWrite={false} />
    </mesh>
  );

  return (
    <>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.08, 0]} receiveShadow>
        <planeGeometry args={[24, 16]} />
        <meshStandardMaterial color="#535f62" roughness={0.94} />
      </mesh>
      <mesh position={[0, -0.025, -3.1]} receiveShadow>
        <boxGeometry args={[24, 0.03, 5.8]} />
        <meshStandardMaterial color="#4b585c" roughness={0.94} />
      </mesh>
      {layout.kind === 'parallel' ? (
        <>
          <ParkingLine position={[0, 0.055, -0.85]} size={[22, 0.1, 0.16]} color="#bbc5c4" />
          <ParkingLine position={[0, 0.025, 4.25]} size={[22, 0.035, 0.07]} color="#e2e8e4" />
          <ParkingLine position={[0, 0.025, 0.3]} size={[22, 0.035, 0.06]} color="#d8dfdd" />
          <group position={[0, 0, -2.15]}>
            {targetFill}
            {[-2.6, 2.6].map((x) => (
              <ParkingLine key={x} position={[x, 0.028, 0]} size={[0.07, 0.035, 2.45]} />
            ))}
            {[-1.22, 1.22].map((z) => (
              <ParkingLine key={z} position={[0, 0.028, z]} size={[5.2, 0.035, 0.07]} />
            ))}
          </group>
          {layout.parkedCars.map((vehicle) => (
            <StaticVehicle key={vehicle.position[0]} vehicle={vehicle} />
          ))}
        </>
      ) : (
        <group rotation={[0, bayAngle, 0]}>
          {BAY_OFFSETS.map((offset) => (
            <group key={offset} position={[offset, 0, BAY_CENTER_Z]}>
              {offset === 0 && targetFill}
              {[-BAY_WIDTH / 2, BAY_WIDTH / 2].map((x) => (
                <ParkingLine
                  key={x}
                  position={[x, 0.028, 0]}
                  size={[0.07, 0.035, BAY_DEPTH]}
                />
              ))}
              <ParkingLine
                position={[0, 0.028, BAY_DEPTH / 2]}
                size={[BAY_WIDTH, 0.035, 0.07]}
              />
            </group>
          ))}
          {layout.parkedCars.map((vehicle) => (
            <StaticVehicle key={vehicle.position[0]} vehicle={vehicle} />
          ))}
        </group>
      )}
    </>
  );
}

function ParkingPath({ scenario }) {
  return scenario.steps.map((step, index) => {
    if (!step.motion) return null;
    const samples = sampleParkingPath(step.motion);
    const points = samples.map(([x, z]) => [x, 0.075, z]);
    const arrowIndex = Math.floor(samples.length * 0.68);
    const point = samples[arrowIndex];
    const nextPoint = samples[arrowIndex + 1];
    const arrowYaw = Math.atan2(nextPoint[0] - point[0], nextPoint[1] - point[1]);
    const color = step.motion.direction === 'reverse' ? '#e79b53' : '#8cc7b1';

    return (
      <group key={`${scenario.id}-${index}`}>
        <Line points={points} color={color} lineWidth={2.2} transparent opacity={0.82} />
        <mesh
          position={[point[0], 0.105, point[1]]}
          rotation={[Math.PI / 2, arrowYaw, 0]}
        >
          <coneGeometry args={[0.12, 0.3, 8]} />
          <meshBasicMaterial color={color} />
        </mesh>
      </group>
    );
  });
}

function MovingVehicle({ scenario, elapsed }) {
  const ref = useRef(null);
  const frame = getParkingFrame(scenario.id, elapsed);

  useFrame((_, delta) => {
    if (!ref.current) return;
    const amount = 1 - Math.exp(-delta * 18);
    ref.current.position.x += (frame.position[0] - ref.current.position.x) * amount;
    ref.current.position.z += (frame.position[1] - ref.current.position.z) * amount;
    let angle = frame.yaw - ref.current.rotation.y;
    angle = ((angle + Math.PI) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2) - Math.PI;
    ref.current.rotation.y += angle * amount;
  });

  return (
    <group
      ref={ref}
      position={[frame.position[0], 0.025, frame.position[1]]}
      rotation={[0, frame.yaw, 0]}
    >
      <VehicleModel color="#e9a23b" width={VEHICLE_WIDTH} length={VEHICLE_LENGTH} wheels />
    </group>
  );
}

function ParkingScene({ scenario, elapsed }) {
  return (
    <>
      <color attach="background" args={['#e8eff0']} />
      <ambientLight intensity={1.35} />
      <directionalLight position={[5, 10, 7]} intensity={1.8} castShadow />
      <ParkingLot scenario={scenario} />
      <ParkingPath scenario={scenario} />
      <MovingVehicle scenario={scenario} elapsed={elapsed} />
      <OrbitControls
        enablePan={false}
        minDistance={8}
        maxDistance={21}
        maxPolarAngle={Math.PI / 2.12}
      />
    </>
  );
}

export default function ParkingSimulator({
  scenarioId = 'parallel',
  onScenarioChange,
  autoPlayRequest = false,
  onAutoPlayRequestConsumed,
}) {
  const scenario = getParkingScenario(scenarioId);
  const duration = getParkingDuration(scenarioId);
  const [elapsed, setElapsed] = useState(0);
  const [playing, setPlaying] = useState(false);
  const elapsedRef = useRef(0);
  const autoPlayStarted = useRef(false);
  const currentStepIndex = getParkingStepIndex(scenarioId, elapsed);
  const currentStep = scenario.steps[currentStepIndex];

  const seek = (time) => {
    const nextTime = Math.max(0, Math.min(time, duration));
    elapsedRef.current = nextTime;
    setElapsed(nextTime);
  };

  useEffect(() => {
    setPlaying(false);
    seek(0);
  }, [scenarioId]);

  useEffect(() => {
    if (!autoPlayRequest) {
      autoPlayStarted.current = false;
      return;
    }
    if (autoPlayStarted.current) return;
    autoPlayStarted.current = true;
    setPlaying(false);
    seek(0);
    setPlaying(true);
    onAutoPlayRequestConsumed?.();
  }, [autoPlayRequest, scenarioId]);

  useEffect(() => {
    if (!playing) return undefined;

    const startedAt = performance.now() - elapsedRef.current;
    let frameId;
    const advance = (now) => {
      const nextTime = Math.min(now - startedAt, duration);
      elapsedRef.current = nextTime;
      setElapsed(nextTime);
      if (nextTime >= duration) {
        setPlaying(false);
        return;
      }
      frameId = window.requestAnimationFrame(advance);
    };

    frameId = window.requestAnimationFrame(advance);
    return () => window.cancelAnimationFrame(frameId);
  }, [playing, duration]);

  const restart = () => {
    setPlaying(false);
    seek(0);
  };

  const togglePlayback = () => {
    if (playing) {
      setPlaying(false);
      return;
    }
    if (elapsed >= duration) seek(0);
    setPlaying(true);
  };

  const advanceStep = () => {
    setPlaying(false);
    const nextStart = getParkingStepStart(scenarioId, currentStepIndex + 1);
    seek(nextStart);
  };

  const previousStep = () => {
    setPlaying(false);
    seek(getParkingStepStart(scenarioId, Math.max(0, currentStepIndex - 1)));
  };

  return (
    <section className="panel parking-panel" id="parking-simulator" aria-labelledby="parking-heading">
      <div className="panel-heading parking-heading">
        <div>
          <span className="section-kicker">INTERACTIVE PARKING LESSON</span>
          <h2 id="parking-heading">Choose a parking technique</h2>
          <p>Follow the path, watch the steering cue, and move through each step at your own pace.</p>
        </div>
        <span className="scene-live"><span />3D walkthrough</span>
      </div>

      <div className="parking-techniques" role="tablist" aria-label="Parking techniques">
        {parkingScenarios.map((option) => (
          <button
            key={option.id}
            type="button"
            className={`parking-technique${option.id === scenarioId ? ' parking-technique-active' : ''}`}
            role="tab"
            aria-selected={option.id === scenarioId}
            onClick={() => onScenarioChange?.(option.id)}
          >
            <strong>{option.title}</strong>
            <span>{option.subtitle}</span>
          </button>
        ))}
      </div>

      <p className="parking-summary">{scenario.description}</p>

      <div className="parking-layout">
        <div className="parking-visual-column">
          <div className="parking-scene-canvas" aria-label={`${scenario.title} 3D demonstration`}>
            <Canvas camera={{ position: [0, 16, 13], fov: 45 }} shadows>
              <ParkingScene scenario={scenario} elapsed={elapsed} />
            </Canvas>
            <div className="parking-scene-label">
              <span>{scenario.title}</span>
              <b>{currentStep.direction}</b>
            </div>
            <div className="parking-scene-hint">Drag to orbit · Scroll to zoom</div>
          </div>
          <div className="parking-playback">
            <div className="parking-status" aria-live="polite">
              <span className="parking-status-dot" />
              <strong>Step {currentStepIndex + 1} of {scenario.steps.length}</strong>
              <span>{currentStep.title}</span>
            </div>
            <div className="parking-cue-row">
              <span className="parking-cue">{currentStep.direction === 'Reverse' ? '↶' : '↗'} {currentStep.direction}</span>
              <span className="parking-cue">Steering: {currentStep.steering}</span>
            </div>
            <div
              className="parking-progress"
              role="progressbar"
              aria-label="Demonstration progress"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round((elapsed / duration) * 100)}
            >
              <span style={{ width: `${(elapsed / duration) * 100}%` }} />
            </div>
            <div className="parking-controls">
              <button type="button" className="action-button" onClick={togglePlayback}>
                {playing ? 'Pause' : elapsed >= duration ? 'Replay' : '▶  Play'}
              </button>
              <button type="button" className="parking-secondary-button" onClick={restart}>Restart</button>
              <div className="parking-step-controls">
                <button
                  type="button"
                  className="parking-secondary-button"
                  onClick={previousStep}
                  disabled={currentStepIndex === 0 && elapsed === 0}
                >
                  Previous step
                </button>
                <button
                  type="button"
                  className="parking-secondary-button"
                  onClick={advanceStep}
                  disabled={currentStepIndex >= scenario.steps.length - 1}
                >
                  Next step
                </button>
              </div>
            </div>
          </div>
        </div>

        <aside className="parking-instructions" aria-label={`${scenario.title} instructions`}>
          <div className="parking-instruction-heading">
            <span className="section-kicker">THE MANEUVER</span>
            <h3>{scenario.title}</h3>
          </div>
          <ol className="parking-step-list">
            {scenario.steps.map((step, index) => (
              <li key={step.title}>
                <button
                  type="button"
                  className={`parking-step${index === currentStepIndex ? ' parking-step-active' : ''}`}
                  aria-current={index === currentStepIndex ? 'step' : undefined}
                  onClick={() => {
                    setPlaying(false);
                    seek(getParkingStepStart(scenarioId, index));
                  }}
                >
                  <span className="parking-step-number">{String(index + 1).padStart(2, '0')}</span>
                  <span className="parking-step-copy">
                    <strong>{step.title}</strong>
                    <span>{step.instruction}</span>
                  </span>
                </button>
              </li>
            ))}
          </ol>
          <div className="parking-guidance">
            <h4>Safety checks</h4>
            <p>{scenario.safety}</p>
          </div>
          <div className="parking-guidance">
            <h4>Common mistakes</h4>
            <ul>{scenario.mistakes.map((mistake) => <li key={mistake}>{mistake}</li>)}</ul>
          </div>
          <div className="parking-guidance parking-recognition">
            <h4>How to recognize a good finish</h4>
            <p>{scenario.recognition}</p>
          </div>
          <p className="parking-source">
            <strong>Georgia DDS source:</strong> {scenario.source}
            <span>{scenario.sourceNote}</span>
          </p>
        </aside>
      </div>
    </section>
  );
}
