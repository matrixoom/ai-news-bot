/**
 * 根据收盘价序列计算简单移动平均线。
 * @param data 按时间升序排列的数值序列。
 * @param period 移动平均窗口长度。
 * @returns 与输入等长的移动平均序列，窗口未满足时返回空值。
 */
export function calculateSMA(data: number[], period: number): (number | null)[] {
  return data.map((_, index) => {
    if (index < period - 1) return null;
    let sum = 0;
    for (let i = index - period + 1; i <= index; i++) {
      sum += data[i];
    }
    return Number((sum / period).toFixed(4));
  });
}

export const MA_CONFIGS = [
  { period: 20, label: "MA20", color: "#94a3b8" },
  { period: 60, label: "MA60", color: "#f59e0b" },
  { period: 120, label: "MA120", color: "#10b981" },
  { period: 126, label: "半年均线", color: "#3b82f6" },
  { period: 252, label: "年均线", color: "#ef4444" },
] as const;
