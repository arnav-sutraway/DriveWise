import { useEffect, useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { getAnimationPhase, resolveRightOfWay } from '../logic/rightOfWay.js';
import VehicleModel from './VehicleModel.jsx';

const approaches = [
  { id: 'N-1', name: 'North', approachPosition: [0, 0, -4.8], position: [0, 0, -3.2], rotation: 0, color: '#3d8fd1', move: [0, 0, 1.1] },
  { id: 'E-1', name: 'East', approachPosition: [4.8, 0, 0], position: [3.2, 0, 0], rotation: Math.PI / 2, color: '#e9a23b', move: [-1.1, 0, 0] },
  { id: 'S-1', name: 'South', approachPosition: [0, 0, 4.8], position: [0, 0, 3.2], rotation: Math.PI, color: '#47a982', move: [0, 0, -1.1] },
  { id: 'W-1', name: 'West', approachPosition: [-4.8, 0, 0], position: [-3.2, 0, 0], rotation: -Math.PI / 2, color: '#9a72c7', move: [1.1, 0, 0] },
];
const DEMO_DURATION = 8000;

function Road() {
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.07, 0]} receiveShadow>
        <planeGeometry args={[15, 15]} /><meshStandardMaterial color="#a8c992" />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
        <planeGeometry args={[3.5, 15]} /><meshStandardMaterial color="#454f58" />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, 0]}>
        <planeGeometry args={[15, 3.5]} /><meshStandardMaterial color="#454f58" />
      </mesh>
      {[-2.05, 2.05].map((offset) => (
        <group key={offset}>
          <mesh position={[0, 0.045, offset]} receiveShadow>
            <boxGeometry args={[15, 0.08, 0.38]} /><meshStandardMaterial color="#cbd3d6" />
          </mesh>
          <mesh position={[offset, 0.045, 0]} receiveShadow>
            <boxGeometry args={[0.38, 0.08, 15]} /><meshStandardMaterial color="#cbd3d6" />
          </mesh>
        </group>
      ))}
      {[-1.88, 1.88].map((x) => [-1.88, 1.88].map((z) => (
        <mesh key={`${x}-${z}`} rotation={[-Math.PI / 2, 0, 0]} position={[x, 0.012, z]}>
          <planeGeometry args={[0.7, 0.08]} /><meshStandardMaterial color="#f4f7fa" />
        </mesh>
      )))}
      {[[-2.65, 0, 0.08, 1.8], [2.65, 0, 0.08, 1.8], [0, -2.65, 1.8, 0.08], [0, 2.65, 1.8, 0.08]].map(([x, z, w, h]) => (
        <mesh key={`${x}-${z}`} rotation={[-Math.PI / 2, 0, 0]} position={[x, 0.025, z]}>
          <planeGeometry args={[w, h]} /><meshStandardMaterial color="#f8fafc" />
        </mesh>
      ))}
      <mesh position={[0, 0.17, 0]}><boxGeometry args={[1.3, 0.28, 1.3]} /><meshStandardMaterial color="#dce8f0" /></mesh>
      {[
        [-4.7, -4.5, '#d7c6a1'], [4.6, -4.4, '#a7c7b2'], [-4.6, 4.5, '#c2d0e3'], [4.8, 4.6, '#e3c9b9'],
      ].map(([x, z, color]) => (
        <group key={`${x}-${z}`} position={[x, 0, z]}>
          <mesh position={[0, 0.55, 0]}><boxGeometry args={[1.5, 1.1, 1.4]} /><meshStandardMaterial color={color} /></mesh>
          <mesh position={[0, 1.25, 0]}><coneGeometry args={[1.05, 0.8, 4]} /><meshStandardMaterial color="#ab7557" /></mesh>
        </group>
      ))}
      {[
        [-5.2, 2.7], [5.2, 2.7], [-5.2, -2.7], [5.2, -2.7],
      ].map(([x, z]) => (
        <group key={`${x}-${z}`} position={[x, 0, z]}>
          <mesh position={[0, 0.32, 0]} castShadow><cylinderGeometry args={[0.09, 0.13, 0.64, 6]} /><meshStandardMaterial color="#8f694c" /></mesh>
          <mesh position={[0, 1.05, 0]} castShadow><coneGeometry args={[0.58, 1.1, 6]} /><meshStandardMaterial color="#608c62" /></mesh>
          <mesh position={[0, 1.65, 0]} castShadow><coneGeometry args={[0.42, 0.85, 6]} /><meshStandardMaterial color="#719d70" /></mesh>
        </group>
      ))}
    </group>
  );
}

