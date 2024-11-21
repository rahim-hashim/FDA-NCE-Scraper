import os
import re
import sys
import time
import tqdm
import string
import argparse
import datetime
import textwrap
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
# turn off lxml warning
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
# pytrials
from utils.drug_search import read_pytrials_fields
from pytrials.client import ClinicalTrials
# urllib / BeautifulSoup
import urllib.request, urllib.parse, urllib.error
from bs4 import BeautifulSoup
# custom functions
from utils.webpage_scraping import test_connection
from utils.pickle_dataframes import unpickle_dataframes
from utils.ctgov_search import get_ctgov_synonyms
from utils.drug_search import ctgov_search, find_drug_multiple_fields
from utils.fda_sponsors import fda_sponsor_list, rename_sponsors, plot_sponsors
from utils.pubchem_search import search_pubchem
from utils.fda_api_search import scrape_fda_data, fda_api_dict_to_df


def pubmed_links_parser(pubmed_links):
	'''
	linksParser reads each URL from PMID_ListGenerator output 
	and parses specified info
	'''
	articleCount = 0; abstract_text = []
	searchesHash = defaultdict(lambda: defaultdict(list)) # primary key = PMID
	for link in tqdm.tqdm(pubmed_links):
		searchHash = defaultdict(str)
		authorAffiliationDict = defaultdict(list)
		affiliationDict = defaultdict(str)
		searchHash['articleCount'] = articleCount
		articleCount += 1
		# Open, read and process link through BeautifulSoup
		r1 = urllib.request.urlopen(link).read()
		soup = BeautifulSoup(r1, "html.parser")
		# Add link to searchHash
		searchHash['search_link'] = link
		# ARTICLE NAME Parser
		article_title = soup.find('title').text
		searchHash['article_title'] = article_title
		# META INFO (journal title, date published)
		meta = soup.find_all('meta')
		author_list = []
		author_institutions = []
		for tag in meta:
			if 'name' in tag.attrs.keys():
				if tag.attrs['name'] == 'citation_journal_title':
					searchHash['journal_title'] = tag.attrs['content']
				elif tag.attrs['name'] == 'citation_journal_abbrev':
					searchHash['journal_title_abv'] = tag.attrs['content']
				elif tag.attrs['name'] == 'citation_publisher':
					searchHash['publisher'] = tag.attrs['content']
				elif tag.attrs['name'] == 'citation_abstract':
					searchHash['abstract'] = tag.attrs['content']
				elif tag.attrs['name'] == 'citation_keywords':
					keywords_uncleaned = tag.attrs['content'].split(';')
					keywords = [keyword.strip().rstrip('.').lower() for keyword in keywords_uncleaned]
					searchHash['keywords'] = keywords
				elif tag.attrs['name'] == 'citation_publication_date' or tag.attrs['name'] == 'citation_online_date':
					if len(tag.attrs['content'].split('/')) == 2: # date format (YYYY/MM)
						tag.attrs['content'] = tag.attrs['content'].split('/')[0]
					searchHash['publication_date'] = tag.attrs['content']
				elif tag.attrs['name'] == 'citation_author':
					author_list.append(tag.attrs['content'])
				elif tag.attrs['name'] == 'citation_author_institution':
					author_institutions.append(tag.attrs['content'])
				elif tag.attrs['name'] == 'citation_pmid':
					PMID = tag.attrs['content']
				elif tag.attrs['name'] == 'citation_doi':
					searchHash['doi'] = 'doi.org/' + tag.attrs['content']
		searchHash['authors'] = author_list
		searchHash['author_institutions'] = author_institutions
		searchesHash[PMID] = searchHash
		# pause for a second to avoid overloading the server
		time.sleep(1)
	return searchesHash

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

def get_pubmed_info(pubmed_ids):
	pubmed_links = [f'https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}' for pubmed_id in pubmed_ids]
	pubmed_dict = pubmed_links_parser(pubmed_links)
	# sort by publication date
	pubmed_dict = dict(sorted(pubmed_dict.items(), key=lambda item: item[1]['publication_date'], reverse=True))
	return pubmed_dict

def write_pubchem_to_markdown(df, drug_name, active_ingredient, file):
	# write the pubchem dataframe to markdown
	cols = df.columns
	with open(file, 'a') as f:
		f.write(f'### PubChem Search: {drug_name} ({active_ingredient})\n\n')
		f.write(f'#### Summary\n\n')
		if len(df) > 0:
			for col in cols:
				if col == 'pubmed_ids':
					if df[col].iloc[0] != None:
						pubmed_ids = df[col].iloc[0]
						pubmed_dict = get_pubmed_info(pubmed_ids)
					else:
						pubmed_dict = {}
				else:
					text = f'> * **{col}:** {df[col].iloc[0]}'
					f.write(f'{text}\n')
			# write pubmed articles at the end
			if len(pubmed_dict) > 0:
				f.write(f'\n#### Pubmed Articles\n')
				for pmid, pmid_info in pubmed_dict.items():
					f.write(f'> **[{pmid_info["article_title"]}]({pmid_info["search_link"]})**\n')
					f.write(f'> * **Published**: {pmid_info["publication_date"]}\n')
					f.write(f'> * **Journal**: *{pmid_info["journal_title"]}*\n')
					abstract = pmid_info["abstract"]
					# remove HTML tags (i.e. <h3>, <p>, <i>, etc.)
					abstract = re.sub(r'<[^>]*>', '', abstract)
					f.write(f'> * **Abstract**: {abstract}\n')
					f.write('\n')
			else:
				f.write('> * No Pubmed Articles Found\n')
		else:
			f.write('> * No PubChem Results Found\n')

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
	
	if len(pubchem_df) > 0:
		ctgov_df = get_ctgov_synonyms(pubchem_df)

	# Company search
	# df = df_dict['combined_fda_df']
	# df_results = find_drug_multiple_fields(
	# 	df,
	# 	list(df.columns),
	# 	[company_name],
	# 	unique_values=False
	# )
	# write_to_markdown(
	# 	'company_search',
	# 	company_name,
	# 	f,
	# 	df_results			 
	# )
	# # search terms
	# for search_term in search_terms:
	# 	print(f'Searching {search_term}...')
	# 	for d_index, df_key in enumerate(['combined_fda_df', 'ctgov_df']):
	# 		print(f' Searching {df_key}...')
	# 		df = df_dict[df_key]
	# 		df_results = find_drug_multiple_fields(
	# 			df,
	# 			list(df.columns),
	# 			[search_term],
	# 			unique_values=False
	# 		)
	# 		write_to_markdown(
	# 			df_key,
	# 			search_term, 
	# 			f, 
	# 			df_results
	# 		)

def main(
		pdf_name = 'Gate Neurosciences Series B - September 2024.pdf', 
		company_name = 'Gateway Neuroscience',
		drug_name = 'zelquistinel',
		active_ingredient = 'NMDAR',
		search_terms = ['neurodegeneration']
	):

	df_dict = load_databases()
	report_path = create_markdown(company_name)

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

	main(
		pdf_name=args.file, 
		company_name=args.company_name, 
		drug_name=args.drug_name, 
		active_ingredient=args.active_ingredient,
		search_terms=args.search_terms
	)