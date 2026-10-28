"use strict";
function pctChange(open, close) {
    return ((close - open) / open) * 100;
}
function isStrong(signal) {
    return signal.strength > 60;
}
const prices = [93.8, 94.1, 93.2, 95.0];
const highPrices = prices
    .filter((price) => price > 93.5)
    .map((price) => `${price.toFixed(2)} ▲`);
const signal = { symbol: "ES", strength: 72, side: "long" };
console.log(`ES change: ${pctChange(93.8, 95.0).toFixed(2)}%`);
console.log(`Signal strong: ${isStrong(signal)}`);
console.log(`High prices: ${highPrices.join(", ")}`);
