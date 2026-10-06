export function money(value) {
  return `₹${Number(value).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}