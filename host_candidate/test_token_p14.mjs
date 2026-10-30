import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
const js=fs.readFileSync(process.argv[2],"utf8");
const start=js.indexOf("function mpClassifyTurnUsage(");
const end=js.indexOf("function mpPatchUsageUnknownHeader(",start);
assert.ok(start>=0&&end>start,"P14 classifier not found");
const sandbox={};
vm.createContext(sandbox);
vm.runInContext("function mpNormUsageText(x){return String(x||'').replace(/\\s+/g,' ').trim();}\n"+js.slice(start,end),sandbox);
const classify=sandbox.mpClassifyTurnUsage;
const norm=(x)=>JSON.parse(JSON.stringify(x));
assert.deepEqual(norm(classify("22 tok","70 tok",null)),{kind:"provider",input:22,output:70});
assert.deepEqual(norm(classify("0 tok","68 tok",{inputTokens:300,outputTokens:20,totalTokens:320})),
    {kind:"provider",input:0,output:68});
assert.deepEqual(norm(classify("0 tok","0 tok",null)),{kind:"unavailable"});
assert.deepEqual(norm(classify("0 tok","0 tok",{inputTokens:200,outputTokens:0,totalTokens:200})),
    {kind:"unavailable"});
assert.deepEqual(norm(classify("0 tok","0 tok",{inputTokens:200,outputTokens:25,totalTokens:225,source:"dom"})),
    {kind:"estimate",input:200,output:25,total:225,source:"dom"});
assert.deepEqual(norm(classify("≈200 tok","≈25 tok",null)),
    {kind:"estimate",input:200,output:25,total:225,source:"visible-estimate"});
assert.deepEqual(norm(classify("5 tok","≈25 tok",null)),
    {kind:"mixed",input:5,output:25});
assert.deepEqual(norm(classify("≈15 tok","30 tok",null)),
    {kind:"mixed",input:15,output:30});
assert.deepEqual(norm(classify("≈0 tok","1 tok",null)),
    {kind:"mixed",input:0,output:1});
assert.deepEqual(norm(classify("— tok","— tok",null)),{kind:"other"});
assert.deepEqual(norm(classify("0 tok","unknown",null)),{kind:"other"});
assert.deepEqual(norm(classify("0 tok","0 tok",{inputTokens:100,outputTokens:3,totalTokens:1e20})),
    {kind:"unavailable"});
assert.deepEqual(norm(classify("1,500 tok","400 tok",null)),{kind:"provider",input:1500,output:400});
assert.equal(js.includes("function mpPatchUsageUnknownHeader("),true);
assert.equal(js.includes("本轮用量（未提供）"),true);
assert.equal(js.includes("本轮用量（估算）"),true);
assert.equal(js.includes("本轮用量（来源混合）"),true);
assert.equal(js.includes("panel.dataset.mpUsageMixed='1'"),true);
assert.ok(js.includes("if (estInput || estOutput)"),"mixed-provenance logic required");
console.log("P14_PROVIDER_VALUES_PRESERVED=PASS");
console.log("P14_PARTIAL_REAL_PROVIDER_UNCHANGED=PASS");
console.log("P14_HONEST_ESTIMATES=PASS");
console.log("P14_UNKNOWN_NEVER_FAKED_AS_ZERO=PASS");
console.log("P14_MIXED_FIELD_PROVENANCE_NOT_PROMOTED=PASS");
console.log("P14_LAN_API_REAL_TOKEN_USAGE=NOT_VERIFIED");
