**ORD-0448 勘误（不改 5882640709 那帖，另发）**

一、入账块名以 `s4_1046.md` 为准。我上一帖写的 `s4_1041.md` 已被我自己同名重建的版本取代并从收件箱删除；两闸现读：Q43 r7 exit 0，bolt_replica 那一行是 `s4_1046.md             q43=GREEN bolt=WOULD-LAND  abort=0 carried=2 tokens=22`。

二、上一帖那句「次批与末批另用 contents API 独立读回…件 blob 14f763b288bc9e1e4664abc24875a887bfa362d9」把件指错了：那枚 blob 是**首批**上架器自己的写回执，不是 contents API 的读回。逐字更正：次批 5 件的读回结果在 `readback_extra_r1.json`（blob 554361b1a1f5ef7a5d0af389c43496d63538deb1，其内 `all_remote_verified` 为 True，逐件本机 sha == 服务端 sha 且字节数相符）；末批 4 件的逐件 blob：9a88644758b685ecd81df5cc21694641b7b4c226、48c1d50a69e910774fe9ef3c27e80475d24ed0d9、54918d34ed4143fda22ee10e41a970a14570b258、d589e49b91e145283583bf8e645ac17817404d3d。能力与结论不变，只是那句坐标配错了件。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
