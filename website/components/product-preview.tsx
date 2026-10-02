"use client";

import { useState } from "react";
import { ProductScene, type Scene } from "./product-scene";

const views: { id: Scene; label: string }[] = [
  { id: "controls", label: "Controls" },
  { id: "evidence", label: "Evidence" },
  { id: "risk", label: "Risks" },
];

export function ProductPreview() {
  const [view, setView] = useState<Scene>("controls");

  return (
    <div className="hero-product">
      <div className="hero-product-topline">
        <span>Explore a sample workspace</span>
        <div className="hero-product-tabs" role="group" aria-label="Sample workspace views">
          {views.map(({ id, label }) => <button key={id} type="button" aria-pressed={view === id} onClick={() => setView(id)}>{label}</button>)}
        </div>
      </div>
      <div key={view} className="scene-enter"><ProductScene scene={view} /></div>
    </div>
  );
}
