
## Evaluation

The analyzer is evaluated on real commercial contracts from
[CUAD](https://www.atticusprojectai.org/cuad) (CC BY 4.0, The Atticus Project),
labelled by lawyers. Contracts are limited to ~20k characters and must contain
at least 3 of the 4 categories we detect: auto-renewal, termination,
liability cap, liquidated damages (penalty).

Run it:

    cd backend
    python import_cuad.py path/to/data.zip
    python run_eval.py

### Metrics

- **Recall**: share of lawyer-labelled risky clauses the analyzer found.
- **False alarms**: standard clauses (e.g. governing law) wrongly flagged as risky.

### Results

| Version | Change | Recall | False alarms |
|---------|--------|--------|--------------|
| baseline | initial prompt and chunking | TODO | TODO |

Evaluation notes:

- Small evaluation set, so results are indicative, not statistically strong.
- Payment terms have no CUAD equivalent, so they are not part of the evaluation.
