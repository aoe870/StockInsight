<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import * as echarts from 'echarts'
import type { KLineData } from '@/api'

const props = defineProps<{
  data: KLineData[]
  stockName?: string
  period?: string
  indicatorData?: Record<string, any>[]
}>()

const emit = defineEmits<{
  (e: 'periodChange', period: string): void
  (e: 'indicatorChange', indicators: string[]): void
}>()

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

// 周期选项
const periods = [
  { label: '分时', value: 'minute' },
  { label: '日K', value: 'daily' },
  { label: '周K', value: 'weekly' },
  { label: '月K', value: 'monthly' },
  { label: '年K', value: 'yearly' },
]

// 指标选项
const indicatorGroups = {
  trend: { label: '趋势', items: ['MA', 'EMA', 'SAR', 'TRIX', 'DMA'] },
  oscillator: { label: '震荡', items: ['KDJ', 'RSI', 'CCI', 'WR', 'ROC', 'BIAS'] },
  volatility: { label: '波动', items: ['BOLL', 'ATR', 'BBI'] },
  volume: { label: '量能', items: ['VOL', 'OBV', 'VWAP', 'VR'] },
  composite: { label: '综合', items: ['MACD', 'DMI', 'PSY'] },
}

const selectedPeriod = ref(props.period || 'daily')
const selectedIndicators = ref<string[]>(['MA', 'VOL', 'MACD'])
const showIndicatorPanel = ref(false)

// 计算均线
const calculateMA = (data: number[], period: number): (number | null)[] => {
  const result: (number | null)[] = []
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push(null)
    } else {
      let sum = 0
      for (let j = 0; j < period; j++) {
        sum += data[i - j]
      }
      result.push(+(sum / period).toFixed(2))
    }
  }
  return result
}

// 切换周期
const changePeriod = (period: string) => {
  selectedPeriod.value = period
  emit('periodChange', period)
}

// 切换指标
const toggleIndicator = (indicator: string) => {
  const idx = selectedIndicators.value.indexOf(indicator)
  if (idx > -1) {
    selectedIndicators.value.splice(idx, 1)
  } else {
    selectedIndicators.value.push(indicator)
  }
  emit('indicatorChange', selectedIndicators.value)
}

// 从指标数据中提取数据
const getIndicatorSeries = (indicatorData: Record<string, any>[] | undefined, key: string): (number | null)[] => {
  if (!indicatorData) return []
  return indicatorData.map(d => d[key] ?? null)
}