function Vehicle({ vehicle, phase, firstVehicle, elapsed }) {
  const ref = useRef(null);
  const isHighlighted = vehicle.id === firstVehicle && (phase === 'right-of-way' || phase === 'proceeding' || phase === 'complete');
  useFrame((state) => {
    if (!ref.current) return;
    const approachDuration = vehicle.id === firstVehicle ? 1000 : 1600;
    const approachProgress = Math.min(elapsed / approachDuration, 1);
    const targetX = vehicle.approachPosition[0]
      + (vehicle.position[0] - vehicle.approachPosition[0]) * approachProgress;
    const targetZ = vehicle.approachPosition[2]
      + (vehicle.position[2] - vehicle.approachPosition[2]) * approachProgress;
    const shouldMove = (phase === 'proceeding' || phase === 'complete') && vehicle.id === firstVehicle;
    const proceedProgress = shouldMove ? Math.min((elapsed - 3800) / 3400, 1) : 0;
    const easing = 1 - Math.exp(-state.clock.getDelta() * 2.4);
    ref.current.position.x += (targetX + vehicle.move[0] * 5.2 * proceedProgress - ref.current.position.x) * easing;
    ref.current.position.z += (targetZ + vehicle.move[2] * 5.2 * proceedProgress - ref.current.position.z) * easing;
  });
  return (
    <group ref={ref} position={vehicle.approachPosition} rotation={[0, vehicle.rotation, 0]}>
      <VehicleModel color={vehicle.color} highlight={isHighlighted} />
    </group>
  );
}

function Scene({ phase, firstVehicle, elapsed }) {
  return (
    <>
      <color attach="background" args={['#e9f1f5']} />
      <ambientLight intensity={1.35} />
      <directionalLight position={[5, 8, 5]} intensity={2} castShadow />
      <Road />
      {approaches.map((vehicle) => (
        <Vehicle key={vehicle.id} vehicle={vehicle} phase={phase} firstVehicle={firstVehicle} elapsed={elapsed} />
      ))}
      <OrbitControls enablePan={false} minDistance={8} maxDistance={18} maxPolarAngle={Math.PI / 2.15} />
    </>
  );
}

export default function IntersectionScene({ scenarioId, autoPlayKey = 0 }) {
  const decision = resolveRightOfWay(scenarioId);
  const [elapsed, setElapsed] = useState(0);
  const [running, setRunning] = useState(false);
  const lastAutoPlayKey = useRef(autoPlayKey);
  const phase = getAnimationPhase(scenarioId, elapsed);
  const phaseName = phase === 'approaching'
    ? 'Vehicles approaching'
    : phase === 'stopped'
      ? 'All vehicles stopped'
      : phase === 'right-of-way'
        ? `${decision.firstVehicle} has right-of-way`
        : phase === 'proceeding'
          ? `${decision.firstVehicle} proceeds`
          : 'Turn complete';

  useEffect(() => {
    if (!running) return undefined;
    const startedAt = performance.now() - elapsed;
    let frameId;
    const advance = (now) => {
      const nextElapsed = Math.min(now - startedAt, DEMO_DURATION);
      setElapsed(nextElapsed);
      if (nextElapsed >= DEMO_DURATION) {
        setRunning(false);
        return;
      }
      frameId = window.requestAnimationFrame(advance);
    };
    frameId = window.requestAnimationFrame(advance);
    return () => window.cancelAnimationFrame(frameId);
  }, [running, scenarioId]);

  useEffect(() => {
    setElapsed(0);
    setRunning(false);
  }, [scenarioId]);

  useEffect(() => {
    if (lastAutoPlayKey.current === autoPlayKey) return;
    lastAutoPlayKey.current = autoPlayKey;
    setElapsed(0);
    setRunning(true);
  }, [autoPlayKey]);

  const togglePlayback = () => {
    if (running) {
      setRunning(false);
      return;
    }
    if (elapsed >= DEMO_DURATION) setElapsed(0);
    setRunning(true);
  };

  return (
    <section className="panel scene-panel" id="scene" aria-labelledby="scene-heading">
      <div className="panel-heading scene-heading">
        <div>
          <h2 id="scene-heading">Intersection walkthrough</h2>
          <p>Town center <span className="separator">·</span> Four-way stop</p>
        </div>
        <span className="scene-live"><span />Interactive scene</span>
      </div>
      <div className="scene-canvas" aria-label="3D four-way intersection with four labeled vehicles">
        <Canvas camera={{ position: [8.6, 10.5, 9.2], fov: 34 }} shadows>
          <Scene phase={phase} firstVehicle={decision.firstVehicle} elapsed={elapsed} />
        </Canvas>
        <div className="compass north">N</div>
        <div className="scene-caption">TOWN CENTER <span>·</span> FOUR-WAY STOP</div>
      </div>
      <div className="scene-controls">
        <div>
          <div className="status-line"><span className="status-dot" />{phaseName}</div>
          <p>{decision.explanation}</p>
        </div>
        <button className="action-button" type="button" onClick={togglePlayback}>{running ? 'Pause demo' : elapsed >= DEMO_DURATION ? 'Replay demo' : '▶  Play demo'}</button>
      </div>
      <div className="vehicle-key" aria-label="Intersection approaches">
        {approaches.map((vehicle) => (
          <span key={vehicle.id}><i style={{ backgroundColor: vehicle.color }} />{vehicle.name}<b>{vehicle.id}</b></span>
        ))}
      </div>
    </section>
  );
}
