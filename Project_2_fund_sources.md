# Project 2 fund universe and price sources

## Selected funds

| Ticker | Fund name | Portfolio role |
| --- | --- | --- |
| SGOV | iShares 0-3 Month Treasury Bond ETF | Cash and reserve |
| IEI | iShares 3-7 Year Treasury Bond ETF | Government bonds |
| SPIB | SPDR Portfolio Intermediate Term Corporate Bond ETF | Investment-grade fixed income |
| IVV | iShares Core S&P 500 ETF | Broad U.S. equity |

## Price-data record

The file `prices.csv` contains monthly **Adjusted Close** prices, with the date first and observations ordered oldest to newest. The source is Yahoo Finance Historical Data, Monthly frequency; the adjusted-close field incorporates distributions and splits.

| Ticker | Source | Download date |
| --- | --- | --- |
| SGOV | [Yahoo Finance historical data](https://finance.yahoo.com/quote/SGOV/history/) | 2026-10-22 |
| IEI | [Yahoo Finance historical data](https://finance.yahoo.com/quote/IEI/history/) | 2026-10-22 |
| SPIB | [Yahoo Finance historical data](https://finance.yahoo.com/quote/SPIB/history/) | 2026-10-22 |
| IVV | [Yahoo Finance historical data](https://finance.yahoo.com/quote/IVV/history/) | 2026-10-22 |

The downloaded window is October 2021 through September 2026: 60 completed monthly observations. Historical average returns calculated from these prices are estimates, not forecasts.

## Portfolio-engine flow

```mermaid
flowchart TD
    A[prices.csv:<br/>date first, oldest first,<br/>one price column per ticker] --> B[Read and validate prices]
    B --> C[Calculate monthly returns]
    C --> D{Use all months<br/>or last 36?}
    D --> E[Estimate annualized return:<br/>monthly mean × 12]
    D --> F[Estimate annualized volatility:<br/>monthly standard deviation × √12]
    D --> G[Calculate correlation table]
    E --> H[Build covariance matrix:<br/>correlation × vol_i × vol_j]
    F --> H
    G --> H
    H --> I[Generate every long-only<br/>5-point weight mix]
    I --> J[Calculate each mix's return,<br/>volatility, and reserve weight]
    J --> K{Return ≥ objective<br/>and reserve ≥ minimum?}
    K -->|Yes| L[Keep feasible mix]
    K -->|No| M[Discard mix]
    L --> N[Select feasible mix with<br/>lowest volatility]
    M --> N
    N --> O{Any feasible mix?}
    O -->|Yes| P[Show lowest-risk mix]
    O -->|No| Q[Show no mix meets the objective]
```
