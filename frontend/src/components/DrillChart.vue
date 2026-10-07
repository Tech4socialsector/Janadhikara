<template>
  <ECharts :options="options" :events="{ click: (params) => emit('select', params) }" class="h-full w-full cursor-pointer" />
</template>

<script setup>
import { computed } from 'vue'
import { ECharts } from 'frappe-ui'
import { chartTheme, slotFor, FONT, tooltipBox } from '@/data/chartTheme'

// The dashboard's charts, drawn through frappe-ui's ECharts wrapper so a click can be reported
// (`dataIndex`, `seriesName`). Three forms:
//   bar    rows [{ label, count }] - one series, one hue; value at the tip of every bar.
//          `horizontal` for long labels, `suffix` ('%') after the value, `max` for a fixed scale.
//   donut  rows [{ label, count }] - colours follow the label; the total sits in the middle.
//   line   `months` ['2026-10'], `series` [{ name, values }] - 2px lines on a faint wash.
const props = defineProps({
  kind: { type: String, default: 'bar' },
  rows: { type: Array, default: () => [] },
  horizontal: { type: Boolean, default: false },
  suffix: { type: String, default: '' },
  max: { type: Number, default: undefined },
  seriesName: { type: String, default: 'Individuals' },
  months: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] },
})
const emit = defineEmits(['select'])

const monthLabel = (m) => {
  const [year, month] = m.split('-')
  return new Date(Number(year), Number(month) - 1, 1).toLocaleString('en', { month: 'short', year: 'numeric' })
}
const baseText = (t, extra = {}) => ({ fontFamily: FONT, fontSize: 12, color: t.secondary, ...extra })
const tooltipStyle = (t) => ({
  backgroundColor: t.tooltip, borderColor: t.tooltipBorder, borderWidth: 1, padding: [8, 12],
  extraCssText: 'border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,.12);', textStyle: baseText(t),
})

function barOptions(t) {
  const color = t.colors[0]
  const horizontal = props.horizontal
  const names = props.rows.map((r) => r.label)
  const category = {
    type: 'category', data: names, inverse: horizontal,
    axisLine: { lineStyle: { color: t.axis } }, axisTick: { show: false },
    axisLabel: horizontal
      ? { ...baseText(t), width: 150, overflow: 'truncate' }
      : { ...baseText(t), interval: 0, width: 90, overflow: 'break' },
  }
  // Every bar carries its value, so the value axis would only repeat it: hidden.
  const value = { type: 'value', show: false, min: 0, max: props.max ?? ((v) => Math.max(1, Math.ceil(v.max * 1.15))) }
  return {
    animationDuration: 400,
    grid: horizontal ? { left: 8, right: 44, top: 8, bottom: 8, containLabel: true } : { left: 8, right: 8, top: 24, bottom: 8, containLabel: true },
    xAxis: horizontal ? value : category,
    yAxis: horizontal ? category : value,
    tooltip: {
      ...tooltipStyle(t), trigger: 'item',
      formatter: (p) => tooltipBox(t, p.name, [{ color, value: `${p.value}${props.suffix}`, name: props.seriesName }]),
    },
    series: [
      {
        name: props.seriesName, type: 'bar', barMaxWidth: 20,
        data: props.rows.map((r) => ({ value: props.suffix ? r.percent ?? r.count : r.count })),
        itemStyle: { color, borderRadius: horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0] },
        emphasis: { itemStyle: { color: t.hover } },
        label: { show: true, position: horizontal ? 'right' : 'top', formatter: (p) => `${p.value}${props.suffix}`, ...baseText(t, { color: t.primary, fontWeight: 600 }) },
        showBackground: false,
      },
    ],
  }
}

