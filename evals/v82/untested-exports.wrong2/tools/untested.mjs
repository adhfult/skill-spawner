import { readdirSync, readFileSync } from "node:fs";
const tests = readdirSync("test").map((f) => readFileSync(`test/${f}`, "utf8")).join("\n");
const f = readdirSync("src").sort()[0];
const src = readFileSync(`src/${f}`, "utf8");
for (const m of src.matchAll(/^export (?:async )?function (\w+)/gm)) {
  if (!new RegExp(`\\b${m[1]}\\b`).test(tests)) console.log(`src/${f} ${m[1]}`);
}
