export default function VehicleModel({
  color,
  width = 0.76,
  length = 1.25,
  highlight = false,
  wheels = false,
}) {
  const bodyHeight = Math.min(0.42, width * 0.38);
  const wheelX = width * 0.42;
  const wheelZ = length * 0.31;

  return (
    <group>
      <mesh position={[0, bodyHeight * 0.72, 0]} castShadow>
        <boxGeometry args={[width, bodyHeight, length]} />
        <meshStandardMaterial
          color={color}
          emissive={highlight ? '#f5bc58' : '#000000'}
          emissiveIntensity={highlight ? 0.65 : 0}
          roughness={0.45}
        />
      </mesh>
      <mesh position={[0, bodyHeight * 1.38, -length * 0.02]}>
        <boxGeometry args={[width * 0.75, bodyHeight * 0.6, length * 0.43]} />
        <meshStandardMaterial color="#dcebf1" metalness={0.12} roughness={0.24} />
      </mesh>
      {[-1, 1].map((side) => (
        <group key={side}>
          <mesh position={[side * width * 0.31, bodyHeight * 0.69, length * 0.47]}>
            <boxGeometry args={[width * 0.15, bodyHeight * 0.16, 0.055]} />
            <meshStandardMaterial color="#fff0b3" emissive="#d39a3c" emissiveIntensity={0.12} />
          </mesh>
          <mesh position={[side * width * 0.31, bodyHeight * 0.69, -length * 0.47]}>
            <boxGeometry args={[width * 0.15, bodyHeight * 0.16, 0.055]} />
            <meshStandardMaterial color="#bd604d" />
          </mesh>
        </group>
      ))}
      {wheels && [-1, 1].flatMap((side) => [-1, 1].map((axle) => (
        <mesh
          key={`${side}-${axle}`}
          position={[side * wheelX, 0.16, axle * wheelZ]}
          rotation={[0, 0, Math.PI / 2]}
          castShadow
        >
          <cylinderGeometry args={[0.17, 0.17, 0.12, 12]} />
          <meshStandardMaterial color="#27343a" roughness={0.8} />
        </mesh>
      )))}
      {highlight && (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.035, 0]}>
          <ringGeometry args={[width * 0.78, width * 0.96, 32]} />
          <meshBasicMaterial color="#f5bc58" transparent opacity={0.9} />
        </mesh>
      )}
    </group>
  );
}
