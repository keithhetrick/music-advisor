---
name: Bug report
about: Report a problem with Music Advisor
title: "[Bug] "
labels: bug
assignees: ""
---

## Bug Description

<!-- Provide a clear and concise description of what the bug is -->

## Steps to Reproduce

<!-- Detailed steps to reproduce the behavior -->

1. 
2. 
3. 

## Expected Behavior

<!-- What you expected to happen -->

## Actual Behavior

<!-- What actually happened -->

## Logs and Error Messages

<!-- 
Paste relevant logs here. 
Please redact any sensitive data (file paths are OK).
You can find logs in the `logs/` directory if enabled.
-->

```
(paste logs here)
```

## Environment

- **OS**: <!-- e.g., macOS 13.5, Ubuntu 22.04, Windows 11 via WSL2 -->
- **Python Version**: <!-- e.g., 3.11.4 -->
- **Music Advisor Version**: <!-- e.g., v0.3.0 or commit SHA -->
- **Install Method**: <!-- e.g., make bootstrap-locked, manual pip install -->
- **Component Affected**: <!-- e.g., audio_engine, host, CLI, macOS app -->

## Configuration

- **MA_DATA_ROOT Override?**: <!-- Yes/No -->
- **Virtual Environment**: <!-- Active? -->
- **Sparse Checkout**: <!-- Used? If yes, which paths? -->

## Command(s) Run

<!-- The exact command(s) that triggered the bug -->

```bash
# Example:
./automator.sh /path/to/song.wav
```

## Additional Context

<!-- Any other context about the problem, such as:
- Does it happen consistently or intermittently?
- Have you tried any workarounds?
- Related issues or discussions
- Screenshots or screen recordings (if applicable)
-->

## Checklist

- [ ] I have searched existing issues to ensure this is not a duplicate
- [ ] I have included all relevant information above
- [ ] I have redacted any sensitive information from logs/paths
- [ ] I am using a supported Python version (3.9+)
