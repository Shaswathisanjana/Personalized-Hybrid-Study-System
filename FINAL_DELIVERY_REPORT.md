# PHSS local delivery

Prepared on 20 October 2026 following completion of milestones 1–8. This delivery closes local startup, dependency documentation and backup tooling gaps without changing agent behavior or overwriting existing work. It does not claim a public deployment or measured educational effectiveness.

## Delivery additions

| File | Change |
| --- | --- |
| `run_phss.py` | New foreground local launcher, dependency-only check, explicit loopback binding, configurable port and disabled usage telemetry |
| `requirements.txt` | New observed direct dependency pins; no packages installed and no transitive lock claimed |
| `tools/local_environment.py` | New existing-package fallback and actual import validation |
| `tools/backup_student_data.py` | New read-only SQLite source backup with exclusive destination creation and integrity validation |
| `tools/test_local_delivery.py` | Five new checks: committed WAL backup, existing-target preservation, same-path rejection, missing-source rejection and local-only launcher arguments |
| `tools/smoke_startup.py` | New actual loopback server health check with cleanup of its own process |
| `README.md` | Updated startup and backup commands |
| `docs/SETUP.md` | Updated launcher, requirements scope, backup/restore and verification instructions |
| `docs/LIMITATIONS.md` | Updated current delivery status and remaining external validation |
| `FINAL_DELIVERY_REPORT.md` | This report |

Existing documents were backed up under `.milestone_backups/final_delivery_20261020/`. No existing application modules or historical tests were edited in this delivery pass. The two protected test hashes still match the values recorded in MILESTONE_8_REPORT.md.

## Commands

```powershell
python -B -m unittest tools.test_local_delivery tools.test_evaluate_offline
python -B run_phss.py --check
python -B tools/smoke_startup.py
python -B tools/evaluate_offline.py --only test_student_journey_streamlit
python -B tools/evaluate_offline.py
git diff --check -- README.md docs/SETUP.md docs/LIMITATIONS.md
```

The infrastructure command passed all **12 tests**: five local delivery tests and seven evaluation-runner tests. The dependency check imported required packages. The actual Streamlit subprocess returned HTTP 200 with `ok` from its loopback health endpoint and was stopped by the checker. This does not execute or validate a browser session. The selected Streamlit journey run passed **5 tests**, with artifacts at `data/evaluation/20261020T081313076021Z/`.

The final full curated run passed **56/56 cases: 120 application unittest executions and 41 standalone scripts**, with zero failures, errors, skips, missing cases or timeouts. Results and logs are in `data/evaluation/20261020T081407063412Z/`. The separate 12 infrastructure tests are additional; the selected five-test Streamlit run is not added again to the 120 application count. Other historical root tests remain explicitly not run by the curated suite.

All **304 Python files** parsed successfully, documentation links resolved and the scoped whitespace check passed. Earlier unrelated whitespace findings were preserved.

## Start and protect local data

### Follow-up backup/restore verification

An additional integration check now backs up a real PHSS SQLite snapshot populated with explicitly synthetic assessed activity. It reopens the backup through `SQLiteStudentStore`, restores the shared cognitive model, and verifies exact snapshot equality, genuine cross-agent conflict retention, concept aliases, saved code drafts, learning goals and two-profile separation. Replaying the saved evidence and quiz completion does not increase attempts or completion counts, and the original database remains unchanged.

The follow-up command `python -B -m unittest tools.test_local_delivery tools.test_evaluate_offline` passed **13/13 tests**: six local delivery checks and seven runner checks. This supersedes the earlier 12-test tooling count; it is not 13 additional application tests. No production behavior changed, so the unrelated full application suite was not repeated for this test-only addition. Temporary databases were used throughout; existing student data, environment and provider credentials were untouched.

```powershell
python -B run_phss.py --check
python -B run_phss.py
```

Use the URL/profile controls deliberately and retain the same student identifier across refreshes. Keep this local instance for trusted users and trusted code. Run `python -B tools/backup_student_data.py` when you want a real student-data backup. Automated verification exercised disposable databases only; it did not copy, replace or clear real student records.

## What remains outside verified completion

- **Clean install:** direct versions are documented, but downloading/installing into a separate environment still requires approval under the project instructions. The existing environment was preserved.
- **Live providers:** real Gemini/retrieval calls need explicit cost authorization and credentials. They have not been represented as passing offline checks.
- **Manual browser review:** follow `docs/DEMO_AND_VIVA.md` for refresh, drafts, research handoff and profile isolation. AppTest and server health are automated evidence only.
- **Public hosting:** authenticated authorization and isolated untrusted-code execution remain prerequisites. Loopback binding is a local access choice, not authentication or a security sandbox.
- **Educational research:** measured improvement requires a real-student protocol, consent and analysis; source-grounded abstract assistance is not a systematic literature review.

No environment files or secrets were edited or printed. No package installation, real-provider call, commit, staging or push was performed in this delivery pass. Completion means the implemented local prototype and its reproducible software evaluation path, with the above external work explicitly outstanding.
