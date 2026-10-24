import { basePrice, discount } from "../src/pricing.js";

console.log(basePrice("vip") === 90, discount(100, 10) === 90);
