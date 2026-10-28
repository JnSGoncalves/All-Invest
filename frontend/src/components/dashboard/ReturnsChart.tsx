import { useEffect, useId, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import type { ReturnPoint } from "../../services/api";
import { parseDay } from "./dates";

const HEIGHT = 240;
const MARGIN = { top: 14, right: 16, bottom: 30, left: 76 };
const currency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const signedCurrency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", signDisplay: "exceptZero" });
const compactCurrency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", notation: "compact", maximumFractionDigits: 1, signDisplay: "negative" });
const shortDate = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" });
const longDate = new Intl.DateTimeFormat("pt-BR", { weekday: "short", day: "2-digit", month: "short", year: "numeric" });

function niceTicks(min: number, max: number, count = 4): number[] {
  const span = max - min || Math.abs(max) || 1;
  const raw = span / count;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((factor) => factor * magnitude).find((candidate) => candidate >= raw) ?? raw;
  const ticks: number[] = [];
  for (let tick = Math.floor(min / step) * step; tick <= max + step / 2; tick += step) ticks.push(Number(tick.toFixed(10)));
  return ticks;
}

export default function ReturnsChart({ points }: { points: ReturnPoint[] }) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(640);
  const [active, setActive] = useState<number | null>(null);
  const clipId = useId();

  useEffect(() => {
    const element = wrapRef.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(280, Math.round(entry.contentRect.width))));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const gains = points.map((point) => point.gain);
  const ticks = niceTicks(Math.min(0, ...gains), Math.max(0, ...gains));
  const yMin = ticks[0];
  const yMax = ticks[ticks.length - 1];
  const plotWidth = width - MARGIN.left - MARGIN.right;
  const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom;
  const x = (index: number) => MARGIN.left + (points.length > 1 ? (index / (points.length - 1)) * plotWidth : plotWidth / 2);
  const y = (value: number) => MARGIN.top + ((yMax - value) / (yMax - yMin || 1)) * plotHeight;
  const zeroY = y(0);

  const line = points.map((point, index) => `${index ? "L" : "M"}${x(index).toFixed(1)},${y(point.gain).toFixed(1)}`).join("");
  const area = `${line}L${x(points.length - 1).toFixed(1)},${zeroY.toFixed(1)}L${x(0).toFixed(1)},${zeroY.toFixed(1)}Z`;

  const labelCount = Math.min(points.length, width < 520 ? 3 : 5);
  const labelIndexes = [...new Set(Array.from({ length: labelCount }, (_, i) => Math.round((i * (points.length - 1)) / Math.max(labelCount - 1, 1))))];

  const last = points[points.length - 1];
  const summary = `Ganho acumulado de ${signedCurrency.format(last.gain)} entre ${shortDate.format(parseDay(points[0].date))} e ${shortDate.format(parseDay(last.date))}. Use as setas para percorrer os dias.`;

  function nearest(event: PointerEvent<SVGRectElement>) {
    const box = event.currentTarget.getBoundingClientRect();
    const ratio = (event.clientX - box.left) / box.width;
    setActive(Math.min(points.length - 1, Math.max(0, Math.round(ratio * (points.length - 1)))));
  }

  function handleKey(event: KeyboardEvent<SVGSVGElement>) {
    const moves: Record<string, number> = { ArrowLeft: -1, ArrowRight: 1, Home: -Infinity, End: Infinity };
    if (!(event.key in moves)) return;
    event.preventDefault();
    setActive((current) => Math.min(points.length - 1, Math.max(0, (current ?? points.length - 1) + moves[event.key])));
  }

  const hovered = active !== null ? points[active] : null;
  const tooltipLeft = active !== null ? x(active) : 0;
  const flip = tooltipLeft > width - 200;

  return (
    <div className="returns-chart" ref={wrapRef}>
      <svg
        width={width}
        height={HEIGHT}
        role="img"
        aria-label={summary}
        tabIndex={0}
        onKeyDown={handleKey}
        onFocus={() => setActive((current) => current ?? points.length - 1)}
        onBlur={() => setActive(null)}
      >
        <defs>
          <clipPath id={`${clipId}-up`}><rect x={0} y={0} width={width} height={Math.max(zeroY, 0)} /></clipPath>
          <clipPath id={`${clipId}-down`}><rect x={0} y={zeroY} width={width} height={Math.max(HEIGHT - zeroY, 0)} /></clipPath>
        </defs>

        {ticks.map((tick) => (
          <g key={tick}>
            <line className={tick === 0 ? "chart-zero" : "chart-grid"} x1={MARGIN.left} x2={width - MARGIN.right} y1={y(tick)} y2={y(tick)} />
            <text className="chart-axis" x={MARGIN.left - 10} y={y(tick)} dy="0.32em" textAnchor="end">{compactCurrency.format(tick)}</text>
          </g>
        ))}
        {labelIndexes.map((index) => (
          <text
            key={index}
            className="chart-axis"
            x={x(index)}
            y={HEIGHT - 8}
            textAnchor={index === 0 ? "start" : index === points.length - 1 ? "end" : "middle"}
          >
            {shortDate.format(parseDay(points[index].date))}
          </text>
        ))}

        <path className="chart-area up" d={area} clipPath={`url(#${clipId}-up)`} />
        <path className="chart-area down" d={area} clipPath={`url(#${clipId}-down)`} />
        <path className="chart-line up" d={line} clipPath={`url(#${clipId}-up)`} />
        <path className="chart-line down" d={line} clipPath={`url(#${clipId}-down)`} />

        {hovered && active !== null && (
          <g aria-hidden="true">
            <line className="chart-crosshair" x1={x(active)} x2={x(active)} y1={MARGIN.top} y2={HEIGHT - MARGIN.bottom} />
            <circle className={`chart-dot ${hovered.gain < 0 ? "down" : "up"}`} cx={x(active)} cy={y(hovered.gain)} r={5} />
          </g>
        )}

        <rect
          className="chart-hit"
          x={MARGIN.left}
          y={MARGIN.top}
          width={plotWidth}
          height={plotHeight}
          onPointerMove={nearest}
          onPointerDown={nearest}
          onPointerLeave={() => setActive(null)}
        />
      </svg>

      {hovered && (
        <div className={`chart-tooltip ${flip ? "flip" : ""}`} style={{ left: tooltipLeft, top: MARGIN.top }} role="status">
          <span className="chart-tooltip-date">{longDate.format(parseDay(hovered.date))}</span>
          <strong className={hovered.gain < 0 ? "loss" : hovered.gain > 0 ? "gain" : ""}>{signedCurrency.format(hovered.gain)}</strong>
          <span className="chart-tooltip-label">ganho acumulado</span>
          <dl>
            <div><dt>Valor de mercado</dt><dd>{currency.format(hovered.value)}</dd></div>
            <div><dt>Capital aplicado</dt><dd>{currency.format(hovered.invested)}</dd></div>
          </dl>
        </div>
      )}
    </div>
  );
}
