# data/

This folder holds inputs and generated outputs for evaluation. Most of its
contents are **git-ignored** (see `.gitignore`): the BIRD databases, the
generated `cases_*.json`, and the `eval_*.json` results.

Expected layout after setup (see `../RUN_EVAL.md`):

```
data/
  dev_databases/                 # the 11 BIRD dev databases (git-ignored)
    california_schools/california_schools.sqlite
    financial/financial.sqlite
    ...
  cases_dinsql.json              # built from the DIN-SQL error set (git-ignored)
  cases_deepeye.json             # built from the DeepEye error set (git-ignored)
  eval_dinsql_llm_on.json        # evaluation results (git-ignored)
  ...
```

Build the case files and run the evaluation with the commands in
`../RUN_EVAL.md`.
