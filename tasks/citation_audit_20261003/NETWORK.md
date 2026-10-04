# Citation-audit resource accounting

Separately authorized stage; the old submission-prep ≈25/24 ledger is not reset or re-certified.

| Measurement | Used | Limit / interpretation |
|---|---:|---|
| Initial/fallback source acquisitions plus discovery queries | 28 | 32 logical acquisition attempts |
| Subsequent cached-page navigation operations | 28 | Recorded separately; not represented as new source acquisitions |
| All explicitly initiated acquisition/navigation operations | 56 | 56 operations; **not** a claim of ≤32 total web operations or HTTP requests |
| Returned response representations, including exact PubMed XML body | 280195 bytes | 32 MiB retained-response ceiling |
| Underlying HTTP requests / redirects / cache hits | Unknown | Web tool does not expose these counts |
| Actual downloaded documentation bytes | Unknown for web tool | PubMed XML measured exactly 48,236 bytes; web representation size is not downloaded-byte accounting |

[NETWORK.json](NETWORK.json) records each batch. The acquisition-vs-cached-navigation distinction is an operational accounting clarification, not a reset. The plan’s 32-attempt cap is assessed only for initial/fallback acquisitions; compliance with a strict 32-total-operation or physical HTTP cap is **not established**. Readiness below certifies scientific/source checks, not request-cap compliance. No additional acquisition is needed.

Source access limits: initial Nature Squair and Signac endpoints failed; Cell Hao endpoint failed. PMC alternatives for Squair/Hao served CAPTCHA (not bypassed); Signac PMC methods worked. Hao PubMed HTML was empty, an author PDF was rejected by the tool as oversized, and ScienceDirect served 403. The official PubMed XML abstract then supplied the general WNN claim. The XML response was capped at 1,000,000 bytes before parsing. No data, fragments, new matrices or models were downloaded. Primary HTML/abstract evidence was sufficient for retained claims; no full-method reproduction certification is made.
