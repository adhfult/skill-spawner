export const TAX_RATE = 0.2;

export function basePrice(kind: string): number {
  return kind === "vip" ? 90 : 40;
}

export function discount(price: number, pct: number): number {
  return price - (price * pct) / 100;
}

function internalRound(n: number): number {
  return Math.round(n * 100) / 100;
}
