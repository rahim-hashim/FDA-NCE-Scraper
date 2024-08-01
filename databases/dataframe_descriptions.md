# Database Descriptions

**Last Updated:** 7/24/2024

***


## [fda_drug_df](fda_drug_df.pkl)
> * **description:** A database containing all novel drugs approved by the FDA from 2012-2024.
> * **source:** https://www.fda.gov/drugs/development-approval-process-drugs/novel-drug-approvals-fda
> * **shape:** (542, 7)
> * **fields:**
> 	* nce_id
> 	* drug_name
> 	* active_ingredient
> 	* approval_date
> 	* approved_use
> 	* drug_link
> 	* press_release

## [fda_approved_df](fda_approved_df.pkl)
> * **description:** A database containing all drugs from Drugs@FDA approved for human use in the United States.
> * **source:** https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm
> * **shape:** (28291, 7)
> * **fields:**
> 	* drug_name
> 	* active_ingredient
> 	* dosage_form
> 	* drug_link
> 	* application_type
> 	* application_num
> 	* sponsor

## [fda_api_df](fda_api_df.pkl)
> * **description:** A database containing all drug and label information captured using the open.fda API calls for all drugs in the `fda_drug_df` database.
> * **source:** https://open.fda.gov/apis/drug/.
> * **shape:** (541, 88)
> * **fields:**
>    * nce_id
>    * year
>    * year_approval_count
>    * drug_name
>    * active_ingredient
>    * approval_date
>    * approved_use
>    * drug_link
>    * press_release
>    * drug_trials_snapshot
>    * year_month
>    * count
>    * month
>    * submission_type
>    * submission_number
>    * submission_status
>    * submission_status_date
>    * review_priority
>    * submission_class_code
>    * submission_class_code_description
>    * application_docs
>    * application_number
>    * sponsor_name
>    * brand_name
>    * generic_name
>    * manufacturer_name
>    * product_ndc
>    * product_type
>    * route
>    * substance_name
>    * rxcui
>    * spl_id
>    * spl_set_id
>    * package_ndc
>    * nui
>    * pharm_class_epc
>    * pharm_class_cs
>    * unii
>    * product_number
>    * reference_drug
>    * active_ingredients
>    * reference_standard
>    * dosage_form
>    * marketing_status
>    * spl_product_data_elements
>    * indications_and_usage

## [fda_biologics_df](fda_biologics_df.pkl)
> * **description:** A database of approved biologics by the FDA from 1996-2024.
> * **source:** https://www.fda.gov/vaccines-blood-biologics/development-approval-process-cber/biological-approvals-year
> * **shape:** (469, 11)
> * **fields:**
>    * biologics_id
>    * year
>    * drug_name
>    * drug_link
>    * drug_info
>    * indication
>    * stn
>    * manufacturer
>    * manufacturer_info
>    * license_num
>    * approval_date
  
## [pubchem_df](pubchem_df.pkl)
> * **description:** For each drug included in the `fda_drugs_df`, this dataframe captures all synonyms found from the PubChem database.
> * **source:** https://pubchem.ncbi.nlm.nih.gov/
> * **shape:** (541, 8)
> * **fields:**
> 	 * nce_id
>    * drug_name
>    * active_ingredient
>    * cid
>    * sid
>    * compound_synonyms
>    * substance_synonyms
>    * description
>    * pubmed_ids

## [ctgov_df](ctgov_df.pkl)
> * **description:** For each synonym from `pubchem_df` for drug included in the `fda_drugs_df`, this dataframe captures all clinical trials with general search term including the synonym.
> * **source:** https://clinicaltrials.gov/
> * **shape:** (46051, 32)
> * **fields:**
> 	* Drug Name
> 	* Search Term
> 	* NCT Number
> 	* Study Title
> 	* Study URL
> 	* Acronym
> 	* Study Status
> 	* Brief Summary
> 	* Study Results
> 	* Conditions
> 	* Interventions
> 	* Primary Outcome Measures
> 	* Secondary Outcome Measures
> 	* Other Outcome Measures
> 	* Sponsor
> 	* Collaborators
> 	* Sex
> 	* Age
> 	* Phases
> 	* Enrollment
> 	* Funder Type
> 	* Study Type
> 	* Study Design
> 	* Other IDs
> 	* Start Date
> 	* Primary Completion Date
> 	* Completion Date
> 	* First Posted
> 	* Results First Posted
> 	* Last Update Posted
> 	* Locations
> 	* Study Documents
  
## [dailymed_df](dailymed_df.pkl)
> * **description:** This database contains labeling information, submitted to the Food and Drug Administration (FDA) by companies for FDA-approved products.
> * **source:** https://dailymed.nlm.nih.gov/dailymed/browse-drug-classes.cfm
> * **shape:** (259393, 6)
> * **fields:**
> 	*  drug_name
> 	*  drug_class
> 	*  class_type
> 	*  drug_link
> 	*  ndc_code
> 	*  packager

## [ddc_drug_classes](ddc_drug_classes.pkl)
> * **description:** This database contains all drugs associated with a drug class submitted to the www.drugs.com database.
> * **source:** https://www.drugs.com/drug-classes.html
> * **shape:** (8093, 20)
> * **fields:**
> 	* drug_name
> 	* generic_name
> 	* drug_link
> 	* drug_class
> 	* drug_class_description
> 	* drug_class_url
> 	* Generic name
> 	* Brand names
> 	* Dosage form
> 	* Drug class
> 	* uses
> 	* side-effects
> 	* warnings
> 	* before_taking
> 	* dosage
> 	* avoid
> 	* interactions
> 	* storage
> 	* ingredients
> 	* manufacturer


## [ddc_drugs](ddc_drugs.pkl)
> * **description:** This database contains all drugs listed by alphabet submitted to the www.drugs.com database.
> * **source:** https://www.drugs.com/
> * **shape:** (1239, 13)
> * **fields:**
> 	* drug_name
> 	* drug_link
> 	* Generic name
> 	* Brand names
> 	* Dosage form
> 	* Drug class
> 	* uses
> 	* side-effects
> 	* warnings
> 	* before_taking
> 	* dosage
> 	* avoid
> 	* interactions