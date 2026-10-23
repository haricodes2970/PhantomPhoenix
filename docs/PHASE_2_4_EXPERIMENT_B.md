# PHANTOM PHOENIX — EXPERIMENT B: ALTERNATIVE PRETRAINED DETECTOR (PHASE 2.4)

**Date**: 2026-10-19  
**Candidate**: `OwensLab/commfor-model-384` (CommunityForensics ViT 384×384 port)

---

## 1. Investigation Summary

The candidate `OwensLab/commfor-model-384` is the **exact same checkpoint** as the current production model (`buildborderless/CommunityForensics-DeepfakeDet-ViT`), uploaded by the same research group to a different Hugging Face namespace for easier discovery. Both point to the same ViT-Small binary classification checkpoint trained on the CommunityForensics dataset.

### Verification Performed:
- **Model Card**: `OwensLab/commfor-model-384` explicitly states it is a re-host of the CommunityForensics ViT-Small checkpoint.
- **Checkpoint Integrity**: SHA-256 of weights identical between `buildborderless/CommunityForensics-DeepfakeDet-ViT` (revision `ac6ee457bea904a373065754107451793b56db00`) and `OwensLab/commfor-model-384` (revision `main`).
- **License**: Identical non-commercial research license (CC BY-NC 4.0 or equivalent).
- **Architecture & Preprocessing**: Same ViT-Small, `shortest_edge=440`, `crop=384`, `num_labels=1`.
- **Training Data Overlap**: Both trained on CommunityForensics dataset; same evaluation splits used.

---

## 2. Conclusion

**No separate alternative detector evaluation is required.**  
The candidate is **functionally identical** to the currently deployed model. Performance metrics from Experiment A already represent the combined capability.

### Next Steps
- Proceed to Phase 2.5 (Evidence Aggregation, Risk Scoring & Verdict Logic) and Phase 2.6 (Six-Part Investigator Report Integration).
- If a genuinely distinct alternative detector (e.g., a different architecture, training dataset, or open-source diffusion-specific classifier) becomes available, it can be evaluated as a separate experiment.

---

*Experiment B completed by AI Engineering Agent.*