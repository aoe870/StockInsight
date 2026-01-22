<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { BacktestResultResponse } from '@/api/backtest'
import type { EChartsOption } from 'echarts'

interface Props {
  result: BacktestResultResponse
}

const props = defineProps<Props>()

// 图表 refs
const equityChartRef = ref<HTMLDivElement>()
const drawdownChartRef = ref<HTMLDivElement>()
const positionsChartRef = ref<HTMLDivElement>()
const monthlyReturnRef = ref<HTMLDivElement>()

let equityChart: echarts.ECharts | null = null
let drawdownChart: echarts.ECharts | null = null
let positionsChart: echarts.ECharts | null = null
let monthlyReturnChart: echarts.ECharts | null = null

// 格式化百分比
const formatPercent = (value: number, digits = 2) => {
  return (value * 100).toFixed(digits) + '%'
}

// 格式化金额
const formatAmount = (value: number) => {
  return value.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY' })
}

// 盈亏颜色
const getProfitColor = (value: number) => {
  return value >= 0 ? '#f56c6c' : '#67c23a'
}

// 计算回撤曲线
const calculateDrawdown = (equity: number[]) => {
  const drawdown: number[] = []
  let peak = equity[0] || 0

  for (let i = 0; i < equity.length; i++) {
    if (equity[i] > peak) {
      peak = equity[i]
    }
    const dd = peak > 0 ? ((equity[i] - peak) / peak) * 100 : 0
    drawdown.push(dd)
  }

  return drawdown
}

// 计算月度收益
const calculateMonthlyReturns = () => {
  const equity = props.result.equity_curve
  if (!equity.length) return null

  const monthlyData: Record<string, number> = {}
  const years = new Set<string>()
  const months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']

  for (let i = 1; i < equity.length; i++) {
    const date = equity[i].date
    const prevEquity = equity[i - 1].equity
    const currEquity = equity[i].equity

    const [year, month] = date.split('-').slice(0, 2)
    const key = `${year}-${month}`

    if (!monthlyData[key]) {
      monthlyData[key] = 0
    }

    const ret = ((currEquity - prevEquity) / prevEquity) * 100
    monthlyData[key] += ret
    years.add(year)
  }

  // 转换为热力图数据格式 [month, year, value]
  const heatmapData: [number, number, number][] = []
  const sortedYears = Array.from(years).sort()

  sortedYears.forEach((year, yearIdx) => {
    months.forEach((month, monthIdx) => {
      const key = `${year}-${month}`
      const value = monthlyData[key] || 0
      heatmapData.push([monthIdx, yearIdx, value])
    })
  })

  return { heatmapData, years: sortedYears, months }
}

// 绘制资金曲线
const drawEquityCurve = () => {
  if (!equityChartRef.value) return

  if (!equityChart) {
    equityChart = echarts.init(equityChartRef.value)
  }

  const equity = props.result.equity_curve
  if (!equity.length) return

  const dates = equity.map(d => d.date)
  const equityValues = equity.map(d => d.equity)
  const initial = props.result.performance.initial_cash

  // 计算基准线
  const baseline = equityValues.map((_, i) => initial * (1 + 0.03 * (i / equity.length)))

  // 计算回撤
  const drawdown = calculateDrawdown(equityValues)

  const option: EChartsOption = {
    title: { text: '资金曲线', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any) => {
        if (!params || !params.length) return ''
        const date = params[0].axisValue
        let html = `<div style="font-weight:bold;margin-bottom:8px">${date}</div>`
        params.forEach((p: any) => {
          if (p.seriesName === '收益率' || p.seriesName === '回撤') {
            html += `<div>${p.marker}${p.seriesName}: ${p.value.toFixed(2)}%</div>`
          } else {
            html += `<div>${p.marker}${p.seriesName}: ${formatAmount(p.value)}</div>`
          }
        })
        return html
      }
    },
    legend: { data: ['账户净值', '基准线', '收益率', '回撤'], top: 25 },
    grid: { left: '50px', right: '50px', bottom: '60px', top: '60px' },
    xAxis: { type: 'category', data: dates, axisLine: { lineStyle: { color: '#8392A5' } } },
    yAxis: [
      {
        type: 'value',
        name: '账户净值',
        position: 'left',
        axisLine: { show: true, lineStyle: { color: '#8392A5' } },
        splitLine: { lineStyle: { color: '#eee' } },
        axisLabel: { formatter: (value: number) => (value / 10000).toFixed(0) + '万' }
      },
      {
        type: 'value',
        name: '收益率/回撤(%)',
        position: 'right',
        axisLine: { show: true, lineStyle: { color: '#8392A5' } },
        axisLabel: { formatter: '{value}%' },
        splitLine: { show: false }
      }
    ],
    series: [
      {
        name: '账户净值',
        type: 'line',
        data: equityValues,
        smooth: true,
        lineStyle: { width: 2, color: '#409EFF' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
              { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
            ]
          }
        }
      },
      {
        name: '基准线',
        type: 'line',
        data: baseline,
        smooth: true,
        lineStyle: { width: 1, color: '#909399', type: 'dashed' },
        symbol: 'none'
      },
      {
        name: '收益率',
        type: 'line',
        yAxisIndex: 1,
        data: equityValues.map(v => ((v - initial) / initial) * 100),
        smooth: true,
        lineStyle: { width: 1.5, color: '#67C23A' },
        symbol: 'none'
      },
      {
        name: '回撤',
        type: 'line',
        yAxisIndex: 1,
        data: drawdown,
        smooth: true,
        lineStyle: { width: 1, color: '#f56c6c' },
        symbol: 'none'
      }
    ],
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, bottom: 10 }
    ]
  }

  equityChart.setOption(option, true)
}

