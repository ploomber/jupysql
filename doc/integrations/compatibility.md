# Compatibility

## DuckDB

**Full compatibility**

- Running queries with `%%sql` ✅
- CTEs with `%%sql --save NAME` ✅
- Plotting with `%%sqlplot boxplot` ✅
- Plotting with `%%sqlplot histogram` ✅
- Plotting with `ggplot` API ✅
- Profiling tables with `%sqlcmd profile` ✅
- Listing tables with `%sqlcmd tables` ✅
- Listing columns with `%sqlcmd columns` ✅
- Parametrized SQL queries via `{{parameter}}` ✅
- Interactive SQL queries via `--interact` ✅

## PostgreSQL

**Almost full compatibility**

- Running queries with `%%sql` ✅
- CTEs with `%%sql --save NAME` ✅
- Plotting with `%%sqlplot boxplot` ✅
- Plotting with `%%sqlplot histogram` ✅
- Plotting with `ggplot` API ❓
- Profiling tables with `%sqlcmd profile` ✅
- Listing tables with `%sqlcmd tables` ✅
- Listing columns with `%sqlcmd columns` ✅
- Parametrized SQL queries via `{{parameter}}` ✅
- Interactive SQL queries via `--interact` ✅