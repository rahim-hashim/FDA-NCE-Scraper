# FDA NCE Scraper

### Arguments

To generate a report, run `company_report.py` with the following arguments:


> ```--search_file``` : read the `company_search` file to find assigned values for the search
> ```--company_name```: if search_file argument is not assigned, specify the name of the company to search (i.e. Amgen)
> ```--drug_name```: the name of the drug to search (i.e. Aimovig)
> ```--active_ingredient```: the name of the active ingredient to search (i.e. erenumab)
> ```--target```: the target to search (i.e. CGRPR)
> ```--indication```: the indication to search (i.e. migraine)
> ```--mechanism```: the mechanism of action (i.e. calcitonin)

##### Example 1: Search File

```bash
python3 company report.py --search_file
```

##### Example 2: Specify Arguments

```bash
python3 company report.py --company_name Amgen --drug_name aimovig --target CGRPR --indication migraine --mechanism calcitonin
```
