---
cadence: <daily | weekly | one-off>
reads: _shared/policy.yaml (<blocks>), _shared/rules.md, references/, <systems>
writes: <records and systems, on approval, or nothing>
next: <workflow that reads this output, or none>
---

# <Workflow name>

Template, not a skill. Never run it for a request. To add a workflow, follow the route-registration instructions in `AGENTS.md`.

<Purpose. One or two sentences naming the question this workflow answers. CRM is the record.>

## 1. Load policy

Per `rules#run_start`.

## 2. Collect

<Inputs. Exact queries and searches, saved to the explicit external run directory. Name helpers by `policy.tooling.scripts.<key>`.>

## 3. Propose

<Outputs. The report or numbered or lettered proposals in the thread.>

Then wait per `rules#approval`. <This workflow's approval grammar.>

## 4. Apply

Writes per `rules#write_protocol`. <Records and fields. For a read-only workflow, delete this step and cite `rules#read_only_skills`.>

## 5. Close

<Completion checks. Counts that must reconcile and any helper that must pass.> Name each skipped or needs-input item per `rules#approval`.

## Refuse

<Actions outside scope.>
