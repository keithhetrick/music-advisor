# QA Runbook

## US Pop (1985 Echo emphasis)

1. Paste `QA/US_Pop.fixture.json`
2. /advisor ingest
3. /advisor run full
4. Expect: Historical high (HEC_40 dominant), HCI stable across versions
5. /dashboard validate → should be OK

## Global K-Pop (modern echo + market fit)

1. Paste `QA/Global_KPop.fixture.json`
2. /advisor ingest
3. /advisor run full
4. Expect: Market/Sonic strong; Historical shows mixed era support

## LATAM Urban (rhythm-led contemporary)

1. Paste `QA/LATAM_Urban.fixture.json`
2. /advisor ingest
3. /advisor run full
4. Expect: Solid Market/Emotional; Historical moderate; HCI consistent

## Optional

- /datahub save "US Pop baseline" → /datahub list → /datahub load <id>
- /dashboard compare (paste two packs to view diffs)
