import pandas as pd
from collections import defaultdict
from utils.webpage_scraping import test_connection
from utils.pickle_dataframes import pickle_dataframe

def parse_fda_api_dict(api_results, key, fda_api_dict, drug):
	if type(api_results[0][key]) == list:
		if type(api_results[0][key][0]) == dict:
			for app_key in api_results[0][key][0].keys():
				fda_api_dict[drug][app_key] = api_results[0][key][0][app_key]
	elif type(api_results[0][key]) == str:
		fda_api_dict[drug][key] = api_results[0][key]

def get_fda_api_data(nce_id, drug, api_results, fda_api_dict=None):
	if fda_api_dict == None:
		fda_api_dict = defaultdict(lambda: defaultdict(list))
	for key in api_results[0].keys():
		if type(api_results[0][key]) == list:
			if type(api_results[0][key][0]) == dict:
				for app_key in api_results[0][key][0].keys():
					fda_api_dict[nce_id][app_key] = api_results[0][key][0][app_key]
			else:
				fda_api_dict[nce_id][key] = api_results[0][key]
		elif type(api_results[0][key]) == str:
			fda_api_dict[nce_id][key] = api_results[0][key]
		elif type(api_results[0][key]) == dict:
			for app_key in api_results[0][key].keys():
				fda_api_dict[nce_id][app_key] = api_results[0][key][app_key]
		else:
			print(api_results[0][key])
			break
	return fda_api_dict

# convert fda_api_dict to a dataframe
def fda_api_dict_to_df(fda_api_dict, save_df=False):
	if len(fda_api_dict) == 0:
		print('WARNING: fda_api_dict is empty...')
		return None
	columns = list(fda_api_dict[list(fda_api_dict.keys())[0]].keys())
	fda_api_df = pd.DataFrame(columns=columns)
	fda_api_drug_count = 0
	nce_ids = list(fda_api_dict.keys())
	for n_index, nce_id in enumerate(nce_ids):
		if fda_api_dict[nce_id]['brand_name'] == None:
			data = [None for i in range(len(columns)-1)]
		else:
			data = [fda_api_dict[n_index][key] for key in columns]
			fda_api_drug_count += 1
		if len(data) != len(columns):
			print(f'Error: {nce_id} - {len(data)} != {len(columns)}')
		fda_api_df = pd.concat([fda_api_df, pd.DataFrame([data], columns=columns)], ignore_index=True)
	print(f'Number of drugs in fda_api_df: {fda_api_drug_count}')
	if save_df:
		pickle_dataframe(fda_api_df, 'databases/fda_api_df.pkl')
	return fda_api_df

def scrape_fda_data(fda_drug_df):
	fda_api_key = 'I1t0zDXLq61NXyrCsPdeO2mpRxcgyO5h5an4IFuA'
	fda_api_dict = defaultdict(lambda: defaultdict(list))
	for d_index, nce_id in enumerate(fda_drug_df['nce_id'].values):
		# all all the fields to the fda_api_dict
		fda_drug_row = fda_drug_df[fda_drug_df['nce_id'] == nce_id]
		drug = fda_drug_row['drug_name'].iloc[0]
		for col in fda_drug_row.columns:
			fda_api_dict[nce_id][col] = fda_drug_row[col].iloc[0]
		print(f'Getting FDA API data for {drug}...({d_index+1}/{len(fda_drug_df)})')
		open_fda_urls = [
			f'https://api.fda.gov/drug/drugsfda.json?api_key={fda_api_key}&search={drug}',
			f'https://api.fda.gov/drug/label.json?api_key={fda_api_key}&search={drug}'
		]
		fda_drug_page_found = False
		for url in open_fda_urls:
			response = test_connection(url)
			api_response = response.json()
			if 'results' in api_response.keys():
				api_results = api_response['results']
				fda_api_dict = get_fda_api_data(nce_id, drug, api_results, fda_api_dict)
				print(f'  Data found: {url}')
				fda_drug_page_found = True
			else:
				print(f'  No results: {drug}...')
		if fda_drug_page_found == False:
			print(f'  Missing: {drug}...')
	return fda_api_dict