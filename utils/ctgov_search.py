import pandas as pd
from pytrials.client import ClinicalTrials
from utils.drug_search import read_pytrials_fields


def flatten(items, seqtypes=(list, tuple)):
	for i, x in enumerate(items):
		while i < len(items) and isinstance(items[i], seqtypes):
			items[i:i+1] = items[i]
	return items

def flatten_remove_duplicates(messy_list):
	clean_list = []
	for item in messy_list:
		# flatten list
		flattened_item = flatten(item)
		# remove duplicates
		clean_item = list(set(flattened_item))
		clean_list.append(clean_item)
	return clean_list

def clean_ctgov_df(ctgov_df):
	# drop rows with the same 'NCT Number' but combine the 'Search Term' fields and keep the first for all other fields
	agg_dict = {field: 'first' for field in ctgov_df.columns if field not in ['Drug Name', 'Search Term']}
	# combine 'Search Term' fields but don't have duplicates
	agg_dict['Drug Name'] = list
	agg_dict['Search Term'] = list
	ctgov_df = ctgov_df.groupby('NCT Number', as_index=False).agg(agg_dict)
	print('Number of rows in ctgov_df after dropping duplicates:', len(ctgov_df))
	# move 'Search Term' to the first column
	ctgov_df = ctgov_df[['Drug Name', 'Search Term'] + [col for col in ctgov_df.columns if col not in ['Drug Name', 'Search Term']]]
	# for each row, if there are duplicates in 'Drug Name' and 'Search Term' lists, keep only the first and flatten the lists
	drug_names = ctgov_df['Drug Name'].values
	search_terms = ctgov_df['Search Term'].values
	ctgov_df['Drug Name'] = flatten_remove_duplicates(drug_names)
	ctgov_df['Search Term'] = flatten_remove_duplicates(search_terms)
	return ctgov_df

def parse_ctgov_synonyms(pubchem_df, ctgov_df, ct, drug_name, ct_fields):
	if drug_name not in pubchem_df['drug_name'].values:
		# print(f'{drug_name} not found in pubchem_df...')
		return None
	synonyms = pubchem_df[pubchem_df['drug_name'] == drug_name].compound_synonyms.values[0]
	if synonyms is None:
		# print(f'No synonyms found for {drug_name}...')
		return ctgov_df
	print(f'Number of synonyms for {drug_name}: {len(synonyms)}')
	synonyms = [synonym.lower() for synonym in synonyms]
	synonyms = [synonym.replace(' ', '+') for synonym in synonyms]
	ct_gov_count = 0
	for synonym in synonyms:
		try:
			# get the NCTId, Condition and Brief title fields from 1000 studies related to Coronavirus and Covid, in csv format.
			ct_output = ct.get_study_fields(
				search_expr=synonym,
				fields=ct_fields,
				max_studies=1000,
				fmt="csv",
			)
			if ct_output is None:
				# print(f'    No clinical trials found for {synonym}...')
				continue
			# print(f'    Number of clinical trials found for {synonym}: {len(ct_output)}')
			row_header = ['Drug Name', 'Search Term'] + ct_output[0]
			# add all rows to the dataframe
			for row in ct_output[1:]:
				ctgov_df = pd.concat([ctgov_df, pd.DataFrame([drug_name, synonym] + row, index=row_header).T], ignore_index=True)
				ct_gov_count += 1
		except:
			# print(f'  Error parsing {drug_name} - {synonym}...')
			continue
	print(f'    CTs found: {ct_gov_count}')
	return ctgov_df

def get_ctgov_synonyms(pubchem_df):
	ct_fields = read_pytrials_fields()
	ct = ClinicalTrials()
	# create a dataframe
	ctgov_df = pd.DataFrame(columns=['Drug Name', 'Search Term'] + list(ct_fields))
	for d_index, drug in enumerate(pubchem_df['drug_name'].values):
		ctgov_df = parse_ctgov_synonyms(pubchem_df, ctgov_df, ct, drug, ct_fields)
	# clean the dataframe
	# ctgov_df = clean_ctgov_df(ctgov_df)
	return ctgov_df