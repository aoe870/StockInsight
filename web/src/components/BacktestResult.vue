<script setup lang="ts">
import { ref, computed } from 'vue'
import * as echarts from 'echarts'
import type { BacktestResultResponse } from '@/api/backtest'

interface Props {
  result: BacktestResultResponse
}

const props = defineProps<Props>()
const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

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

// 绘制资金曲线
const drawEquityCurve = () => {
  if (!chartRef.value || !props.result.equity_curve.length) return

  chart = echarts.init(chartRef.value)

  const dates = props.result.equity_curve.map(d => d.date)
  const equity = props.result.equity_curve.map(d => d.equity)
  const initial = props.result.performance.initial_cash

  const option = {
    title: {
      text: '资金曲线',
      left: 'center',
      textStyle: { fontSize: 14 }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['账户净值', '收益率'],
      top: 25
    },
    grid: {
      left: '60px',
      right: '60px',
      bottom: '60px',
      top: '60px'
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#8392A5' } }
    },
    yAxis: [
      {
        type: 'value',
        name: '账户净值',
        position: 'left',
        axisLine: { show: true, lineStyle: { color: '#8392A5' } },
        splitLine: { lineStyle: { color: '#eee' } }
      },
      {
        type: 'value',
        name: '收益率',
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
        data: equity,
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
        name: '收益率',
        type: 'line',
        yAxisIndex: 1,
        data: equity.map(v => ((v - initial) / initial) * 100),
        smooth: true,
        lineStyle: { width: 2, color: '#67C23A' }
      }
    ],
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, bottom: 10 }
    ]
  }

  chart.setOption(option)
}

// 组件挂载后绘制图表
const mounted = ref(false)
const initChart = () => {
  if (!mounted.value) {
    mounted.value = true
    setTimeout(drawEquityCurve, 100)
  }
}

initChart()
</script>

<template>
  <div class="backtest-result">
    <!-- 绩效指标 -->
    <div class="metrics-section">
      <h3>绩效指标</h3>

      <div class="metrics-grid">
        <!-- 收益指标 -->
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

        <!-- 风险指标 -->
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

        <!-- 交易统计 -->
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

    <!-- 资金曲线 -->
    <div class="chart-section">
      <h3>资金曲线</h3>
      <div ref="chartRef" class="chart"></div>
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
  gap: 24px;
}

.backtest-result h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #333;
}

.metrics-section,
.chart-section,
.trades-section {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 16px;
}

.metric-card {
  padding: 12px;
  background: #f9f9f9;
  border-radius: 6px;
  text-align: center;
}

.metric-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.chart {
  width: 100%;
  height: 400px;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #999;
}

.trades-table {
  width: 100%;
  border-collapse: collapse;
}

.trades-table th,
.trades-table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.trades-table th {
  font-weight: 600;
  color: #666;
  background: #f9f9f9;
}

.trades-table tbody tr:hover {
  background: #f9f9f9;
}

.buy-action {
  color: #f56c6c;
}

.sell-action {
  color: #67c23a;
}
</style>
