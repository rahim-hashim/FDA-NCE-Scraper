import os
import re
import string
import numpy as np
import pandas as pd
import warnings
import matplotlib.pyplot as plt
from collections import defaultdict, Counter
from pytrials.client import ClinicalTrials
from utils.fda_sponsors import fda_sponsor_list, rename_sponsors
# supress SettingWithCopyWarning in pandas
pd.options.mode.chained_assignment = None  # default='warn'

def find_drug(df, field, list_values, class_type=None, unique_values=False):
	print('Number of rows in input dataframe:', len(df))
	if field not in df.columns:
		print(f'  {field} not found in the dataframe...')
		print(f'  Columns in the dataframe: {df.columns}')
		return None
	# drop NaN values for the field
	df_nonnan = df.dropna(subset=[field])
	if len(df_nonnan) < len(df):
		print(f'  Number of rows after dropping NaN values in {field}: {len(df)}')
	if field == 'ndc_code':
		indices = []
		for i, code in enumerate(df['ndc_code']):
			found_ndc = [value in code for value in list_values]
			if any(found_ndc):
				indices.append(i)
		filtered_values = df.iloc[indices]
	else:
		values = [value.lower().strip() for value in list_values]
		# make a list of lists and strings into a list of strings
		df_field_values = df_nonnan[field].apply(lambda x: x if isinstance(x, str) else ' '.join(x))
		filtered_values = df_nonnan[df_field_values.str.lower().str.contains('|'.join(values), na=False)]
		if field == 'drug_class' and class_type is not None:
			filtered_values = filtered_values[filtered_values[class_type].str.contains(class_type)]
	print(f'  Number of {field} ({list_values}) drugs found: {len(filtered_values)}')
	if unique_values:
		# keep the instance with the most non-nan columns
		filtered_values['non_nan_count'] = filtered_values.notnull().sum(axis=1)
		filtered_values = filtered_values.sort_values(by='non_nan_count', ascending=False).drop_duplicates(subset=[field])
		# remove the non_nan_count column
		filtered_values = filtered_values.drop(columns=['non_nan_count'])
		print(f'  Number of unique {field} ({list_values}) drugs found: {len(filtered_values)}')
	return filtered_values

# find drug function but for multiple fields
def find_drug_multiple_fields(df, fields, list_values, unique_values=False, sort_fields=[]):
	print('Number of rows in input dataframe:', len(df))

	found_drugs_df = pd.DataFrame()
	for field in fields:
		filtered_df = df.copy()
		if field not in df.columns:
			print(f'  {field} not found in the dataframe...')
			print(f'  Columns in the dataframe: {df.columns}')
			return None
		
		# Drop NaN values for the current field
		filtered_df = filtered_df.dropna(subset=[field])
		if len(filtered_df) < len(df):
			print(f'  Number of rows after dropping NaN values in {field}: {len(filtered_df)}')
		values = [value.lower().strip() for value in list_values]
		# Make a list of lists and strings into a list of strings
		df_field_values = filtered_df[field].apply(lambda x: x if isinstance(x, str) else ' '.join(x))
		filtered_df = filtered_df[df_field_values.str.lower().str.contains('|'.join(values), na=False)]
		if len(filtered_df) == 0:
			print(f'  No {field} ({list_values}) drugs found...')
			continue
		found_drugs_df = pd.concat([found_drugs_df, filtered_df], ignore_index=True)
			
		print(f'  Number of {field} ({list_values}) drugs found: {len(filtered_df)}')
	print(f'Number of drugs found in all fields: {len(found_drugs_df)}')
	if len(found_drugs_df) == 0:
		found_drugs_df = pd.DataFrame(columns=df.columns)
	# Remove duplicates on 'fda_nce_id' if its in the columns
	if 'fda_nce_id' in found_drugs_df.columns:
		found_drugs_df = found_drugs_df.drop_duplicates(subset=['fda_nce_id'])
		print(f'  Number of drugs found after removing duplicates: {len(found_drugs_df)}')
	if unique_values:
		# keep the instance with the most non-nan columns
		found_drugs_df['non_nan_count'] = found_drugs_df.notnull().sum(axis=1)
		found_drugs_df = found_drugs_df.sort_values(by='non_nan_count', ascending=False).drop_duplicates(subset=[field])
		# remove the non_nan_count column
		found_drugs_df = found_drugs_df.drop(columns=['non_nan_count'])
		print(f'  Number of unique {field} ({list_values}) drugs found: {len(found_drugs_df)}')
	if len(sort_fields) > 0:
		found_drugs_df = found_drugs_df.sort_values(by=sort_fields)
		print(f'  Sorted by {sort_fields}')
	return found_drugs_df


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
		# dataframe from df_2 with overlapping drugs
		df_overlap = df_2[df_2[field_1].str.lower().isin(overlap_drugs)]
		return df_overlap
	elif return_non_overlap:
		# return drugs that are in df_1 but not in df_2
		print(f' Returning drugs in df_1 but not in df_2 (n={len(non_overlap_drugs_1)})...')
		return non_overlap_drugs_1

