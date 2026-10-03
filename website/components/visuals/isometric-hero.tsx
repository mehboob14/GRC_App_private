/**
 * The hero illustration: isometric "building blocks of proof". Dashed wireframe
 * cubes at the back stand for requirements not yet worked; solid sky cubes at
 * the front are controls with evidence behind them. Original artwork, drawn in
 * code; CSS (motion.css) animates it and reduced motion shows the final state.
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

function WireCube({ i, j, motif, delay = 0 }: { i: number; j: number; motif: "layers" | "dots" | "ring"; delay?: number }) {
  const f = faces(i, j);
  return (
    <g className="iso-wire" style={{ ["--d" as string]: `${delay}ms` }}>
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
    </g>
  );
}

function SolidCube({ i, j, motif, delay = 0, height = 1 }: { i: number; j: number; motif?: "layers" | "check" | "orb" | "dots"; delay?: number; height?: number }) {
  const f = faces(i, j, 0, height);
  return (
    <g className="iso-solid" style={{ ["--d" as string]: `${delay}ms` }}>
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
    <svg viewBox="0 0 680 430" className={`iso-hero ${className ?? ""}`} role="img" aria-label="Illustration: dashed outline cubes at the back become solid blue cubes at the front, as requirements turn into controls proven by evidence.">
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

      {/* Drawn back to front (by i + j). Back row: requirements, still outlines. */}
      <WireCube i={0} j={0} motif="layers" delay={0} />
      <WireCube i={1.5} j={0} motif="dots" delay={120} />
      <SolidCube i={0.9} j={1.7} motif="orb" delay={520} />
      <WireCube i={3.0} j={0} motif="ring" delay={240} />
      <WireCube i={2.3} j={1.7} motif="dots" delay={360} />
      {/* Front row: controls with evidence behind them. */}
      <SolidCube i={1.0} j={3.2} delay={680} />
      <SolidCube i={4.3} j={0.4} motif="layers" delay={440} />
      <SolidCube i={2.45} j={3.2} delay={800} />
      <SolidCube i={3.9} j={3.2} motif="check" delay={920} />
      <SolidCube i={5.35} j={3.2} delay={1040} />
    </svg>
  );
}
