# Music Advisor — Release Checklist

## 1) Bump

- Update `Knowledge/CHANGELOG.md`
- If norms changed, bump `norm_version` in Manifest

## 2) Validate

- `/qa run all` (strict=false): ALL PASS or WARN only
- `/qa set strict true` → `/qa run all`: ALL PASS (no FAIL)

## 3) Smoke

```shell
/cp start
/cp edit genre=Pop
/cp edit region=US
/cp finalize
/advisor ingest
/advisor run full
/advisor export summary
```

## 4) Research sanity

```shell
/research seed "<brief query>" region=<X> profile=<Y>
/research scan depth=2 window=90 platforms=press,spotify
/research compile
/research build pack
/research finalize
/advisor run full
```

## 5) Package

- Root folder name **MusicAdvisor/** (no double nesting)
- Remove `__MACOSX/`, `.DS_Store`, `._*`
- Run manifest builder to refresh checksums/sizes

## 6) Upload & Tag

- Upload ZIP to GPT Knowledge
- Save Instruction snapshot and tag version in `CHANGELOG.md`

## Release Checklist

Pre-release QA

- [ ] Boot self-test passes
- [ ] Templates render correctly
- [ ] Baseline block present in exports:
      Baseline.active_profile, effective_utc, previous_profile, pinned
- [ ] One-time banner on baseline change; badge when pinned
- [ ] /baseline pin|unpin|status commands wired in router

Post-release Monitoring

- [ ] Verify default baseline id for regions (US_Pop_2025 for US)
- [ ] Confirm no regressions in HCI_v1 logic (unchanged)
