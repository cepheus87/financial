# financial scripts


## Record entries:

- [run_record_entries.py](entries_recording/run_record_entries.py) - script to print all needed values based on csv 
  files with columns: `data,account,type,name,units,price_in_currency,currency,full_cost,comments` 
- [entries_by_file.py](entries_recording/entries_by_file.py) - script to print or create csv file of "ready to copy" 
  entries
  - `--portfolio-path` it needs path to starting portfolio in csv format (adding entries only for those entities which 
    already exist)
  - `--input-path` file to csv file with columns: `data,account,type,name,units,price_in_currency,currency,full_cost,comments`
  - `--output-mode` (print or file)
  - `--output-path` path to output csv file

## Taxes:

- [calculate_income.py](taxes/calculate_income.py) - script to calculate income and costs based on csv 
  file from broker statements (at the moment only ibkr's statement is supported)
  
```commandline
usage: calculate_income.py [-h] --statement-paths STATEMENT_PATHS
                           [STATEMENT_PATHS ...]
                           [--entity-symbol ENTITY_SYMBOL] --tax-year TAX_YEAR

options:
  -h, --help            show this help message and exit
  --statement-paths STATEMENT_PATHS [STATEMENT_PATHS ...]
                        Paths to statement files (csv)
  --entity-symbol ENTITY_SYMBOL
                        Entity symbol to calculate income and costs for
                        (default: all entities)
  --tax-year TAX_YEAR   Tax year to calculate income and costs for
```

 The script uses the FIFO order of transactions to calculate income and costs for each entity.

 [reckoning_rules.py](taxes/reckoning_rules.py) - contain rules of selecting proper day of fx conversion of trades 
 with respect to settlement date. It also takes into account working days of stock exchanges (LSE and XETRA) and 
 possible holidays of these stocks and holidays in Poland (for average fx conversion 
 rate). At the moment, it supports only XETRA and LSE settlement rules (T+2).
 To calculate fx conversion date, first working date is taken after settlement date (if it is not working date). Then 
 the latest working day (in Poland) before settlement date is chosen to calculate average fx conversion rate for given day.
 
**NOTE Stock exchange is selected based on the trade currency (if it is EUR - XETRA, if it is GBP or USD - LSE).**

 [trades.py](taxes/trades.py) - contain functions to parse trades from csv files (at the moment only ibkr's 
 statement is supported) and convert them to internal format used for income and cost calculation. It assumes that 
 buy and sell transactions (amount and commission) have positive values.


#### TODO List:
 * handle downloading fx_data for current year if already cached
 * handle ibkr hours of trades (12 hours clock)
 * split flow for many brokers statements (at the moment only ibkr is supported)

 
 