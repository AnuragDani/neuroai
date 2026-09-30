# Lane C compact cohort table

Branch `gnhf/read-users-anuragdan-ea5475` @ `808fa734`. Metadata from saved records only.

## Internal development cohort (current NN-v2)

| Field | Value | Source |
|---|---|---|
| Study | Lattke et al. fetal cortex multiome (GSE305146 / CELLxGENE `f16c25da-…`) | `PAIRED_DS_MULTIOME_DATASET_OPTIONS.md`; sampling H5AD path |
| H5AD sha256 | `08d6eff265db6e6a2e1c4a259153588f3dba3c51f5f754736dc63c28795fcdbb` | `sampling_cap1000_seed22.json` |
| Donors | 30 (15 DS + 15 CON) | sampling `n_donors`; spectrum support counts |
| Cells available / selected | 248998 / 30000 (cap 1000/donor, seed 22) | sampling `primary` |
| Libraries | 37 unique | sampling `library_available` keys |
| Age span | PCW 10–20 (uneven: PCW12/13=6; PCW10/14/15=1) | donor IDs in sampling |
| Strata | `author_cell_type` × `library` | sampling `strata` |
| Spectrum-eligible types | 9 (IPC, IPC_prol, NEU_CALB2/CUX2/RORB/SST/TLE4, RG, RG_prol) | `spectrum.json` |
| Spectrum-excluded (support floor) | AST, MIC, NEU_RELN, NEU_low, OPC, VASC | `spectrum.json` |
| Primary CA−TC | 0.0267, CI [−0.0250, 0.0768], margin 0.07 → `B_NULL` | `ladder_verification.json` |
| Dosage control | chr21_dosage BA/AUROC = 1.0; N11 `DOSAGE_DOMINATED` | verifier; `chr21_excluded.json` |
| Spectrum call | `SPECTRUM_NULL` | `spectrum.json` |
| Pairing faithfulness | `CA_PAIRING_UNUSED`; PC `N/A` | `faithfulness.json` |
| Biological A_ADVANTAGE power | `POWER_UNESTABLISHED` | X4 `min_detectable_delta=null`; FEASIBILITY P3 |

## External / related candidates (not acquired by this lane)

| Candidate | DS/CON | Paired multiome | Lane C status |
|---|---|---|---|
| Same GSE305146 / CELLxGENE | 15/15 | Yes | **Internal only** — not independent external |
| Vuong NeMO `col-umstjg0` | 13/13 metadata | Yes (processed) | **Reserved external; BLOCKED** — QC gap 3731 nuclei, specimen independence unresolved, feature contract pending (T13) |
| GSE280175 | 5/5 | RNA only | RNA replication track; not multimodal CA validation |
| HF Zarr / GSE204684 | N/A | No DS paired design | Engineering / pretrain only |

## Decision (one line)

**Bounded internal paper: GO. Independent paired validation: NO-GO until NeMO preflight clears. Power: POWER_UNESTABLISHED — no donor-n target.**
