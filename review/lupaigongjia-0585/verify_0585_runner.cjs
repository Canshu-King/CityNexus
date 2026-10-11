const path=require("path");
const esbuild=require(path.join("D:/moodle/_qoder_lupaigongjia_0576/frontend","node_modules","esbuild"));
(async()=>{
  await esbuild.build({entryPoints:["D:/moodle/_qoder_lupaigongjia_0576/frontend/src/__verify0585/probe.ts"],bundle:true,format:"cjs",platform:"node",
    jsx:"automatic",external:["react","react/jsx-runtime"],outfile:"D:/moodle/_qoder_lupaigongjia_0576/frontend/src/__verify0585/bundle.cjs",logLevel:"silent"});
  const v=require("D:/moodle/_qoder_lupaigongjia_0576/frontend/src/__verify0585/bundle.cjs").read("recovery.acceptanceUnanswered");
  process.stdout.write(JSON.stringify(v));
})().catch(e=>{console.error(String(e.message||e).slice(0,400));process.exit(1)});