const chartOption = computed(() => {
  const dates = props.data.map(d => d.trade_date)
  const ohlc = props.data.map(d => [d.open, d.close, d.low, d.high])
  const volumes = props.data.map(d => d.volume)
  const closes = props.data.map(d => d.close)

  const ma5 = calculateMA(closes, 5)
  const ma10 = calculateMA(closes, 10)
  const ma20 = calculateMA(closes, 20)
  const ma60 = calculateMA(closes, 60)

  // 从后端指标数据提取
  const ind = props.indicatorData || []

  // 基础系列
  const series: any[] = [
    {
      name: 'K线',
      type: 'candlestick',
      data: ohlc,
      xAxisIndex: 0,
      yAxisIndex: 0,
      itemStyle: {
        color: '#ec0000',
        color0: '#00da3c',
        borderColor: '#ec0000',
        borderColor0: '#00da3c',
      },
    },
  ]

  const legendData = ['K线', '成交量']

  // 主图指标说明文字（在标题中显示，不放入图例）
  const mainIndicatorLabels: string[] = []

  // MA 均线 - 不加入图例
  if (selectedIndicators.value.includes('MA')) {
    const ma5Val = ma5[ma5.length - 1]?.toFixed(2) || '--'
    const ma10Val = ma10[ma10.length - 1]?.toFixed(2) || '--'
    const ma20Val = ma20[ma20.length - 1]?.toFixed(2) || '--'
    const ma60Val = ma60[ma60.length - 1]?.toFixed(2) || '--'
    mainIndicatorLabels.push(`MA5:${ma5Val}`, `MA10:${ma10Val}`, `MA20:${ma20Val}`, `MA60:${ma60Val}`)

    series.push(
      { name: 'MA5', type: 'line', data: ma5, smooth: true, lineStyle: { width: 1, color: '#f6a700' }, symbol: 'none' },
      { name: 'MA10', type: 'line', data: ma10, smooth: true, lineStyle: { width: 1, color: '#1890ff' }, symbol: 'none' },
      { name: 'MA20', type: 'line', data: ma20, smooth: true, lineStyle: { width: 1, color: '#ff4d4f' }, symbol: 'none' },
      { name: 'MA60', type: 'line', data: ma60, smooth: true, lineStyle: { width: 1, color: '#52c41a' }, symbol: 'none' },
    )
  }

  // BOLL 布林带 - 不加入图例
  if (selectedIndicators.value.includes('BOLL') && ind.length) {
    const bollUpper = ind[ind.length - 1]?.boll_upper?.toFixed(2) || '--'
    const bollMid = ind[ind.length - 1]?.boll_mid?.toFixed(2) || '--'
    const bollLower = ind[ind.length - 1]?.boll_lower?.toFixed(2) || '--'
    mainIndicatorLabels.push(`BOLL(${bollUpper}, ${bollMid}, ${bollLower})`)

    series.push(
      { name: 'BOLL上轨', type: 'line', data: getIndicatorSeries(ind, 'boll_upper'), lineStyle: { width: 1, type: 'dashed', color: '#eb2f96' }, symbol: 'none' },
      { name: 'BOLL中轨', type: 'line', data: getIndicatorSeries(ind, 'boll_mid'), lineStyle: { width: 1, color: '#722ed1' }, symbol: 'none' },
      { name: 'BOLL下轨', type: 'line', data: getIndicatorSeries(ind, 'boll_lower'), lineStyle: { width: 1, type: 'dashed', color: '#eb2f96' }, symbol: 'none' },
    )
  }

  // 主图标题显示指标值
  const mainTitle = mainIndicatorLabels.length > 0 ? mainIndicatorLabels.join('  ') : ''

  // 成交量
  series.push({
    name: '成交量',
    type: 'bar',
    data: volumes.map((v, i) => ({
      value: v,
      itemStyle: { color: ohlc[i][1] >= ohlc[i][0] ? '#ec0000' : '#00da3c' },
    })),
    xAxisIndex: 1,
    yAxisIndex: 1,
  })

  // 计算需要多少个指标子图
  const subIndicators: string[] = []
  if (selectedIndicators.value.includes('MACD')) subIndicators.push('MACD')
  if (selectedIndicators.value.includes('KDJ')) subIndicators.push('KDJ')
  if (selectedIndicators.value.includes('RSI')) subIndicators.push('RSI')
  if (selectedIndicators.value.includes('CCI')) subIndicators.push('CCI')
  if (selectedIndicators.value.includes('WR')) subIndicators.push('WR')
  if (selectedIndicators.value.includes('DMI')) subIndicators.push('DMI')

  // 预估图例数据项数量（用于提前计算legendHeight）
  let estimatedLegendItems = 1 // K线
  if (selectedIndicators.value.includes('MA')) estimatedLegendItems += 4
  if (selectedIndicators.value.includes('BOLL')) estimatedLegendItems += 3
  if (selectedIndicators.value.includes('MACD')) estimatedLegendItems += 3
  if (selectedIndicators.value.includes('KDJ')) estimatedLegendItems += 3
  if (selectedIndicators.value.includes('RSI')) estimatedLegendItems += 3
  if (selectedIndicators.value.includes('CCI')) estimatedLegendItems += 1
  if (selectedIndicators.value.includes('WR')) estimatedLegendItems += 2
  if (selectedIndicators.value.includes('DMI')) estimatedLegendItems += 3
  // 减少图例占用的空间
  const legendHeight = estimatedLegendItems > 8 ? 25 : estimatedLegendItems > 4 ? 20 : 18

  // 动态计算 grid 布局 - 根据指标数量调整
  const subCount = subIndicators.length
  // 主图高度随指标数量减少
  const mainHeight = subCount === 0 ? 58 : subCount === 1 ? 48 : subCount === 2 ? 40 : subCount === 3 ? 34 : 28
  const volHeight = 10
  // 副图指标高度：确保每个至少有足够空间
  const availableHeight = 88 - mainHeight - volHeight - 4 // 留出底部滑块空间
  const subHeight = subCount > 0 ? Math.max(12, Math.floor(availableHeight / subCount)) : 0

  const grids: any[] = [
    {
      left: '10%',
      right: '3%',
      top: `${legendHeight + 6}%`,
      height: `${mainHeight}%`,
      backgroundColor: 'rgba(255, 255, 255, 0)',
      borderWidth: 0,
      show: true
    },
    {
      left: '10%',
      right: '3%',
      top: `${legendHeight + mainHeight + 8}%`,
      height: `${volHeight}%`,
      backgroundColor: 'rgba(0, 0, 0, 0.01)',
      borderWidth: 0,
      show: true
    },
  ]

  const xAxes: any[] = [
    { type: 'category', data: dates, gridIndex: 0, axisLine: { lineStyle: { color: '#8392A5' } }, splitLine: { show: false }, axisLabel: { show: false } },
    { type: 'category', data: dates, gridIndex: 1, axisLine: { lineStyle: { color: '#8392A5' } }, splitLine: { show: false }, axisLabel: { show: false } },
  ]

  const yAxes: any[] = [
    { type: 'value', gridIndex: 0, scale: true, splitArea: { show: true }, axisLine: { lineStyle: { color: '#8392A5' } }, splitLine: { lineStyle: { color: '#eee' } }, position: 'right' },
    { type: 'value', gridIndex: 1, scale: true, splitNumber: 2, axisLabel: { show: false }, axisLine: { show: false }, splitLine: { show: false } },
  ]

  // 添加指标子图
  let currentTop = legendHeight + mainHeight + volHeight + 10
  // 为不同指标定义不同的背景色和标题颜色（更明显）
  const indicatorStyles: Record<string, string> = {
    'MACD': '#1890ff',
    'KDJ': '#faad14',
    'RSI': '#eb2f96',
    'CCI': '#722ed1',
    'WR': '#52c41a',
    'DMI': '#13c2c2',
  }

  // 生成左侧指标标签和副图标题栏（提前初始化数组）
  const graphicLabels: any[] = [
    { type: 'text', left: 5, top: `${legendHeight + 6}%`, style: { text: 'K线', fill: '#666', fontSize: 10 } },
    { type: 'text', left: 5, top: `${legendHeight + mainHeight + 8}%`, style: { text: 'VOL', fill: '#666', fontSize: 10 } },
  ]

  subIndicators.forEach((indicator, idx) => {
    const gridIdx = grids.length
    const isLast = idx === subIndicators.length - 1
    const indicatorColor = indicatorStyles[indicator] || '#666'

    // 在循环中保存当前指标的top位置，用于后面添加graphic
    const indicatorTop = currentTop

    grids.push({
      left: '10%',
      right: '3%',
      top: `${currentTop}%`,
      height: `${subHeight}%`,
      backgroundColor: 'rgba(0, 0, 0, 0.02)',
      borderWidth: 0,
      borderColor: 'transparent',
      show: true
    })
    xAxes.push({ type: 'category', data: dates, gridIndex: gridIdx, axisLine: { lineStyle: { color: '#8392A5' } }, splitLine: { show: false }, axisLabel: { show: isLast, fontSize: 10 } })

    // 获取指标当前值用于显示
    const getLastValue = (key: string) => {
      if (!ind.length) return '--'
      const val = ind[ind.length - 1]?.[key]
      return val !== null && val !== undefined ? val.toFixed(2) : '--'
    }

    if (indicator === 'MACD') {
      yAxes.push({ type: 'value', gridIndex: gridIdx, scale: true, splitNumber: 2, axisLabel: { fontSize: 9, show: false }, axisLine: { show: false }, splitLine: { lineStyle: { color: '#f0f0f0' } }, position: 'right' })

      if (ind.length) {
        series.push(
          { name: 'DIF', type: 'line', data: getIndicatorSeries(ind, 'macd'), xAxisIndex: gridIdx, yAxisIndex: gridIdx, lineStyle: { width: 1, color: '#1890ff' }, symbol: 'none' },
          { name: 'DEA', type: 'line', data: getIndicatorSeries(ind, 'macd_signal'), xAxisIndex: gridIdx, yAxisIndex: gridIdx, lineStyle: { width: 1, color: '#faad14' }, symbol: 'none' },
          { name: 'MACD柱', type: 'bar', data: getIndicatorSeries(ind, 'macd_hist').map(v => ({ value: v, itemStyle: { color: v !== null && v >= 0 ? '#ec0000' : '#00da3c' } })), xAxisIndex: gridIdx, yAxisIndex: gridIdx },
        )
      }
    }

    if (indicator === 'KDJ') {
      yAxes.push({ type: 'value', gridIndex: gridIdx, scale: true, splitNumber: 2, axisLabel: { fontSize: 9, show: false }, axisLine: { show: false }, splitLine: { lineStyle: { color: '#f0f0f0' } }, position: 'right' })

      if (ind.length) {
        series.push(
          { name: 'K', type: 'line', data: getIndicatorSeries(ind, 'k'), xAxisIndex: gridIdx, yAxisIndex: gridIdx, lineStyle: { width: 1, color: '#1890ff' }, symbol: 'none' },
          { name: 'D', type: 'line', data: getIndicatorSeries(ind, 'd'), xAxisIndex: gridIdx, yAxisIndex: gridIdx, lineStyle: { width: 1, color: '#faad14' }, symbol: 'none' },
          { name: 'J', type: 'line', data: getIndicatorSeries(ind, 'j'), xAxisIndex: gridIdx, yAxisIndex: gridIdx, lineStyle: { width: 1, color: '#eb2f96' }, symbol: 'none' },
        )
      }
    }

    if (indicator === 'RSI') {
      yAxes.push({ type: 'value', gridIndex: gridIdx, scale: true, splitNumber: 2, axisLabel: { fontSize: 9, show: false }, axisLine: { show: false }, splitLine: { lineStyle: { color: '#f0f0f0' } }, position: 'right' })

      if (ind.length) {
        series.push(
          { name: 'RSI6', type: 'line', data: getIndicatorSeries(ind, 'rsi6'), xAxisIndex: gridIdx, yAxisIndex: gridIdx, lineStyle: { width: 1, color: '#1890ff' }, symbol: 'none' },
          { name: 'RSI12', type: 'line', data: getIndicatorSeries(ind, 'rsi12'), xAxisIndex: gridIdx, yAxisIndex: gridIdx, lineStyle: { width: 1, color: '#faad14' }, symbol: 'none' },
          { name: 'RSI24', type: 'line', data: getIndicatorSeries(ind, 'rsi24'), xAxisIndex: gridIdx, yAxisIndex: gridIdx, lineStyle: { width: 1, color: '#eb2f96' }, symbol: 'none' },
        )
      }
    }

    if (indicator === 'CCI') {
      yAxes.push({ type: 'value', gridIndex: gridIdx, scale: true, splitNumber: 2, axisLabel: { fontSize: 9, show: false }, axisLine: { show: false }, splitLine: { lineStyle: { color: '#f0f0f0' } }, position: 'right' })

      if (ind.length) {
        series.push(
          { name: 'CCI', type: 'line', data: getIndicatorSeries(ind, 'cci'), xAxisIndex: gridIdx, yAxisIndex: gridIdx, lineStyle: { width: 1, color: '#722ed1' }, symbol: 'none' },
        )
      }
    }

    if (indicator === 'WR') {
      yAxes.push({ type: 'value', gridIndex: gridIdx, scale: true, splitNumber: 2, axisLabel: { fontSize: 9, show: false }, axisLine: { show: false }, splitLine: { lineStyle: { color: '#f0f0f0' } }, position: 'right' })

      if (ind.length) {
        series.push(
          { name: 'WR14', type: 'line', data: getIndicatorSeries(ind, 'wr'), xAxisIndex: gridIdx, yAxisIndex: gridIdx, lineStyle: { width: 1, color: '#1890ff' }, symbol: 'none' },
          { name: 'WR6', type: 'line', data: getIndicatorSeries(ind, 'wr6'), xAxisIndex: gridIdx, yAxisIndex: gridIdx, lineStyle: { width: 1, color: '#faad14' }, symbol: 'none' },
        )
      }
    }

    if (indicator === 'DMI') {
      yAxes.push({ type: 'value', gridIndex: gridIdx, scale: true, splitNumber: 2, axisLabel: { fontSize: 9, show: false }, axisLine: { show: false }, splitLine: { lineStyle: { color: '#f0f0f0' } }, position: 'right' })

      if (ind.length) {
        series.push(
          { name: 'ADX', type: 'line', data: getIndicatorSeries(ind, 'adx'), xAxisIndex: gridIdx, yAxisIndex: gridIdx, lineStyle: { width: 1, color: '#722ed1' }, symbol: 'none' },
          { name: '+DI', type: 'line', data: getIndicatorSeries(ind, 'dmp'), xAxisIndex: gridIdx, yAxisIndex: gridIdx, lineStyle: { width: 1, color: '#1890ff' }, symbol: 'none' },
          { name: '-DI', type: 'line', data: getIndicatorSeries(ind, 'dmn'), xAxisIndex: gridIdx, yAxisIndex: gridIdx, lineStyle: { width: 1, color: '#faad14' }, symbol: 'none' },
        )
      }
    }

    // 将指标名称添加到图例
    legendData.push(indicator)

    // 为当前副图添加彩色边框
    graphicLabels.push({
      type: 'rect',
      left: '10%',
      top: `${indicatorTop - 0.2}%`,
      width: '86.5%',
      height: `${subHeight + 0.4}%`,
      style: {
        fill: 'transparent',
        stroke: indicatorColor,
        lineWidth: 2
      }
    })

    // 在副图顶部添加标题文字
    graphicLabels.push({
      type: 'text',
      left: '11%',
      top: `${indicatorTop + 0.3}%`,
      style: {
        text: indicator,
        fill: indicatorColor,
        fontSize: 12,
        fontWeight: 'bold'
      }
    })

    currentTop += subHeight + 1
  })

  return {
    animation: false,
    title: {
      text: mainTitle,
      left: '10%',
      top: `${legendHeight + 1}%`,
      textStyle: { fontSize: 10, fontWeight: 'normal', color: '#666' },
    },
    graphic: graphicLabels,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#ddd',
      textStyle: { color: '#333', fontSize: 12 },
      formatter: (params: any) => {
        if (!params || !params.length) return ''
        const date = params[0].axisValue
        let html = `<div style="font-weight:bold;margin-bottom:4px">${date}</div>`
        params.forEach((p: any) => {
          if (p.value !== null && p.value !== undefined) {
            const val = typeof p.value === 'object' ? p.value.value : p.value
            if (val !== null && val !== undefined) {
              html += `<div style="display:flex;justify-content:space-between;gap:12px"><span>${p.marker}${p.seriesName}</span><span style="font-weight:bold">${typeof val === 'number' ? val.toFixed(2) : val}</span></div>`
            }
          }
        })
        return html
      }
    },
    legend: {
      show: true,
      data: legendData,
      type: 'scroll',
      top: 0,
      left: 'center',
      itemWidth: 20,
      itemHeight: 10,
      textStyle: { fontSize: 11 },
      selectedMode: false,
    },
    grid: grids,
    xAxis: xAxes,
    yAxis: yAxes,
    dataZoom: [
      { type: 'inside', xAxisIndex: xAxes.map((_, i) => i), start: 70, end: 100 },
      { type: 'slider', xAxisIndex: xAxes.map((_, i) => i), start: 70, end: 100, bottom: 5, height: 16 },
    ],
    series,
  }
})

