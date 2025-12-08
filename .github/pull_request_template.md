## Summary

<!-- Provide a brief description of what this PR does -->

### Why / What Changed

<!-- Explain the motivation for these changes and what problem they solve -->

### Related Issues

<!-- Link to related issues (use "Fixes #123" or "Closes #456" to auto-close issues) -->

- Fixes #
- Related to #

## Type of Change

<!-- Check all that apply -->

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📖 Documentation update
- [ ] 🧪 Test addition or update
- [ ] 🎨 UI/UX change
- [ ] ♻️ Code refactoring (no functional changes)
- [ ] ⚡ Performance improvement
- [ ] 🔒 Security fix

## Changes Made

<!-- Provide a detailed list of changes made in this PR -->

- 
- 
- 

## User-Facing Changes

<!-- Are there any user-facing or pipeline behavior changes? -->

- [ ] Yes (describe below)
- [ ] No

<!-- If yes, describe what users need to know about these changes -->

## Testing

### Tests Run

<!-- Check all that apply and provide details -->

- [ ] `make quick-check` (full test suite)
- [ ] `infra/scripts/test_affected.sh` (affected tests only)
- [ ] `make lint` and `make typecheck` (if applicable)
- [ ] Component-specific tests: <!-- specify -->
- [ ] Manual testing: <!-- describe -->
- [ ] Other: <!-- specify -->

### Test Results

<!-- Paste relevant test output or summarize results -->

```
(test output here)
```

### New Tests Added

<!-- Did you add new tests? -->

- [ ] Yes (describe below)
- [ ] No (explain why not)

<!-- If yes, describe the new tests -->

## Documentation

- [ ] Documentation updated (paths/commands/behavior)
- [ ] README.md updated (if applicable)
- [ ] Docs in `docs/` directory updated
- [ ] Code comments added for complex logic
- [ ] No documentation changes needed

## Security Checklist

- [ ] No secrets, tokens, or presigned URLs added to code
- [ ] No raw audio files or databases committed
- [ ] Sensitive data properly redacted in logs/examples
- [ ] Environment variables used for configuration
- [ ] Security implications considered and addressed

## Code Quality

- [ ] Code follows project style guidelines
- [ ] Imports are organized correctly (stdlib, third-party, local)
- [ ] Used path helpers (MA_DATA_ROOT, etc.) instead of hardcoded paths
- [ ] Error messages are clear and helpful
- [ ] No commented-out code or debug statements
- [ ] Type hints added where appropriate

## Breaking Changes

<!-- If this PR includes breaking changes, describe them here -->

**Does this PR introduce breaking changes?**
- [ ] Yes (describe below and update CHANGELOG.md)
- [ ] No

<!-- If yes, describe:
- What breaks
- Migration path for users
- Deprecation warnings added (if applicable)
-->

## Screenshots/Recordings

<!-- If applicable, add screenshots or screen recordings to demonstrate UI changes -->

## Performance Impact

<!-- Does this change affect performance? -->

- [ ] No performance impact
- [ ] Performance improved (explain how)
- [ ] Performance may be affected (explain how and why it's acceptable)

## Deployment Notes

<!-- Any special notes for deployment or rollout? -->

- [ ] Requires data migration
- [ ] Requires environment variable changes
- [ ] Requires dependency updates
- [ ] No special deployment considerations

## Additional Context

<!-- Any other context, background, or information reviewers should know -->

## Reviewer Checklist

<!-- For reviewers - no need to fill this out as the PR author -->

- [ ] Code changes are minimal and focused
- [ ] Tests cover the changes adequately
- [ ] Documentation is clear and accurate
- [ ] No security concerns
- [ ] Performance is acceptable
- [ ] Error handling is appropriate

---

**Note to PR Author**: 
- Keep PRs focused and reasonably sized
- Ensure CI passes before requesting review
- Respond to review feedback promptly
- Update this description as the PR evolves
