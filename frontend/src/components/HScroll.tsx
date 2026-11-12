'use client';
import { useEffect, useRef, useState, ReactNode } from 'react';

// Wraps wide content. When it overflows at the current width, shows a hint and a right-edge fade that goes away at the end.
export function HScroll({ children, className = '' }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [over, setOver] = useState(false);
  const [atEnd, setAtEnd] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const check = () => {
      setOver(el.scrollWidth > el.clientWidth + 2);
      setAtEnd(el.scrollLeft + el.clientWidth >= el.scrollWidth - 2);
    };
    check();
    const ro = new ResizeObserver(check);
    ro.observe(el);
    if (el.firstElementChild) ro.observe(el.firstElementChild);
    el.addEventListener('scroll', check, { passive: true });
    return () => { ro.disconnect(); el.removeEventListener('scroll', check); };
  }, []);

  return (
    <div className={className}>
      {over && <p className="hscroll-hint">Scroll sideways to see all columns.</p>}
      <div className="hscroll-wrap">
        <div ref={ref} className="hscroll" tabIndex={0} role="region" aria-label="Scrollable table">
          {children}
        </div>
        {over && !atEnd && <span className="hscroll-fade" aria-hidden="true" />}
      </div>
    </div>
  );
}