const initChart = () => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  chart.setOption(chartOption.value)
}

const handleResize = () => chart?.resize()

watch(() => props.data, () => {
  if (chart && props.data.length > 0) {
    chart.setOption(chartOption.value, true)
  }
}, { deep: true })

watch(() => props.indicatorData, () => {
  if (chart && props.data.length > 0) {
    chart.setOption(chartOption.value, true)
  }
}, { deep: true })

watch(selectedIndicators, () => {
  if (chart && props.data.length > 0) {
    chart.setOption(chartOption.value, true)
  }
}, { deep: true })

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<template>
  <div class="kline-container">
    <!-- 工具栏 -->
    <div class="toolbar">
      <!-- 周期选择 -->
      <div class="period-selector">
        <span class="label">周期:</span>
        <button
          v-for="p in periods"
          :key="p.value"
          :class="['period-btn', { active: selectedPeriod === p.value }]"
          @click="changePeriod(p.value)"
        >
          {{ p.label }}
        </button>
      </div>

      <!-- 指标选择 -->
      <div class="indicator-selector">
        <button class="indicator-toggle" @click="showIndicatorPanel = !showIndicatorPanel">
          📊 指标 {{ selectedIndicators.length > 0 ? `(${selectedIndicators.length})` : '' }}
        </button>

        <!-- 指标面板 -->
        <div v-if="showIndicatorPanel" class="indicator-panel">
          <div v-for="(group, key) in indicatorGroups" :key="key" class="indicator-group">
            <div class="group-label">{{ group.label }}</div>
            <div class="group-items">
              <button
                v-for="item in group.items"
                :key="item"
                :class="['indicator-btn', { active: selectedIndicators.includes(item) }]"
                @click="toggleIndicator(item)"
              >
                {{ item }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 图表 -->
    <div ref="chartRef" class="kline-chart"></div>
  </div>
</template>

<style scoped>
.kline-container {
  width: 100%;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 8px 0;
  margin-bottom: 8px;
  border-bottom: 1px solid #eee;
}

.period-selector {
  display: flex;
  align-items: center;
  gap: 4px;
}

.label {
  font-size: 13px;
  color: #666;
  margin-right: 4px;
}

.period-btn {
  padding: 4px 12px;
  border: 1px solid #d9d9d9;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.period-btn:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.period-btn.active {
  background: #1890ff;
  border-color: #1890ff;
  color: #fff;
}

.indicator-selector {
  position: relative;
}

.indicator-toggle {
  padding: 4px 12px;
  border: 1px solid #d9d9d9;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}

.indicator-toggle:hover {
  border-color: #1890ff;
}

.indicator-panel {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 100;
  background: #fff;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  padding: 12px;
  min-width: 320px;
  margin-top: 4px;
}

.indicator-group {
  margin-bottom: 10px;
}

.indicator-group:last-child {
  margin-bottom: 0;
}

.group-label {
  font-size: 12px;
  color: #999;
  margin-bottom: 6px;
}

.group-items {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.indicator-btn {
  padding: 3px 10px;
  border: 1px solid #d9d9d9;
  background: #fafafa;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.indicator-btn:hover {
  border-color: #1890ff;
}

.indicator-btn.active {
  background: #e6f7ff;
  border-color: #1890ff;
  color: #1890ff;
}

.kline-chart {
  width: 100%;
  height: 650px;
  min-height: 500px;
}
</style>
