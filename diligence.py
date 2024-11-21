import os
import re
import sys
import time
import tqdm
import argparse
import datetime
import textwrap
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
from pytrials.client import ClinicalTrials
# turn off lxml warning
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
# custom functions
from utils.pickle_dataframes import unpickle_dataframes
from utils.drug_search import ctgov_search, find_drug_multiple_fields
from utils.fda_sponsors import fda_sponsor_list, rename_sponsors, plot_sponsors
from utils.pubchem_search import search_pubchem
from utils.fda_api_search import scrape_fda_data, fda_api_dict_to_df

def load_databases():
	print(f'Loading Database...')
	df_dict = unpickle_dataframes(database_folder='databases')
	return df_dict

def read_pdf(report_path, pdf_dir, pdf_name):
	print(f'  Reading {pdf_name}')
	# process using llama3.2

def ordered_df(df_key):
	order_by_dict = {
		'combined_fda_df': ['fda_year', 'fda_year_approval_count'],
		'ctgov_df': ['Study Title'],
		'dailymed_df': ['drug_name'],
	}
	if df_key in order_by_dict.keys():
		return order_by_dict[df_key]
	else:
		return order_by_dict['combined_fda_df']

df_keys_dict = \
	{'ctgov_df': 
		['search_term', 'NCT Number', 'Study Title', 'Study URL', 'Acronym',
		 'Study Status', 
		#  'Brief Summary', 
		 'Study Results', 'Conditions',
     'Interventions', 'Sponsor', 'Collaborators', 'Phases', 'Enrollment', 
		 'Funder Type', 'Study Type', 
		 'Start Date', 'Primary Completion Date', 'Completion Date', 
		 'First Posted', 'Results First Posted', 'Last Update Posted', 
		 'Locations', 'Study Documents'],
	}

def df_cols(df_key):
	if df_key in df_keys_dict.keys():
		return df_keys_dict[df_key]

def create_markdown(
	company_name,
	results_dir='results',
):
	if not os.path.exists(results_dir):
		os.makedirs(results_dir)
	report_path = os.path.join(results_dir, f'{company_name}.md')
	print(f'Creating {report_path}')
	with open(report_path, 'w') as f:
		f.write(f'# {company_name}')
		date = datetime.date.today()
		date_formatted = date.strftime('%B %d, %Y')
		f.write(f'\n## {date_formatted}\n\n')
	return report_path

def write_pubchem_to_markdown(df, drug_name, active_ingredient, file):
	# write the pubchem dataframe to markdown
	cols = df.columns
	with open(file, 'a') as f:
		f.write(f'### PubChem Search: {drug_name} ({active_ingredient})\n')
		f.write('\n')
		if len(df) > 0:
			f.write(df[cols].to_markdown(index=False))
		else:
			f.write('> * No PubChem Results Found')
		f.write(f'\n### Search Terms\n')


def write_fda_to_markdown(f, df, search_term, cols, sort_by):
	f.write(f'#### {search_term}\n')
	f.write(f'**FDA Approvals**\n\n')
	if len(df) == 1:
		f.write(df[cols].to_markdown(index=False))
	if len(df) > 1:
		df = df.sort_values(by=ordered_df(sort_by), ascending=False)
		f.write(df[cols].to_markdown(index=False))
	else:
		f.write('> * No Approved Drugs Found\n')
	f.write('\n\n')

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

def get_ctgov_synonyms(pubchem_df):
	ct_fields = read_pytrials_fields()
	ct = ClinicalTrials()
	# create a dataframe
	ctgov_df = pd.DataFrame(columns=['Drug Name', 'Search Term'] + list(ct_fields))
	for d_index, drug in enumerate(pubchem_df['drug_name'].values):
		ctgov_df = parse_ctgov_synonyms(pubchem_df, ctgov_df, ct, drug, ct_fields)
	# clean the dataframe
	ctgov_df = clean_ctgov_df(ctgov_df)
	return ctgov_df

