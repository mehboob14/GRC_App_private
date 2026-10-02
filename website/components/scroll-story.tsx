"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ProductScene, type Scene } from "./product-scene";

const chapters: { scene: Scene; number: string; title: string; text: string; link: string; linkText: string }[] = [
  {
    scene: "controls",
    number: "01",
    title: "Put ownership on the control.",
    text: "Adopt the SOC 2 control library, map requirements, assign an owner, and track implementation in the control record. Your team can see who is responsible before an evidence request arrives.",
    link: "/docs/03-frameworks-and-controls/",
    linkText: "Read about controls",
  },
  {
    scene: "evidence",
    number: "02",
    title: "Keep proof with the work it supports.",
    text: "Attach a file or record to the relevant controls. The evidence record shows its source, validity, and review state; a person makes the approval decision.",
    link: "/docs/04-evidence/",
    linkText: "Read about evidence",
  },
  {
    scene: "risk",
    number: "03",
    title: "Give risk its own decision trail.",
    text: "Score risks in a register, assign a business owner, plan treatment, and link the controls that reduce exposure. Vendor, asset, and vulnerability work has its own records too.",
    link: "/docs/07-risks/",
    linkText: "Read about risks",
  },
];

export function ScrollStory() {
  const [active, setActive] = useState(0);
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const steps = sectionRef.current?.querySelectorAll<HTMLElement>("[data-story-step]");
    if (!steps || !('IntersectionObserver' in window)) return;
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) setActive(Number((entry.target as HTMLElement).dataset.storyStep));
      }
    }, { rootMargin: "-49% 0px -49% 0px", threshold: 0 });
    steps.forEach((step) => observer.observe(step));
    return () => observer.disconnect();
  }, []);

  return (
    <section id="platform" className="story-section" ref={sectionRef} aria-labelledby="story-title">
      <div className="site-container">
        <div className="story-heading"><span className="story-eyebrow">Inside the workspace</span><h2 id="story-title">Follow the work from control to decision.</h2></div>
        <div className="story-layout">
          <div className="story-copy">
            {chapters.map((chapter, index) => <article className={`story-step ${active === index ? "is-active" : ""}`} data-story-step={index} key={chapter.scene}>
              <span className="story-index">{chapter.number} / 03</span>
              <h3>{chapter.title}</h3>
              <p>{chapter.text}</p>
              <Link className="plain-link" href={chapter.link}>{chapter.linkText}</Link>
              <div className="story-mobile-scene"><ProductScene scene={chapter.scene} compact /></div>
            </article>)}
          </div>
          <div className="story-visual" aria-hidden="true">
            <div className="story-visual-inner"><div key={chapters[active].scene} className="scene-enter"><ProductScene scene={chapters[active].scene} compact /></div></div>
            <div className="story-progress" aria-hidden="true"><span>{chapters[active].number} / 03</span><div>{chapters.map((chapter, index) => <i className={active === index ? "current" : ""} key={chapter.scene} />)}</div></div>
          </div>
        </div>
      </div>
    </section>
  );
}
