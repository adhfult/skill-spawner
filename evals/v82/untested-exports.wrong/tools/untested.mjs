import { readdirSync, readFileSync } from "node:fs";
for (const f of readdirSync("src").sort()) {
  const src = readFileSync(`src/${f}`, "utf8");
  for (const m of src.matchAll(/^export (?:async )?function (\w+)/gm)) console.log(`src/${f} ${m[1]}`);
}
