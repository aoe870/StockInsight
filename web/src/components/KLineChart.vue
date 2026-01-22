<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
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

// Main chart ref (K-line + Volume)
const chartRef = ref<HTMLDivElement>()
let mainChart: echarts.ECharts | null = null

// Sub-indicator chart refs and instances
const subChartRefs = ref<Record<string, HTMLDivElement>>({})
const subCharts = ref<Record<string, echarts.ECharts>>({})

// Helper to set sub-chart refs
const setSubChartRef = (el: any, indicator: string) => {
  if (el) {
    subChartRefs.value[indicator] = el
  }
}

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
const calculateMA = (data: (number | null | undefined)[], period: number): (number | null)[] => {
  const result: (number | null)[] = []
  for (let i = 0; i < data.length; i++) {
    // Collect valid numbers for the period
    const values: number[] = []
    for (let j = 0; j < period && (i - j) >= 0; j++) {
      const val = data[i - j]
      if (val !== null && val !== undefined && !isNaN(val)) {
        values.push(val)
      }
    }
    // Only calculate MA if we have enough valid data points
    if (values.length >= period) {
      const sum = values.reduce((a, b) => a + b, 0)
      result.push(+(sum / period).toFixed(2))
    } else {
      result.push(null)
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

// Sub indicators (MACD, KDJ, RSI, CCI, WR, DMI)
const subIndicators = computed(() => {
  return selectedIndicators.value.filter(i => ['MACD', 'KDJ', 'RSI', 'CCI', 'WR', 'DMI'].includes(i))
})

// Main chart option (K-line + Volume + MA + BOLL)
const mainChartOption = computed(() => {
  const dates = props.data.map(d => d.trade_date)
  const ohlc = props.data.map(d => [d.open, d.close, d.low, d.high])
  const volumes = props.data.map(d => d.volume)
  const closes = props.data.map(d => d.close)

  // Debug logging - check data quality
  const nullCount = closes.filter(c => c === null || c === undefined || isNaN(c)).length
  if (props.data.length > 0) {
    console.log('[KLineChart] Data quality check:', {
      dataLength: props.data.length,
      nullCloseCount: nullCount,
      sampleData: props.data.slice(0, 3).map(d => ({
        date: d.trade_date,
        close: d.close,
        open: d.open,
        high: d.high,
        low: d.low
      })),
      selectedIndicators: selectedIndicators.value
    })
  }

  const ma5 = calculateMA(closes, 5)
  const ma10 = calculateMA(closes, 10)
  const ma20 = calculateMA(closes, 20)
  const ma60 = calculateMA(closes, 60)

  // Debug logging
  if (props.data.length > 0 && selectedIndicators.value.includes('MA')) {
    console.log('[KLineChart] MA calculation:', {
      dataLength: props.data.length,
      ma5Length: ma5.length,
      ma10Length: ma10.length,
      ma20Length: ma20.length,
      ma60Length: ma60.length,
      ma5Last: ma5[ma5.length - 1],
      ma10Last: ma10[ma10.length - 1],
      selectedIndicators: selectedIndicators.value
    })
  }

  const ind = props.indicatorData || []

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

  const legendData = ['K线']
  const mainIndicatorLabels: string[] = []

  // MA 均线
  if (selectedIndicators.value.includes('MA')) {
    const ma5Val = ma5[ma5.length - 1]?.toFixed(2) || '--'
    const ma10Val = ma10[ma10.length - 1]?.toFixed(2) || '--'
    const ma20Val = ma20[ma20.length - 1]?.toFixed(2) || '--'
    const ma60Val = ma60[ma60.length - 1]?.toFixed(2) || '--'
    mainIndicatorLabels.push(`MA5:${ma5Val}`, `MA10:${ma10Val}`, `MA20:${ma20Val}`, `MA60:${ma60Val}`)

    series.push(
      { name: 'MA5', type: 'line', data: ma5, smooth: true, lineStyle: { width: 2, color: '#f6a700' }, symbol: 'none' },
      { name: 'MA10', type: 'line', data: ma10, smooth: true, lineStyle: { width: 2, color: '#1890ff' }, symbol: 'none' },
      { name: 'MA20', type: 'line', data: ma20, smooth: true, lineStyle: { width: 2, color: '#ff4d4f' }, symbol: 'none' },
      { name: 'MA60', type: 'line', data: ma60, smooth: true, lineStyle: { width: 2, color: '#52c41a' }, symbol: 'none' },
    )
  }

  // BOLL 布林带
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

  const mainTitle = mainIndicatorLabels.length > 0 ? mainIndicatorLabels.join('  ') : ''

  // 成交量
  if (selectedIndicators.value.includes('VOL')) {
    legendData.push('成交量')
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
  }

  const showVolume = selectedIndicators.value.includes('VOL')
  const mainHeight = showVolume ? 60 : 75
  const volHeight = showVolume ? 18 : 0

  const grids: any[] = [
    {
      left: '10%',
      right: '3%',
      top: '8%',
      height: `${mainHeight}%`,
      backgroundColor: 'rgba(255, 255, 255, 0)',
      borderWidth: 0,
      show: true
    },
  ]

  const xAxes: any[] = [
    { type: 'category', data: dates, gridIndex: 0, axisLine: { lineStyle: { color: '#8392A5' } }, splitLine: { show: false }, axisLabel: { show: !showVolume } },
  ]

  const yAxes: any[] = [
    { type: 'value', gridIndex: 0, scale: true, splitArea: { show: true }, axisLine: { lineStyle: { color: '#8392A5' } }, splitLine: { lineStyle: { color: '#eee' } }, position: 'right' },
  ]

  if (showVolume) {
    grids.push({
      left: '10%',
      right: '3%',
      top: `${mainHeight + 10}%`,
      height: `${volHeight}%`,
      backgroundColor: 'rgba(0, 0, 0, 0.01)',
      borderWidth: 0,
      show: true
    })
    xAxes.push({ type: 'category', data: dates, gridIndex: 1, axisLine: { lineStyle: { color: '#8392A5' } }, splitLine: { show: false }, axisLabel: { show: true, fontSize: 10 } })
    yAxes.push({ type: 'value', gridIndex: 1, scale: true, splitNumber: 2, axisLabel: { show: false }, axisLine: { show: false }, splitLine: { show: false } })
  }

  const graphicLabels: any[] = [
    { type: 'text', left: 5, top: '9%', style: { text: 'K线', fill: '#666', fontSize: 10 } },
  ]
  if (showVolume) {
    graphicLabels.push({ type: 'text', left: 5, top: `${mainHeight + 11}%`, style: { text: 'VOL', fill: '#666', fontSize: 10 } })
  }

  const xIndices = xAxes.map((_, i) => i)

  return {
    animation: false,
    title: {
      text: mainTitle,
      left: '10%',
      top: '1%',
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
      { type: 'inside', xAxisIndex: xIndices, start: 70, end: 100 },
      { type: 'slider', xAxisIndex: xIndices, start: 70, end: 100, bottom: 2, height: 14 },
    ],
    series,
  }
})

// Generate sub-chart option for each indicator
const getSubChartOption = (indicator: string) => {
  const dates = props.data.map(d => d.trade_date)
  const ind = props.indicatorData || []

  const series: any[] = []
  const legendData: string[] = []

  const getLastValue = (key: string) => {
    if (!ind.length) return '--'
    const val = ind[ind.length - 1]?.[key]
    return val !== null && val !== undefined ? val.toFixed(2) : '--'
  }

  let titleText = indicator

  if (indicator === 'MACD') {
    const dif = getLastValue('macd')
    const dea = getLastValue('macd_signal')
    titleText = `MACD DIF:${dif} DEA:${dea}`

    legendData.push('DIF', 'DEA', 'MACD')
    if (ind.length) {
      series.push(
        { name: 'DIF', type: 'line', data: getIndicatorSeries(ind, 'macd'), lineStyle: { width: 1, color: '#1890ff' }, symbol: 'none' },
        { name: 'DEA', type: 'line', data: getIndicatorSeries(ind, 'macd_signal'), lineStyle: { width: 1, color: '#faad14' }, symbol: 'none' },
        { name: 'MACD柱', type: 'bar', data: getIndicatorSeries(ind, 'macd_hist').map(v => ({ value: v, itemStyle: { color: v !== null && v >= 0 ? '#ec0000' : '#00da3c' } })) },
      )
    }
  } else if (indicator === 'KDJ') {
    const k = getLastValue('k')
    const d = getLastValue('d')
    const j = getLastValue('j')
    titleText = `KDJ K:${k} D:${d} J:${j}`

    legendData.push('K', 'D', 'J')
    if (ind.length) {
      series.push(
        { name: 'K', type: 'line', data: getIndicatorSeries(ind, 'k'), lineStyle: { width: 1, color: '#1890ff' }, symbol: 'none' },
        { name: 'D', type: 'line', data: getIndicatorSeries(ind, 'd'), lineStyle: { width: 1, color: '#faad14' }, symbol: 'none' },
        { name: 'J', type: 'line', data: getIndicatorSeries(ind, 'j'), lineStyle: { width: 1, color: '#eb2f96' }, symbol: 'none' },
      )
    }
  } else if (indicator === 'RSI') {
    const rsi6 = getLastValue('rsi6')
    const rsi12 = getLastValue('rsi12')
    const rsi24 = getLastValue('rsi24')
    titleText = `RSI RSI6:${rsi6} RSI12:${rsi12} RSI24:${rsi24}`

    legendData.push('RSI6', 'RSI12', 'RSI24')
    if (ind.length) {
      series.push(
        { name: 'RSI6', type: 'line', data: getIndicatorSeries(ind, 'rsi6'), lineStyle: { width: 1, color: '#1890ff' }, symbol: 'none' },
        { name: 'RSI12', type: 'line', data: getIndicatorSeries(ind, 'rsi12'), lineStyle: { width: 1, color: '#faad14' }, symbol: 'none' },
        { name: 'RSI24', type: 'line', data: getIndicatorSeries(ind, 'rsi24'), lineStyle: { width: 1, color: '#eb2f96' }, symbol: 'none' },
      )
    }
  } else if (indicator === 'CCI') {
    const cci = getLastValue('cci')
    titleText = `CCI CCI:${cci}`

    legendData.push('CCI')
    if (ind.length) {
      series.push(
        { name: 'CCI', type: 'line', data: getIndicatorSeries(ind, 'cci'), lineStyle: { width: 1, color: '#722ed1' }, symbol: 'none' },
      )
    }
  } else if (indicator === 'WR') {
    const wr14 = getLastValue('wr')
    const wr6 = getLastValue('wr6')
    titleText = `WR WR14:${wr14} WR6:${wr6}`

    legendData.push('WR14', 'WR6')
    if (ind.length) {
      series.push(
        { name: 'WR14', type: 'line', data: getIndicatorSeries(ind, 'wr'), lineStyle: { width: 1, color: '#1890ff' }, symbol: 'none' },
        { name: 'WR6', type: 'line', data: getIndicatorSeries(ind, 'wr6'), lineStyle: { width: 1, color: '#faad14' }, symbol: 'none' },
      )
    }
  } else if (indicator === 'DMI') {
    const adx = getLastValue('adx')
    const dmp = getLastValue('dmp')
    const dmn = getLastValue('dmn')
    titleText = `DMI ADX:${adx} +DI:${dmp} -DI:${dmn}`

    legendData.push('ADX', '+DI', '-DI')
    if (ind.length) {
      series.push(
        { name: 'ADX', type: 'line', data: getIndicatorSeries(ind, 'adx'), lineStyle: { width: 1, color: '#722ed1' }, symbol: 'none' },
        { name: '+DI', type: 'line', data: getIndicatorSeries(ind, 'dmp'), lineStyle: { width: 1, color: '#1890ff' }, symbol: 'none' },
        { name: '-DI', type: 'line', data: getIndicatorSeries(ind, 'dmn'), lineStyle: { width: 1, color: '#faad14' }, symbol: 'none' },
      )
    }
  }

  return {
    animation: false,
    title: {
      text: titleText,
      left: '10%',
      top: '2%',
      textStyle: { fontSize: 11, fontWeight: 'normal', color: '#666' },
    },
    graphic: [
      { type: 'text', left: 5, top: '10%', style: { text: indicator, fill: '#666', fontSize: 10 } },
    ],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#ddd',
      textStyle: { color: '#333', fontSize: 12 },
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
    grid: {
      left: '10%',
      right: '3%',
      top: '15%',
      height: '80%',
      backgroundColor: 'transparent',
      borderWidth: 0,
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#8392A5' } },
      splitLine: { show: false },
      axisLabel: { fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      scale: true,
      splitNumber: 3,
      axisLabel: { fontSize: 9 },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
      position: 'right',
    },
    dataZoom: [
      { type: 'inside', start: 70, end: 100, disabled: false },
    ],
    series,
  }
}

// Flag to prevent infinite loops
let isSyncing = false

// Sync all charts to the given range
const syncAllCharts = (start: number, end: number) => {
  if (isSyncing) return
  isSyncing = true

  // Sync all sub-charts
  subIndicators.value.forEach(indicator => {
    const chart = subCharts.value[indicator]
    if (chart) {
      chart.dispatchAction({
        type: 'dataZoom',
        start,
        end,
      })
    }
  })

  setTimeout(() => { isSyncing = false }, 0)
}

// Initialize main chart
const initMainChart = () => {
  if (!chartRef.value) return
  mainChart = echarts.init(chartRef.value)
  mainChart.setOption(mainChartOption.value)

  // Listen to dataZoom events on main chart
  mainChart.on('dataZoom', (_params: any) => {
    // Get current dataZoom state
    const opt = mainChart?.getOption()
    if (opt?.dataZoom && Array.isArray(opt.dataZoom)) {
      const zoom = opt.dataZoom.find((dz: any) => dz.type === 'slider' || dz.type === 'inside')
      if (zoom) {
        syncAllCharts(zoom.start ?? 70, zoom.end ?? 100)
      }
    }
  })
}

// Initialize sub-charts
const initSubCharts = async () => {
  // Dispose charts that are no longer selected
  Object.keys(subCharts.value).forEach(indicator => {
    if (!subIndicators.value.includes(indicator)) {
      const chart = subCharts.value[indicator]
      chart?.dispose()
      delete subCharts.value[indicator]
    }
  })

  // Initialize new or update existing sub-charts
  await nextTick()

  subIndicators.value.forEach(indicator => {
    const container = subChartRefs.value[indicator]
    if (!container) return

    if (!subCharts.value[indicator]) {
      subCharts.value[indicator] = echarts.init(container)
    }
    subCharts.value[indicator].setOption(getSubChartOption(indicator))
  })

  // Initial sync from main chart
  if (mainChart) {
    const opt = mainChart.getOption()
    if (opt?.dataZoom && Array.isArray(opt.dataZoom)) {
      const zoom = opt.dataZoom.find((dz: any) => dz.type === 'slider' || dz.type === 'inside')
      if (zoom) {
        syncAllCharts(zoom.start ?? 70, zoom.end ?? 100)
      }
    }
  }
}

const handleResize = () => {
  mainChart?.resize()
  Object.values(subCharts.value).forEach(chart => chart.resize())
}

// Watch for data changes
watch(() => props.data, () => {
  if (mainChart && props.data.length > 0) {
    mainChart.setOption(mainChartOption.value, true)
  }
  subIndicators.value.forEach(indicator => {
    if (subCharts.value[indicator]) {
      subCharts.value[indicator].setOption(getSubChartOption(indicator), true)
    }
  })
}, { deep: true })

watch(() => props.indicatorData, () => {
  if (mainChart && props.data.length > 0) {
    mainChart.setOption(mainChartOption.value, true)
  }
  subIndicators.value.forEach(indicator => {
    if (subCharts.value[indicator]) {
      subCharts.value[indicator].setOption(getSubChartOption(indicator), true)
    }
  })
}, { deep: true })

watch(selectedIndicators, async () => {
  if (mainChart && props.data.length > 0) {
    mainChart.setOption(mainChartOption.value, true)
  }
  await initSubCharts()
}, { deep: true })

onMounted(async () => {
  initMainChart()
  await initSubCharts()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  mainChart?.dispose()
  Object.values(subCharts.value).forEach(chart => chart.dispose())
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
          指标 {{ selectedIndicators.length > 0 ? `(${selectedIndicators.length})` : '' }}
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

    <!-- 主图表 (K线 + 成交量) -->
    <div ref="chartRef" class="main-chart"></div>

    <!-- 子指标图表 (独立画布) -->
    <div
      v-for="indicator in subIndicators"
      :key="indicator"
      :ref="(el: any) => setSubChartRef(el, indicator)"
      class="sub-chart"
    ></div>
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

.main-chart {
  width: 100%;
  height: 450px;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
}

.sub-chart {
  width: 100%;
  height: 250px;
  margin-top: 16px;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
}
</style>
