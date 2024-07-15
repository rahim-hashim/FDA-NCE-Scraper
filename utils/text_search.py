import os
import pandas as pd

def find_drug(df, field, list_values, class_type=None):
	print('Number of rows in the dataframe:', len(df))
	if field not in df.columns:
		print(f'{field} not found in the dataframe...')
		return None
	# drop NaN values for the field
	df = df.dropna(subset=[field])
	print(f'Number of rows after dropping NaN values in {field}: {len(df)}')
	if field == 'ndc_code':
		indices = []
		for i, code in enumerate(df['ndc_code']):
			found_ndc = [value in code for value in list_values]
			if any(found_ndc):
				indices.append(i)
		filtered_values = df.iloc[indices]
	else:
		values = [value.lower().strip() for value in list_values]
		filtered_values = df[df[field].str.lower().str.contains('|'.join(values), na=False)]
		if field == 'drug_class' and class_type is not None:
			filtered_values = filtered_values[filtered_values[class_type].str.contains(class_type)]
	print(f'Number of {field} ({list_values}) drugs found: {len(filtered_values)}')
	return filtered_values

# see overlap between dataframes
def find_df_overlap(df_1, df_2, field_1='drug_name', return_overlap=False, return_non_overlap=False):
	print(f'Finding overlap between {field_1} in two dataframes...')
	df_1_lower = [drug.lower() for drug in set(df_1[field_1].values)]
	print(f' Number of drugs in df_1: {len(df_1_lower)}')
	df_2_lower = [drug.lower() for drug in set(df_2[field_1].values)]
	print(f' Number of drugs in df_2: {len(df_2_lower)}')
	# see whether a drug in fda_drug_df matches any of the words for all drugs in df_2
	overlap_drugs_1 = [drug for drug in df_1_lower if any([word in drug for word in df_2_lower])]
	non_overlap_drugs_1 = [drug for drug in df_1_lower if drug not in overlap_drugs_1]
	print(f' Number of drugs from df_1 in df_2: {len(overlap_drugs_1)}')
	print(f'  df_1 drugs missing in df_2: {non_overlap_drugs_1[:10]}...')
	overlap_drugs_2 = [drug for drug in df_2_lower if any([word in drug for word in df_1_lower])]
	non_overlap_drugs_2 = [drug for drug in df_2_lower if drug not in overlap_drugs_2]
	print(f' Number of drugs from df_2 in df_1: {len(overlap_drugs_2)}')
	print(f'  df_2 drugs missing in df_1: {non_overlap_drugs_2[:10]}...')
	if return_overlap:
		# combine the two lists
		overlap_drugs = list(set(overlap_drugs_1 + overlap_drugs_2))
		print(f' Number of overlapping drugs: {len(overlap_drugs)}')
		return overlap_drugs
	elif return_non_overlap:
		# return drugs that are in df_1 but not in df_2
		print(f' Returning drugs in df_1 but not in df_2 (n={len(non_overlap_drugs_1)})...')
		return non_overlap_drugs_1
