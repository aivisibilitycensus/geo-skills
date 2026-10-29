# Methods

## Rates

Each rate is a count of answers divided by the number of answers in the group. Every answer counts once per brand. Answers with no citations stay in the denominator for the cited rate.

## Wilson score interval (95%)

For k answers out of n, with p = k/n and z = 1.96:

```
centre = (p + z^2 / 2n) / (1 + z^2 / n)
half   = z * sqrt(p(1 - p)/n + z^2 / 4n^2) / (1 + z^2 / n)
interval = centre +/- half, clipped to [0, 1]
```

It is used instead of p +/- 1.96 * sqrt(p(1 - p)/n) because that formula gives a zero-width interval at 0% or 100% and can go below 0 or above 1 at small n. Reference: Wilson, E. B. (1927), "Probable inference, the law of succession, and statistical inference", Journal of the American Statistical Association 22(158).

## Period comparison

Pooled two-proportion z-test:

```
pooled = (k1 + k2) / (n1 + n2)
se = sqrt(pooled (1 - pooled) (1/n1 + 1/n2))
z = (k2/n2 - k1/n1) / se
p = two-sided normal tail of |z|
```

The reading is "change outside noise" only when p < 0.05 and the two Wilson intervals do not overlap. Non-overlap is a stricter bar than the test alone, which is deliberate: the test assumes independent answers, and logged runs are not independent (the same question asked again tends to get a similar answer). Requiring both keeps the report from calling routine wobble a trend.

## Thresholds

- **Cells under 3 runs** are flagged. With 1 or 2 runs, the only possible rates are 0%, 50% or 100%.
- **Aggregates under 30 answers** are flagged as too thin and not tested. At n = 30 a 50% rate still has an interval of about 33% to 67%. The cutoff is a rule of thumb, not a statistical law.

## What the numbers cannot carry

- Clustering: runs of one question are correlated, so the effective sample size is smaller than the answer count.
- Multiple comparisons: the comparison table tests many rows. Expect about one in twenty to cross p < 0.05 by chance when nothing changed.
- Confounds: engine model updates, retrieval changes and tracker changes all land between periods and cannot be separated from your own work.
