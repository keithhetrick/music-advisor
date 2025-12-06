# Templates Namespace

Templates are grouped by module to avoid collisions and keep PRs clean. They feed GPT prompt/output blocks; keep names stable so references in specs/recipes don’t break.

- `Templates/era/*`
- `Templates/listener/*`
- `Templates/emotion/*`
- `Templates/biome/*`
- `Templates/endurance/*`
- `Templates/narrative/*` (optional)

Naming:

- Use `output_*.txt` for primary prints
- Keep copy human-readable (these strings may ship to Promptsmith)

If unsure where a template is consumed, search for its filename in `Specs/` and `Recipes/`.