def write_ctgov_to_markdown(f, search_term, cols):
	# convert list to string in ['Drug Name'] column
	# df['Drug Name'] = df['Drug Name'].apply(lambda x: ', '.join(x))
	df = ctgov_search(search_term)
	# standardize sponsor names
	# df = rename_sponsors(df, drug_name_field='NCT Number', sponsor_field='Sponsor')
	# plot sponsors
	sponsor_figure = plot_sponsors(
		df, 
		drug_name_field=None, 
		sponsor_field='Sponsor', 
		unique_drugs_only=False
	)
	if sponsor_figure is not None:
		# get directory name for file
		file_path = f.name
		dir_name = os.path.join(os.path.dirname(file_path), 'images')
		# make the directory if it doesn't exist
		if not os.path.exists(dir_name):
			os.makedirs(dir_name)
		figure_path = os.path.join(dir_name, f'sponsor_plot_{search_term}.png')
		sponsor_figure.savefig(figure_path)
		f.write(f'**Clinical Trial Sponsors**\n')
		f.write(f'![sponsor_plot](images/sponsor_plot_{search_term}.png)')
		f.write('\n')
	# sort dataframe by most recent start date
	df = df.sort_values(by='Start Date', ascending=False).head(10)
	# make a markdown table with the first 20 rows
	f.write('\n')
	if len(df) > 0:
		print(df)
		f.write(df[cols].to_markdown(index=False))
	else:
		f.write('> * No Clinical Trials Found\n')
	f.write('\n\n')

def write_to_markdown(df_key, search_term, file, df):
	with open(file, 'a') as f:
		if df_key == 'combined_fda_df' or df_key == 'company_search':
			write_fda_to_markdown(f, df, search_term, df.columns[1:], ordered_df(df_key))
		if df_key == 'ctgov_df' or df_key == 'company_search':
			write_ctgov_to_markdown(f, search_term, df_cols('ctgov_df'))

def default_search(
		df_dict, 
		f, 
		company_name='Gateway Neuroscience',
		drug_name='zelquistinel', 
		active_ingredient='NMDAR', 
		search_terms=['cancer']
):
	print(f'PubChem Search: {drug_name} ({active_ingredient})')
	pubchem_df = search_pubchem(
		pd.DataFrame(
			columns=["drug_name", "active_ingredient"], 
			data=[[drug_name, active_ingredient]]),
		save_df=False
	)
	write_pubchem_to_markdown(pubchem_df, drug_name, active_ingredient, f)
	# Company search
	df = df_dict['combined_fda_df']
	df_results = find_drug_multiple_fields(
		df,
		list(df.columns),
		[company_name],
		unique_values=False
	)
	write_to_markdown(
		'company_search',
		company_name,
		f,
		df_results			 
	)
	# search terms
	for search_term in search_terms:
		print(f'Searching {search_term}...')
		for d_index, df_key in enumerate(['combined_fda_df', 'ctgov_df']):
			print(f' Searching {df_key}...')
			df = df_dict[df_key]
			df_results = find_drug_multiple_fields(
				df,
				list(df.columns),
				[search_term],
				unique_values=False
			)
			write_to_markdown(
				df_key,
				search_term, 
				f, 
				df_results
			)

def main(
		pdf_name = 'Gate Neurosciences Series B - September 2024.pdf', 
		company_name = 'Gateway Neuroscience',
		drug_name = 'zelquistinel',
		active_ingredient = 'NMDAR',
		search_terms = ['cancer']
	):
	# load the databases
	df_dict = load_databases()
	# create markdown file
	report_path = create_markdown(company_name)
	# LLM processing of PDF
	# read_pdf(
	# 	report_path, 
	# 	pdf_dir='diligence_examples', 
	# 	pdf_name=pdf_name
	# )
	# search for drug name and active ingredient in the databases
	default_search(
		df_dict, 
		report_path,
		company_name = company_name,
		drug_name = drug_name,
		active_ingredient = active_ingredient, 
		search_terms = search_terms
	)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Read provided pitch deck and write results to markdown')
	parser.add_argument('--file', help='diligence file name')
	parser.add_argument('--company_name', help='company name')
	parser.add_argument('--drug_name', help='drug name to search')
	parser.add_argument('--active_ingredient', help='active ingredient to search')
	parser.add_argument('--search_terms', nargs='+', help='search terms')
	args = parser.parse_args()
	print(args.search_terms)
	
	# main(
	# 	pdf_name=args.file, 
	# 	company_name=args.company_name, 
	# 	drug_name=args.drug_name, 
	# 	active_ingredient=args.active_ingredient,
	# 	search_terms=args.search_terms
	# )