def get_bigram(segment):
	bigrams = []
	for index, word in enumerate(segment):
		if index == len(segment) - 1:
			break
		# strip all punctuation from the segment
		n_1 = segment[index].translate(str.maketrans('', '', string.punctuation))
		# get the next word
		n2 = segment[index + 1].translate(str.maketrans('', '', string.punctuation))
		# add the bigram to the list
		bigrams.append(n_1 + ' ' + n2)
	return bigrams

# same function as get_bigram but for n-grams
def get_ngram(segment, n):
	ngrams = []
	if len(segment) < n:
		return ngrams
	for index, word in enumerate(segment):
		if index == len(segment) - n:
			break
		# strip all punctuation from the segment
		ngram = ''
		for i in range(n):
			ngram += segment[index + i].translate(str.maketrans('', '', string.punctuation)) + ' '
		# add the ngram to the list
		ngrams.append(ngram.strip())
	return ngrams

def levenshtein_ratio_and_distance(s, t, ratio_calc = False):
	""" levenshtein_ratio_and_distance:
			Calculates levenshtein distance between two strings.
			If ratio_calc = True, the function computes the
			levenshtein distance ratio of similarity between two strings
			For all i and j, distance[i,j] will contain the Levenshtein
			distance between the first i characters of s and the
			first j characters of t
	"""
	# Initialize matrix of zeros
	rows = len(s)+1
	cols = len(t)+1
	distance = np.zeros((rows,cols),dtype = int)

	# Populate matrix of zeros with the indeces of each character of both strings
	for i in range(1, rows):
		for k in range(1,cols):
			distance[i][0] = i
			distance[0][k] = k

	# Iterate over the matrix to compute the cost of deletions,insertions and/or substitutions    
	for col in range(1, cols):
		for row in range(1, rows):
			if s[row-1] == t[col-1]:
				cost = 0 # If the characters are the same in the two strings in a given position [i,j] then the cost is 0
			else:
				# In order to align the results with those of the Python Levenshtein package, if we choose to calculate the ratio
				# the cost of a substitution is 2. If we calculate just distance, then the cost of a substitution is 1.
				if ratio_calc == True:
					cost = 2
				else:
					cost = 1
			distance[row][col] = min(distance[row-1][col] + 1,      # Cost of deletions
														distance[row][col-1] + 1,          # Cost of insertions
														distance[row-1][col-1] + cost)     # Cost of substitutions
	if ratio_calc == True:
		# Computation of the Levenshtein Distance Ratio
		# deal with the edge case where the length of the string is 0
		if len(s) == 0 or len(t) == 0:
			Ratio = 0
		else:
			Ratio = ((len(s)+len(t)) - distance[row][col]) / (len(s)+len(t))
		return Ratio
	else:
		# print(distance) # Uncomment if you want to see the matrix showing how the algorithm computes the cost of deletions,
		# insertions and/or substitutions
		# This is the minimum number of edits needed to convert string a to string b
		return "The strings are {} edits away".format(distance[row][col])

def fuzzy_matching(target_word, segments, fuzzy_threshold=0.8):
	'''Fuzzy matching for players while requesting from html'''
	fuzzy_matches = defaultdict(lambda: defaultdict(list))
	max_fuzzy = [0, None]  # [score, name]
	target_word_size = len(target_word.split())
	# split segments into n-grams
	for idx, segment in enumerate(segments):
		segment_words = segment.split()
		# get the n-grams
		ngrams = get_ngram(segment_words, target_word_size)
		# perform fuzzy matching on the bi-grams
		for ngram in ngrams:
			fuzzy_ratio = levenshtein_ratio_and_distance(target_word.lower(), ngram.lower(), ratio_calc=True)
			if fuzzy_ratio > max_fuzzy[0]:
				max_fuzzy = [fuzzy_ratio, ngram]
			# if above a threshold, stop looking for the word
			if max_fuzzy[0] >= fuzzy_threshold:
				break
	# align the target word, match score and the segment print using fstring
	# print(f'  \"{target_word}\" Match Score: {round(max_fuzzy[0], 4):<6} | Match: {max_fuzzy[1]}')
	return (max_fuzzy[0], max_fuzzy[1])



def clean_drug_name(drug_name):
	if drug_name is None:
		return None
	# check if it has (<dose>)
	if '(' in drug_name:
		drug_name = drug_name.split('(')[0].strip()
	dose_information_types = ['capsule', 'kit']
	# check if it has a dose information type
	for dose_type in dose_information_types:
		if dose_type in drug_name:
			drug_name = drug_name.split(dose_type)[0].strip()
	return drug_name

