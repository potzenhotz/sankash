import { BarChart, SankeyChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useRef, useState } from "react";

echarts.use([SankeyChart, BarChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

export type ChartOption = echarts.EChartsCoreOption;
export type ChartColors = Record<"text" | "muted" | "grid" | "surface" | "income" | "account" | "expense", string>;

/** Chart colors come from the CSS tokens so light/dark stay in one place (styles.css). */
function readColors(): ChartColors {
  const css = getComputedStyle(document.documentElement);
  const v = (name: string) => css.getPropertyValue(name).trim();
  return {
    text: v("--text"), muted: v("--muted"), grid: v("--border"), surface: v("--surface"),
    income: v("--series-income"), account: v("--series-account"), expense: v("--series-expense"),
  };
}

export function useChartColors(): ChartColors {
  const [colors, setColors] = useState(readColors);
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => setColors(readColors());
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return colors;
}

type Props = {
  option: ChartOption;
  height: number;
  ariaLabel: string;
  onClick?: (params: echarts.ECElementEvent) => void;
};

export function Chart({ option, height, ariaLabel, onClick }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  const clickRef = useRef(onClick);
  clickRef.current = onClick;

  useEffect(() => {
    const instance = echarts.init(ref.current!);
    chart.current = instance;
    instance.on("click", (p) => clickRef.current?.(p as echarts.ECElementEvent));
    const resize = new ResizeObserver(() => instance.resize());
    resize.observe(ref.current!);
    return () => {
      resize.disconnect();
      instance.dispose();
    };
  }, []);

  useEffect(() => {
    chart.current?.setOption(option, { notMerge: true });
  }, [option]);

  return <div ref={ref} role="img" aria-label={ariaLabel} style={{ height, width: "100%" }} />;
}