// 绘制回撤曲线
const drawDrawdownCurve = () => {
  if (!drawdownChartRef.value) return

  if (!drawdownChart) {
    drawdownChart = echarts.init(drawdownChartRef.value)
  }

  const equity = props.result.equity_curve
  if (!equity.length) return

  const dates = equity.map(d => d.date)
  const equityValues = equity.map(d => d.equity)
  const drawdownData = calculateDrawdown(equityValues)

  const option: EChartsOption = {
    title: { text: '回撤曲线', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any) => {
        if (!params || !params.length) return ''
        const date = params[0].axisValue
        const dd = params[0].value
        return `<div>${date}</div><div>回撤: ${dd.toFixed(2)}%</div>`
      }
    },
    grid: { left: '50px', right: '30px', bottom: '50px', top: '50px' },
    xAxis: { type: 'category', data: dates, axisLine: { lineStyle: { color: '#8392A5' } } },
    yAxis: {
      type: 'value',
      name: '回撤(%)',
      axisLine: { show: true, lineStyle: { color: '#8392A5' } },
      axisLabel: { formatter: '{value}%' },
      splitLine: { lineStyle: { color: '#eee' } }
    },
    series: [
      {
        name: '回撤',
        type: 'line',
        data: drawdownData,
        smooth: true,
        lineStyle: { width: 2, color: '#f56c6c' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(245, 108, 108, 0.4)' },
              { offset: 1, color: 'rgba(245, 108, 108, 0.1)' }
            ]
          }
        }
      }
    ],
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, bottom: 10 }
    ]
  }

  drawdownChart.setOption(option, true)
}

// 绘制持仓分布图
const drawPositionsChart = () => {
  if (!positionsChartRef.value) return

  if (!positionsChart) {
    positionsChart = echarts.init(positionsChartRef.value)
  }

  const equity = props.result.equity_curve
  if (!equity.length) return

  const dates = equity.map(d => d.date)
  const positions = equity.map(d => d.positions)

  const option: EChartsOption = {
    title: { text: '持仓数量', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any) => {
        if (!params || !params.length) return ''
        const date = params[0].axisValue
        const pos = params[0].value
        return `<div>${date}</div><div>持仓数: ${pos}</div>`
      }
    },
    grid: { left: '50px', right: '30px', bottom: '50px', top: '50px' },
    xAxis: { type: 'category', data: dates, axisLine: { lineStyle: { color: '#8392A5' } } },
    yAxis: {
      type: 'value',
      name: '持仓数',
      minInterval: 1,
      axisLine: { show: true, lineStyle: { color: '#8392A5' } },
      splitLine: { lineStyle: { color: '#eee' } }
    },
    series: [
      {
        name: '持仓数',
        type: 'bar',
        data: positions,
        itemStyle: { color: '#409EFF' }
      }
    ],
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, bottom: 10 }
    ]
  }

  positionsChart.setOption(option, true)
}