# see overlap between dataframes
def combine_fda_dfs(df_1, df_2, field_1='drug_name', field_2='active_ingredient'):
	print(f'Finding overlap between {field_1} in dataframes...')
	fda_columns = list(map('fda_{}'.format, list(df_1.columns)))
	approved_columns = list(map('fda_2_{}'.format, list(df_2.columns)))
	combined_columns = fda_columns + approved_columns
	print(f'Combined columns: {combined_columns}')
	fda_approved_df = pd.DataFrame(columns=combined_columns)
	for i, drug in df_1.iterrows():
		# check if the drug name is in the active ingredient field
		drug_1_lower = clean_drug_name(drug[field_1].lower())
		# check if it contains extraneous information (i.e. Sivextro (tablet)Sivextro (injection))
		active_ingredient_lower = drug[field_2].lower()
		ddc_found = False
		df_2_drug = df_2[df_2[field_1].str.lower() == drug_1_lower]
		if len(df_2_drug) > 0:
			# concatenate drug_2 to the fda_ddc_df with all the columns
			ddc_row = [*drug, *df_2_drug.iloc[0]]
			fda_approved_df.loc[i] = ddc_row
			print(f'  {drug[field_1]:<20} -> {fda_approved_df.loc[i]["fda_2_drug_name"]:<20}...({i}/{len(df_1)})')
			ddc_found = True
			continue
		for j, drug_2 in df_2.iterrows():
			# check if the drug name is in the active ingredient field
			drug_2_lower = clean_drug_name(drug_2[field_1].lower())
			generic_name_2 = drug_2['active_ingredient']
			if generic_name_2 is None:
				generic_name_2 = ''
			generic_name_2_lower = generic_name_2.lower()
			if drug_1_lower == drug_2_lower or \
				 drug_1_lower == generic_name_2_lower or \
				 active_ingredient_lower == generic_name_2_lower or \
				 active_ingredient_lower == drug_2_lower:
				# concatenate drug_2 to the fda_ddc_df with all the columns
				ddc_row = [*drug, *drug_2]
				fda_approved_df.loc[i] = ddc_row
				print(f'  {drug[field_1]:<20} -> {fda_approved_df.loc[i]["fda_2_drug_name"]:<20}...({i}/{len(df_1)})')
				ddc_found = True
				break
		if not ddc_found:
			ddc_row = [*drug] + [np.nan]*len(df_2.columns)
			fda_approved_df.loc[i] = ddc_row
			missing_str = 'No match found...'
			print(f'  {drug[field_1]:<20} -> {missing_str:<20}...({i}/{len(df_1)})')
	# count number of drugs with non-nan values for ddc_drug_name
	print(f'Number of drugs overlapping: {len(fda_approved_df.dropna(subset=["fda_2_drug_name"]))}')
	return fda_approved_df

def combine_ddc_databases(df_1, df_2):
	'''Insert drugs missing from df_1 into df_2'''
	# get drugs missing from df_1
	missing_drugs = find_df_overlap(df_1, df_2 , 'drug_name', return_overlap=False)
	df_2_copy = df_2.copy()
	combined_df = pd.concat([df_1, df_2_copy], ignore_index=True)
	# sort by drug name
	combined_df = combined_df.sort_values(by=['drug_name']).reset_index(drop=True)
	unique_drugs = combined_df['drug_name'].unique()
	print('Number of unique drugs in combined database:', len(unique_drugs))
	if 'Generic name' in combined_df.columns:
		# find differences between fields 'Generic name' and 'generic_name'
		generic_name_diff = combined_df[combined_df['Generic name'] != combined_df['generic_name']]
		combined_df['generic_name'] = combined_df['generic_name'].fillna(combined_df['Generic name'])
		# do the same for 'Generic name'
		combined_df['Generic name'] = combined_df['Generic name'].fillna(combined_df['generic_name'])
		# rename 'Generic name' to 'drug_name_generic'
		combined_df.rename(columns={'Generic name': 'drug_name_generic'}, inplace=True)
		# rename 'generic_name' to 'drug_name_generic_drugclass'
		combined_df.rename(columns={'generic_name': 'drug_name_generic_drugclass'}, inplace=True)
	return combined_df

# open pytrials_fields.csv
def read_pytrials_fields(verbose=False):
	if not os.path.exists('databases/pytrials_fields.csv'):
		print('pytrials_fields.csv not found...')
		return None
	pytrial_fields = pd.read_csv('databases/pytrials_fields.csv')
	ct_fields = pytrial_fields['Column Name'].values
	if verbose:
		print('pytrials fields:')
		[print(f'  {field}') for field in ct_fields]
	return ct_fields

def ctgov_search(search_term):
	ct_fields = read_pytrials_fields()
	ct = ClinicalTrials()
	print(f'Searching CT for {search_term}...')
	ct_output = ct.get_study_fields(
		search_expr=search_term,
			fields=ct_fields,
			max_studies=1000,
			fmt="csv",
		)
	if ct_output is None:
		print(f'  No CT results.')
	# convert to dataframe
	columns = ['search_term'] + ct_output[0]
	data_df = pd.DataFrame(columns=columns)
	print(f'  Number of CTs found: {len(ct_output)}')
	for row in ct_output[1:]:
		data_df = pd.concat([data_df, pd.DataFrame([search_term] + row, index=columns).T], ignore_index=True)
	return data_df