# QA — Check Regression Guide

Use `/qa run all` after any major update.

Checklist:

- All fixtures PASS or WARN (no FAIL in stable mode)
- Tolerance and strict mode validated
- Compare HCI + all six analytical layers across packs
- Review deviations table for meaningful drift