// 绘制月度收益热力图
const drawMonthlyReturn = () => {
  if (!monthlyReturnRef.value) return

  if (!monthlyReturnChart) {
    monthlyReturnChart = echarts.init(monthlyReturnRef.value)
  }

  const monthlyData = calculateMonthlyReturns()
  if (!monthlyData) return

  const { heatmapData, years, months } = monthlyData

  const option: EChartsOption = {
    title: { text: '月度收益热力图', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {
      position: 'top',
      formatter: (params: any) => {
        const [month, year, value] = params.data
        const yearLabel = years[year]
        const monthLabel = months[month]
        return `${yearLabel}年${monthLabel}月<br/>收益: ${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
      }
    },
    grid: { height: '70%', top: '15%', left: '8%', right: '3%' },
    xAxis: {
      type: 'category',
      data: months.map(m => parseInt(m) + '月'),
      splitArea: { show: true },
      axisLine: { lineStyle: { color: '#8392A5' } }
    },
    yAxis: {
      type: 'category',
      data: years,
      splitArea: { show: true },
      axisLine: { lineStyle: { color: '#8392A5' } }
    },
    visualMap: {
      min: -10,
      max: 10,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '3%',
      inRange: { color: ['#67C23A', '#FAD614', '#f56c6c'] },
      text: ['盈利', '亏损']
    },
    series: [
      {
        name: '月度收益',
        type: 'heatmap',
        data: heatmapData,
        label: {
          show: true,
          formatter: (params: any) => {
            const value = params.data[2]
            return (value >= 0 ? '+' : '') + value.toFixed(1) + '%'
          },
          fontSize: 9
        }
      }
    ]
  }

  monthlyReturnChart.setOption(option, true)
}

// 初始化所有图表
const initCharts = async () => {
  await nextTick()

  setTimeout(() => {
    drawEquityCurve()
    drawDrawdownCurve()
    drawPositionsChart()
    drawMonthlyReturn()
  }, 200)
}

// 窗口大小改变时重绘
const handleResize = () => {
  equityChart?.resize()
  drawdownChart?.resize()
  positionsChart?.resize()
  monthlyReturnChart?.resize()
}

// 监听结果变化
watch(() => props.result, () => {
  initCharts()
}, { deep: true })

onMounted(() => {
  initCharts()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  equityChart?.dispose()
  drawdownChart?.dispose()
  positionsChart?.dispose()
  monthlyReturnChart?.dispose()
})
</script>

<template>
  <div class="backtest-result">
    <!-- 绩效指标 -->
    <div class="metrics-section">
      <h3>绩效指标</h3>
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-label">总收益率</div>
          <div class="metric-value" :style="{ color: getProfitColor(result.performance.total_return) }">
            {{ formatPercent(result.performance.total_return) }}
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-label">年化收益率</div>
          <div class="metric-value" :style="{ color: getProfitColor(result.performance.annual_return) }">
            {{ formatPercent(result.performance.annual_return) }}
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-label">初始资金</div>
          <div class="metric-value">{{ formatAmount(result.performance.initial_cash) }}</div>
        </div>

        <div class="metric-card">
          <div class="metric-label">最终资金</div>
          <div class="metric-value" :style="{ color: getProfitColor(result.performance.final_cash - result.performance.initial_cash) }">
            {{ formatAmount(result.performance.final_cash) }}
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-label">最大回撤</div>
          <div class="metric-value" style="color: #f56c6c;">
            {{ formatPercent(Math.abs(result.performance.max_drawdown)) }}
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-label">夏普比率</div>
          <div class="metric-value">
            {{ result.performance.sharpe_ratio?.toFixed(2) || '-' }}
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-label">回撤持续天数</div>
          <div class="metric-value">{{ result.performance.max_drawdown_duration }} 天</div>
        </div>

        <div class="metric-card">
          <div class="metric-label">总交易次数</div>
          <div class="metric-value">{{ result.performance.total_trades }}</div>
        </div>

        <div class="metric-card">
          <div class="metric-label">盈利次数</div>
          <div class="metric-value" style="color: #f56c6c;">
            {{ result.performance.profitable_trades }}
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-label">亏损次数</div>
          <div class="metric-value" style="color: #67c23a;">
            {{ result.performance.losing_trades }}
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-label">胜率</div>
          <div class="metric-value">
            {{ formatPercent(result.performance.win_rate) }}
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-label">平均盈利</div>
          <div class="metric-value" style="color: #f56c6c;">
            {{ formatAmount(result.performance.avg_profit) }}
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-label">平均亏损</div>
          <div class="metric-value" style="color: #67c23a;">
            {{ formatAmount(result.performance.avg_loss) }}
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-label">盈亏比</div>
          <div class="metric-value">
            {{ result.performance.profit_loss_ratio.toFixed(2) }}
          </div>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-container">
      <!-- 资金曲线 - 全宽 -->
      <div class="chart-card full-width">
        <h3>资金曲线</h3>
        <div ref="equityChartRef" class="chart-container large"></div>
      </div>

      <!-- 回撤曲线 -->
      <div class="chart-card">
        <h3>回撤曲线</h3>
        <div ref="drawdownChartRef" class="chart-container"></div>
      </div>

      <!-- 持仓数量 -->
      <div class="chart-card">
        <h3>持仓数量</h3>
        <div ref="positionsChartRef" class="chart-container"></div>
      </div>

      <!-- 月度收益 - 全宽 -->
      <div class="chart-card full-width">
        <h3>月度收益热力图</h3>
        <div ref="monthlyReturnRef" class="chart-container medium"></div>
      </div>
    </div>

    <!-- 交易记录 -->
    <div class="trades-section">
      <h3>交易记录</h3>

      <div v-if="result.trades.length === 0" class="empty-state">
        暂无交易记录
      </div>

      <table v-else class="trades-table">
        <thead>
          <tr>
            <th>日期</th>
            <th>代码</th>
            <th>名称</th>
            <th>操作</th>
            <th>价格</th>
            <th>数量</th>
            <th>金额</th>
            <th>盈亏</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(trade, idx) in result.trades.slice().reverse()" :key="idx">
            <td>{{ trade.date }}</td>
            <td>{{ trade.code }}</td>
            <td>{{ trade.name }}</td>
            <td>
              <span :class="trade.action === 'buy' ? 'buy-action' : 'sell-action'">
                {{ trade.action === 'buy' ? '买入' : '卖出' }}
              </span>
            </td>
            <td>{{ trade.price.toFixed(2) }}</td>
            <td>{{ trade.shares }}</td>
            <td>{{ formatAmount(trade.amount) }}</td>
            <td v-if="trade.profit !== undefined">
              <span :style="{ color: getProfitColor(trade.profit) }">
                {{ trade.profit >= 0 ? '+' : '' }}{{ formatAmount(trade.profit) }}
              </span>
            </td>
            <td v-else>-</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.backtest-result {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 0;
}

.backtest-result h3 {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: #333;
}

.metrics-section,
.chart-card,
.trades-section {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 12px;
}

.metric-card {
  padding: 10px;
  background: #f5f7fa;
  border-radius: 6px;
  text-align: center;
  transition: all 0.2s;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.metric-label {
  font-size: 11px;
  color: #909399;
  margin-bottom: 6px;
}

.metric-value {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.charts-container {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.full-width {
  grid-column: 1 / -1;
}

.chart-container {
  width: 100%;
  min-height: 300px;
}

.chart-container.large {
  min-height: 400px;
}

.chart-container.medium {
  min-height: 350px;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #909399;
}

.trades-table {
  width: 100%;
  border-collapse: collapse;
}

.trades-table th,
.trades-table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #ebeef5;
}

.trades-table th {
  font-weight: 600;
  color: #606266;
  background: #f5f7fa;
}

.trades-table tbody tr:hover {
  background: #f5f7fa;
}

.buy-action {
  color: #f56c6c;
  font-weight: 600;
}

.sell-action {
  color: #67c23a;
  font-weight: 600;
}

@media (max-width: 1024px) {
  .charts-container {
    grid-template-columns: 1fr;
  }

  .metrics-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .backtest-result h3 {
    font-size: 14px;
  }
}
</style>