function donutOptions(t) {
  const total = props.rows.reduce((sum, r) => sum + r.count, 0)
  const colorOf = (label) => t.colors[slotFor(label)]
  const countOf = Object.fromEntries(props.rows.map((r) => [r.label, r.count]))
  return {
    animationDuration: 400,
    tooltip: {
      ...tooltipStyle(t), trigger: 'item',
      formatter: (p) => tooltipBox(t, p.name, [{ color: p.color, value: `${p.value} (${p.percent}%)`, name: 'Records' }]),
    },
    legend: {
      bottom: 0, type: 'scroll', icon: 'circle', itemWidth: 8, itemHeight: 8, itemGap: 14, textStyle: baseText(t),
      formatter: (name) => `${name}  ${countOf[name] ?? ''}`,
      pageTextStyle: baseText(t), pageIconColor: t.secondary, pageIconInactiveColor: t.axis,
    },
    title: {
      text: String(total), subtext: 'Total', left: 'center', top: '34%', itemGap: 2,
      textStyle: { fontFamily: FONT, fontSize: 28, fontWeight: 600, color: t.primary },
      subtextStyle: { fontFamily: FONT, fontSize: 12, color: t.muted },
    },
    series: [
      {
        type: 'pie', radius: ['56%', '76%'], center: ['50%', '45%'], minAngle: 4,
        // the 2px surface-coloured gap separates the slices - no outline on the marks
        itemStyle: { borderColor: t.surface, borderWidth: 2, borderRadius: 4 },
        label: { show: false }, labelLine: { show: false },
        emphasis: { scaleSize: 4, label: { show: false } },
        data: props.rows.map((r) => ({ name: r.label, value: r.count, itemStyle: { color: colorOf(r.label) } })),
      },
    ],
  }
}

// One or two months are too few for a line: draw side-by-side columns, one per series.
function groupedBarOptions(t) {
  return {
    animationDuration: 400,
    grid: { left: 8, right: 8, top: 36, bottom: 8, containLabel: true },
    legend: { top: 0, right: 0, icon: 'roundRect', itemWidth: 10, itemHeight: 10, itemGap: 18, textStyle: baseText(t) },
    tooltip: {
      ...tooltipStyle(t), trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: t.grid, opacity: 0.5 } },
      formatter: (items) => tooltipBox(t, items[0].axisValueLabel, items.map((i) => ({ color: i.color, value: i.value, name: i.seriesName }))),
    },
    xAxis: { type: 'category', data: props.months.map(monthLabel), axisLine: { lineStyle: { color: t.axis } }, axisTick: { show: false }, axisLabel: baseText(t) },
    yAxis: { type: 'value', show: false, min: 0, max: (v) => Math.max(1, Math.ceil(v.max * 1.2)) },
    series: props.series.map((s, i) => ({
      name: s.name, type: 'bar', barMaxWidth: 22, barGap: '12%',
      data: s.values,
      itemStyle: { color: t.colors[i], borderRadius: [4, 4, 0, 0] },
      label: { show: true, position: 'top', ...baseText(t, { color: t.primary, fontWeight: 600 }) },
    })),
  }
}

function lineOptions(t) {
  if (props.months.length < 3) return groupedBarOptions(t)
  const labels = props.months.map(monthLabel)
  const single = props.months.length < 2
  const last = props.months.length - 1
  return {
    animationDuration: 400,
    grid: { left: 8, right: 36, top: 36, bottom: 8, containLabel: true },
    legend: { top: 0, right: 0, icon: 'roundRect', itemWidth: 14, itemHeight: 3, itemGap: 18, textStyle: baseText(t) },
    tooltip: {
      ...tooltipStyle(t), trigger: 'axis',
      axisPointer: { type: 'line', lineStyle: { color: t.axis, width: 1 } },
      formatter: (items) => tooltipBox(t, items[0].axisValueLabel, items.map((i) => ({ color: i.color, value: i.value, name: i.seriesName }))),
    },
    xAxis: {
      type: 'category', data: labels, boundaryGap: single,
      axisLine: { lineStyle: { color: t.axis } }, axisTick: { show: false }, axisLabel: baseText(t),
    },
    yAxis: {
      type: 'value', minInterval: 1, min: 0,
      splitLine: { lineStyle: { color: t.grid, type: 'solid', width: 1 } },
      axisLine: { show: false }, axisTick: { show: false }, axisLabel: baseText(t, { color: t.muted }),
    },
    series: props.series.map((s, i) => {
      const color = t.colors[i]
      return {
        name: s.name, type: 'line', smooth: false, symbol: 'circle', symbolSize: 8, showSymbol: true,
        lineStyle: { width: 2, color, cap: 'round', join: 'round' },
        // the 2px surface ring keeps a dot legible where it crosses another line
        itemStyle: { color, borderColor: t.surface, borderWidth: 2 },
        areaStyle: { color, opacity: 0.1 },
        emphasis: { focus: 'series', scale: 1.4 },
        // label only the latest point - the axis and tooltip carry the rest
        data: s.values.map((v, idx) => ({ value: v, label: { show: idx === last, position: 'top', ...baseText(t, { color: t.primary, fontWeight: 600 }) } })),
      }
    }),
  }
}

const options = computed(() => {
  const t = chartTheme.value
  if (props.kind === 'donut') return donutOptions(t)
  if (props.kind === 'line') return lineOptions(t)
  return barOptions(t)
})
</script>
