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
# turn off lxml warning
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
# custom functions
from utils.pickle_dataframes import unpickle_dataframes
from utils.drug_search import ctgov_search, find_drug_multiple_fields
from utils.fda_sponsors import fda_sponsor_list, rename_sponsors, plot_sponsors
from utils.pubchem_search import search_pubchem

def load_databases():
	print(f'Loading Database...')
	df_dict = unpickle_dataframes(database_folder='databases')
	return df_dict

def read_pdf(report_path, pdf_dir, pdf_name):
	print(f'Reading {pdf_name}')
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
		['Search Term', 'NCT Number', 'Study Title', 'Study URL', 'Acronym',
		 'Study Status', 'Brief Summary', 'Study Results', 'Conditions',
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
	results_dir='results',
	company_name='company'
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
		f.write('\n')

def write_to_markdown(df_key, search_term, file, df):
	cols = df.columns[1:]
	# sort columns by fda_year and then fda_year_approval_count
	with open(file, 'a') as f:
		if df_key == 'combined_fda_df':
			f.write(f'### {search_term}\n')
			f.write(f'**FDA Approvals**\n')
			df = df.sort_values(by=ordered_df(df_key), ascending=False)
				# make a markdown table with the first 5 columns of the dataframe
			f.write('\n')
			if len(df) > 0:
				f.write(df[cols].to_markdown(index=False))
			else:
				f.write('> * No Approved Drugs Found\n')
			f.write('\n\n')
		elif df_key == 'ctgov_df':
			# convert list to string in ['Drug Name'] column
			df['Drug Name'] = df['Drug Name'].apply(lambda x: ', '.join(x))
			# create a pie chart of the sponsors and insert it into the markdown
			df = rename_sponsors(df, drug_name_field='NCT Number', sponsor_field='Sponsor')
			sponsor_figure = plot_sponsors(
				df, 
				drug_name_field='Drug Name', 
				sponsor_field='Sponsor', 
				unique_drugs_only=True
			)
			if sponsor_figure is not None:
				# get directory name for file path
				dir_name = os.path.join(os.path.dirname(file), 'images')
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
				ct_cols = df_cols(df_key)
				f.write(df[ct_cols].to_markdown(index=False))
			else:
				f.write('> * No Clinical Trials Found\n')
			f.write('\n\n')

def default_search(df_dict, f, drug_name='zelquistinel', active_ingredient='NMDAR', search_terms=['cancer']
):
	print(f'PubChem Search: {drug_name} ({active_ingredient})')
	pubchem_df = search_pubchem(
		pd.DataFrame(
			columns=["drug_name", "active_ingredient"], 
			data=[[drug_name, active_ingredient]]),
		save_df=False
	)
	write_pubchem_to_markdown(pubchem_df, drug_name, active_ingredient, f)
	for search_term in search_terms:
		# for d_index, df_key in enumerate(df_dict.keys()):
		for d_index, df_key in enumerate(['combined_fda_df', 'ctgov_df']):
			print(f'Searching {df_key}...')
			df = df_dict[df_key]
			df_results = find_drug_multiple_fields(
				df,
				list(df.columns),
				[search_term],
				unique_values=True
			)
			write_to_markdown(
				df_key,
				search_term, 
				f, 
				df_results
			)

def main(pdf_name='Gate Neurosciences Series B - September 2024.pdf'):
	df_dict = load_databases()
	report_path = create_markdown(company_name='Gateway Neuroscience')
	# LLM processing of PDF
	read_pdf(
		report_path, 
		pdf_dir='diligence_examples', 
		pdf_name=pdf_name
	)
	# search for terms in the databases
	default_search(
		df_dict, 
		report_path,
		drug_name = 'zelquistinel',
		active_ingredient = 'NMDAR', 
		search_terms =
			['NMDA', 
			 'depression', 
			 'cognitive impairment', 
			 'alzheimer'
			 ]
	)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Read provided pitch deck and write results to markdown')
	parser.add_argument('--file', help='diligence file name')
	# parse arguments
	args = parser.parse_args()
	main(pdf_name=args.file)