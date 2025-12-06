BUILDER_OUT=builder/export/MusicAdvisor_GPT_v1.1.1.zip

builder-zip:
	@mkdir -p builder/export
	@zip -r $(BUILDER_OUT) \
		builder/INSTRUCTIONS_v0.3.5.md \
		builder/VALIDATION_v0.3.5.md \
		builder/PROMPT_SNIPPETS/ \
		contracts/audiotools_payload_v0.3.5.json \
		contracts/audiotools_payload_v0.3.5.yaml \
		contracts/examples/ \
		docs/payload_contracts.md
	@echo "Wrote $(BUILDER_OUT)"
