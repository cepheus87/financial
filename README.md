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

 TODO:
* create CLI for tax scripts
* ADD DESCRIPTION OF TAXES SCRIPTS



#### TODO List:
 * check days of reckoning for tax purposes

 * handle using not all units from buy entry during selling
 * handle downloading fx_data for current year if already cached
 * handle ibkr hours of trades (12 hours clock)
 * add tests to ibkr trades format parsing
 * add joining statements from different files (e.g. few years)
