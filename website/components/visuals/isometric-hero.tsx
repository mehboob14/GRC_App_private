/**
 * The hero illustration: isometric "building blocks of proof". Dashed wireframe
 * cubes at the back stand for requirements not yet worked; solid sky cubes at
 * the front are controls with evidence behind them. Original artwork, drawn in
 * code; three signal routes reach every cube during the longer build sequence.
 * People who prefer reduced motion see the complete static illustration.
 */

const COS30 = 0.8660254;
const S = 62; // cube edge in px
const OX = 290;
const OY = 82;

type Point = [number, number];

function project(x: number, y: number, z: number): Point {
  return [OX + (x - y) * COS30 * S, OY + (x + y) * 0.5 * S - z * S];
}

const fmt = (points: Point[]) => points.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
const topCenter = (i: number, j: number): Point => project(i + 0.5, j + 0.5, 1.03);
const routePath = (points: Point[]) => points.map(([x, y], index) => `${index ? "L" : "M"} ${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");

const nodes = {
  source: topCenter(0, 0),
  upperMiddle: topCenter(1.5, 0),
  upperRight: topCenter(3, 0),
  rightLayers: topCenter(4.3, 0.4),
  centreLeft: topCenter(0.9, 1.7),
  centreRight: topCenter(2.3, 1.7),
  farLeft: topCenter(1, 3.2),
  frontLeft: topCenter(2.45, 3.2),
  frontMiddle: topCenter(3.9, 3.2),
  frontRight: topCenter(5.35, 3.2),
};

const signalRoutes = [
  { path: routePath([nodes.source, nodes.upperMiddle, nodes.upperRight, nodes.rightLayers]), begin: "0s", travel: 0.36, fade: 0.38, size: 4.8 },
  { path: routePath([nodes.source, nodes.centreLeft, nodes.centreRight, nodes.frontLeft, nodes.frontMiddle, nodes.frontRight]), begin: "1s", travel: 0.64, fade: 0.66, size: 5.2 },
  { path: routePath([nodes.centreLeft, nodes.farLeft]), begin: "2.2s", travel: 0.18, fade: 0.2, size: 3.8 },
];

function faces(i: number, j: number, k = 0, h = 1) {
  const P = (a: number, b: number, c: number) => project(i + a, j + b, k + c * h);
  return {
    top: fmt([P(0, 0, 1), P(1, 0, 1), P(1, 1, 1), P(0, 1, 1)]),
    right: fmt([P(1, 0, 0), P(1, 1, 0), P(1, 1, 1), P(1, 0, 1)]),
    left: fmt([P(0, 1, 0), P(1, 1, 0), P(1, 1, 1), P(0, 1, 1)]),
    hidden: [
      [P(0, 0, 0), P(1, 0, 0)],
      [P(0, 0, 0), P(0, 1, 0)],
      [P(0, 0, 0), P(0, 0, 1)],
    ] as Point[][],
    P,
  };
}

function rhombus(i: number, j: number, z: number, inset = 0.16): string {
  const a = inset;
  const b = 1 - inset;
  return fmt([project(i + a, j + a, z), project(i + b, j + a, z), project(i + b, j + b, z), project(i + a, j + b, z)]);
}

function WireCube({ i, j, motif, delay = 0, hit }: { i: number; j: number; motif: "layers" | "dots" | "ring"; delay?: number; hit: number }) {
  const f = faces(i, j);
  const [cx, cy] = topCenter(i, j);
  return (
    <g className="iso-wire" style={{ ["--d" as string]: `${delay}ms`, ["--hit" as string]: `${hit}s` }}>
      {f.hidden.map((edge, index) => (
        <line key={index} x1={edge[0][0]} y1={edge[0][1]} x2={edge[1][0]} y2={edge[1][1]} className="iso-hidden-edge" />
      ))}
      <polygon points={f.left} className="iso-wire-face" />
      <polygon points={f.right} className="iso-wire-face" />
      <polygon points={f.top} className="iso-wire-face" />
      {motif === "layers" && [0.22, 0.38, 0.54, 0.7].map((z, index) => <polygon key={z} points={rhombus(i, j, z)} className="iso-wire-layer" style={{ ["--n" as string]: index }} />)}
      {motif === "dots" &&
        [0.25, 0.5, 0.75].flatMap((u) =>
          [0.25, 0.5, 0.75].flatMap((v) => {
            const right = f.P(1, u, v);
            const left = f.P(u, 1, v);
            const top = f.P(u, v, 1);
            return [right, left, top].map((p, index) => <circle key={`${u}-${v}-${index}`} cx={p[0]} cy={p[1]} r={2.1} className="iso-dot" />);
          }),
        )}
      {motif === "ring" && (() => {
        const [cx, cy] = f.P(0.5, 0.5, 0.5);
        return <circle cx={cx} cy={cy} r={S * 0.42} className="iso-ring" />;
      })()}
      <circle cx={cx} cy={cy} r="12" className="iso-node-pulse" />
    </g>
  );
}

function SolidCube({ i, j, motif, delay = 0, height = 1, hit }: { i: number; j: number; motif?: "layers" | "check" | "orb" | "dots"; delay?: number; height?: number; hit: number }) {
  const f = faces(i, j, 0, height);
  const [cx, cy] = topCenter(i, j);
  return (
    <g className="iso-solid" style={{ ["--d" as string]: `${delay}ms`, ["--hit" as string]: `${hit}s` }}>
      <g className="iso-build-outline" aria-hidden="true">
        <polygon points={f.left} />
        <polygon points={f.right} />
        <polygon points={f.top} />
      </g>
      <g className="iso-solid-body">
        <polygon points={f.left} className="iso-face-left" />
        <polygon points={f.right} className="iso-face-right" />
        <polygon points={f.top} className="iso-face-top" />
        {motif === "layers" &&
          [0.2, 0.36, 0.52, 0.68, 0.84].map((z, index) => <polygon key={z} points={rhombus(i, j, z * height, 0.12)} className="iso-layer" style={{ ["--n" as string]: index }} />)}
        {motif === "dots" &&
          [0.25, 0.5, 0.75].flatMap((u) =>
            [0.25, 0.5, 0.75].flatMap((v) => {
              const right = f.P(1, u, v);
              const left = f.P(u, 1, v);
              return [right, left].map((p, index) => <circle key={`${u}-${v}-${index}`} cx={p[0]} cy={p[1]} r={2.4} className="iso-dot-active" style={{ ["--n" as string]: Math.round((u + v) * 4) + index }} />);
            }),
          )}
        {motif === "orb" && (() => {
          const [cx, cy] = f.P(0.5, 0.5, 0.55);
          return (
            <>
              <circle cx={cx} cy={cy} r={S * 0.55} fill="url(#iso-orb)" className="iso-orb" />
              <circle cx={cx} cy={cy} r={S * 0.16} className="iso-orb-core" />
            </>
          );
        })()}
        {motif === "check" && (() => {
          const [tx, ty] = f.P(0.5, 0.5, 1);
          return <polyline points={fmt([[tx - 13, ty - 1], [tx - 4, ty + 7], [tx + 14, ty - 9]])} className="iso-check" />;
        })()}
      </g>
      <circle cx={cx} cy={cy} r="12" className="iso-node-pulse" />
    </g>
  );
}

function Plane({ i0, j0, i1, j1, delay = 0 }: { i0: number; j0: number; i1: number; j1: number; delay?: number }) {
  const corners = [project(i0, j0, 0), project(i1, j0, 0), project(i1, j1, 0), project(i0, j1, 0)];
  return (
    <g className="iso-plane" style={{ ["--d" as string]: `${delay}ms` }}>
      <polygon points={fmt(corners)} className="iso-plane-fill" />
      <polygon points={fmt(corners)} className="iso-plane-edge" />
      {corners.map(([x, y], index) => (
        <rect key={index} x={x - 4} y={y - 4} width={8} height={8} transform={`rotate(45 ${x} ${y})`} className="iso-plane-node" />
      ))}
    </g>
  );
}

export function IsometricHero({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 680 430" className={`iso-hero ${className ?? ""}`} role="img" aria-label="Illustration: signals travel from requirements across connected controls and evidence boxes.">
      <defs>
        <radialGradient id="iso-orb">
          <stop offset="0" stopColor="#38BDF8" stopOpacity="0.75" />
          <stop offset="0.55" stopColor="#7DD3FC" stopOpacity="0.28" />
          <stop offset="1" stopColor="#E0F2FE" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* Ground planes. */}
      <Plane i0={4.0} j0={-0.6} i1={6.2} j1={1.6} delay={150} />
      <Plane i0={-0.6} j0={2.0} i1={1.8} j1={4.4} delay={350} />

      <g className="iso-signal-tracks" aria-hidden="true">
        {signalRoutes.map(({ path }) => <path key={path} d={path} className="iso-signal-track" />)}
      </g>

      {/* Drawn back to front (by i + j). Back row: requirements, still outlines. */}
      <WireCube i={0} j={0} motif="layers" delay={0} hit={0.6} />
      <WireCube i={1.5} j={0} motif="dots" delay={120} hit={1.4} />
      <SolidCube i={0.9} j={1.7} motif="orb" delay={520} hit={2} />
      <WireCube i={3.0} j={0} motif="ring" delay={240} hit={2.8} />
      <WireCube i={2.3} j={1.7} motif="dots" delay={360} hit={3.4} />
      {/* Front row: controls with evidence behind them. */}
      <SolidCube i={1.0} j={3.2} delay={680} hit={4.2} />
      <SolidCube i={4.3} j={0.4} motif="layers" delay={440} hit={4} />
      <SolidCube i={2.45} j={3.2} delay={800} hit={5.1} />
      <SolidCube i={3.9} j={3.2} motif="check" delay={920} hit={6.6} />
      <SolidCube i={5.35} j={3.2} delay={1040} hit={8} />

      <g className="iso-signal" aria-hidden="true">
        {signalRoutes.map(({ path, begin, travel, fade }) => (
          <path key={path} d={path} pathLength="100" className="iso-signal-flow" opacity="0">
            <animate attributeName="stroke-dashoffset" values="0;-100;-100" keyTimes={`0;${travel};1`} dur="11s" begin={begin} repeatCount="indefinite" />
            <animate attributeName="opacity" values="0;0.8;0.8;0;0" keyTimes={`0;0.02;${travel};${fade};1`} dur="11s" begin={begin} repeatCount="indefinite" />
          </path>
        ))}
        {signalRoutes.map(({ path, begin, travel, fade, size }) => (
          <circle key={path} r={size} className="iso-signal-dot">
            <animateMotion dur="11s" begin={begin} repeatCount="indefinite" path={path} keyPoints="0;1;1" keyTimes={`0;${travel};1`} calcMode="linear" />
            <animate attributeName="opacity" values="0;1;1;0;0" keyTimes={`0;0.02;${travel};${fade};1`} dur="11s" begin={begin} repeatCount="indefinite" />
          </circle>
        ))}
      </g>
    </svg>
  );
}
