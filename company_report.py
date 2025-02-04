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
from utils.fda_sponsors import fda_sponsor_list, clean_sponsors
from utils.pubchem_search import search_pubchem
from utils.fda_api_search import scrape_fda_data, fda_api_dict_to_df
from utils.pubmed_parser import SearchParameters, entrezSearch, linksParser, semantic_scholar_search, construct_dataframe
# assign terms for search from the search file
from company_search import company_search
# ollama
from ollama import chat, ChatResponse

def dataParser(resultsList, searchParameters):
	"""
	dataParser creates a multi-nested dictionary
	containing all article data for each search term

	Args:
		resultsList (list): list of all article URLs for each search term

	Returns:
		data (dict): multi-nested dictionary containing all article data for each search term
	"""
	print('\nParsing info for search terms...')
	queriesHash = defaultdict(lambda: defaultdict(list)) # primary key = pubmed query
	for a_index, termLinks in enumerate(resultsList):
		query = searchParameters.searchTerms[a_index]
		searchesHash = linksParser(termLinks, searchParameters, query)
		queriesHash[query] = searchesHash
	return queriesHash

def pubmed_search(search_terms):
	parameters = {}
	# Database : Specified NCBI database
	#   Options = Pubmed [pubmed] | Pubmed Central [PMC] | Unigene [Unigene] | Others [Look Up Key]
	parameters['database'] = 'pubmed'
	# SearchTerms : PubMed desired search term(s)
	parameters['searchTerms'] = search_terms
	# searchLimit : Max number of articles for each search term
	parameters['searchLimit'] = 5
	# StartIndex : The start index for the search (larger for older papers)
	parameters['startIndex'] = 0
	searchParameters = SearchParameters(parameters)
	resultsList = entrezSearch(searchParameters)
	searchesHash = dataParser(resultsList, searchParameters)
	# searchesHash = semantic_scholar_search(searchesHash, verbose=True)
	authors_df = construct_dataframe(searchesHash)
	abstract_text_list = authors_df['abstract'].tolist()
	# combine into one string but getting rid of typeError: sequence item 0: expected str instance, float found
	abstract_text_list = [str(abstract) for abstract in abstract_text_list if abstract is not None]
	abstract_text = ' '.join(abstract_text_list)
	return abstract_text

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
		time.sleep(0.5)
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
		'fda_api_df': ['year', 'year_approval_count'],
	}
	if df_key in order_by_dict.keys():
		return order_by_dict[df_key]
	else:
		return order_by_dict['combined_fda_df']

def flatten_list(l):
	for el in l:
		if isinstance(el, list):
			yield from flatten_list(el)
		else:
			yield el

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
		# return file still open
		return f

def write_fda_to_markdown(f, df, search_term, field='active_ingredient'):
	file_path = f.name
	with open(file_path, 'a') as f:
		# prettify list of search terms for markdown
		if isinstance(search_term, list):
			search_term = ', '.join(search_term)
		# prettify the field for markdown
		field_string = field.replace('_', ' ').capitalize()
		f.write(f'#### {field_string}:\n\n')
		f.write(f'**{search_term}**\n\n')
		# cols = [
		# 	'year',
		# 	'year_approval_count',
		# 	'drug_name',
		# 	'active_ingredient',
		# 	'approval_date',
		# 	'approved_use', 
		# 	'dosage_and_administration', 
		# 	'mechanism_of_action'
		# ]
		cols = [
			'year', 
			'approval_date', 
			'drug_name',
			'active_ingredient', 
			'submission_type',
			'indications_and_usage',
			'mechanism_of_action',
			'sponsor',
			'drug_link'
		]
		# convert 'approval_date' column to YYYY-MM-DD format
		df['approval_date'] = pd.to_datetime(df['approval_date']).dt.strftime('%Y-%m-%d')
		# shorten the [text] in the 'indications_and_usage' and 'mechanism_of_action' columns to max 200 
		# text is in a list so first convert to string
		df['indications_and_usage'] = \
			df['indications_and_usage'].apply(lambda x: textwrap.shorten(' '.join(x), width=200, placeholder='...'))
		df['mechanism_of_action'] = \
			df['mechanism_of_action'].apply(lambda x: textwrap.shorten(' '.join(x), width=200, placeholder='...'))
		df['drug_link'] = df['drug_link'].apply(lambda x: f'[link]({x})')
		if len(df) == 1:
			f.write(df[cols].to_markdown(index=False))
		if len(df) > 1:
			# sort by year and then by year_approval_count
			df = df.sort_values(by=ordered_df('fda_api_df'))
			f.write(df[cols].to_markdown(index=False))
		else:
			f.write('> * No Approved Drugs Found\n')
		f.write('\n\n')

def plot_sponsors_report(
		df, 
		drug_name_field='drug_name', 
		sponsor_field='sponsor', 
		unique_drugs_only=True
	):
	# drop any rows that have the exact same (drug_name, sponsor) pair
	if unique_drugs_only and drug_name_field:
		df_sponsors = df.copy().drop_duplicates(subset=[drug_name_field, sponsor_field])
	else:
		df_sponsors = df.copy()
	sponsors = df_sponsors[sponsor_field]
	# drop any nan values
	sponsors = [sponsor for sponsor in sponsors if sponsor != '']
	if len(sponsors) == 0:
		print('No sponsors found')
		return
	# count the number of unique sponsors from a list where value_counts() cannot be used
	top_sponsors = pd.Series(sponsors).value_counts().nlargest(50)
	# plot
	f, axarr = plt.subplots(1, 2, dpi=300, sharey=True)
	top_sponsor_names = top_sponsors.index
	top_sponsor_counts = top_sponsors.values
	# print(list(zip(top_sponsor_names, top_sponsor_counts)))
	# make bar edges black
	axarr[0].bar(top_sponsor_names, top_sponsor_counts, edgecolor='black', color='#6B95B6')
	# rotate x-axis labels
	axarr[0].set_xticks(range(len(top_sponsor_names)))
	# for s_index, sponsor in enumerate(top_sponsor_names):
	# 	sponsor_df = df[df[sponsor_field] == sponsor]
	# 	statuses = phase_df['Status']
	# 	completed_studies = len([status for status in statuses if status == 'Completed'])
	# 	# plot as darker green if completed
	# 	if completed_studies > 0:
	# 		axarr[1].bar(p_index, top_phase_counts[p_index], edgecolor='black', color='#7eb1a1')
	# 	recruiting_studies = len([status for status in statuses if status == 'Recruiting'])
	# 	if recruiting_studies > 0:
	# 		axarr[1].bar(p_index, completed_studies+recruiting_studies, edgecolor='black', color='#deebe7')
	top_sponsors_truncated = [textwrap.shorten(sponsor, width=30, placeholder='...') for sponsor in top_sponsor_names]
	# make xticks font size to be proportional to the number of sponsors
	xtick_fontsize = 6 if len(top_sponsor_names) < 10 else 4
	axarr[0].set_xticklabels(top_sponsors_truncated, rotation=90, fontsize=xtick_fontsize, fontname='Optima')
	# show each sponsor on x-axis
	axarr[0].set_xlabel('Sponsor', fontsize=12, fontweight='bold', fontname='Optima')
	axarr[0].set_ylabel('Number of Clinical Trials', fontsize=12, fontweight='bold', fontname='Optima')
	plt.tight_layout()
	# make sure nothing is cut off
	plt.subplots_adjust(bottom=0.6, top=0.9)
	# create a second plot with the same bar plot but with Phases on the x-axis and sort by Phases (i.e. PHASE1, PHASE2, PHASE3, PHASE4)
	phases = df['Phases']
	phases = [phase for phase in phases if (phase != '') and (phase != 'NA')]
	# sort the phases
	phases = sorted(list(phases))
	# plot a bar graph of the number of drugs in each phase
	top_phases = pd.Series(phases).value_counts()
	# make sure it is sorted by phase
	sorted_top_phases = top_phases.sort_index()
	top_phase_names = sorted_top_phases.index
	top_phase_counts = sorted_top_phases.values
	# plot the number of drugs in each phase with hex AECEC4
	axarr[1].bar(top_phase_names, top_phase_counts, edgecolor='black', color='#AECEC4')
	# rotate x-axis labels
	axarr[1].set_xticks(range(len(top_phase_names)))
	axarr[1].set_xticklabels(top_phase_names, rotation=90, fontsize=6, fontname='Optima')
	# show each sponsor on x-axis
	axarr[1].set_xlabel('Phases', fontsize=12, fontweight='bold', fontname='Optima')
	# show the status of the studies in each phase
	for p_index, phase in enumerate(top_phase_names):
		phase_df = df[df['Phases'] == phase]
		statuses = phase_df['Study Status']
		completed_studies = len([status for status in statuses if status == 'Completed'])
		# plot as darker green if completed
		if completed_studies > 0:
			axarr[1].bar(p_index, top_phase_counts[p_index], edgecolor='black', color='#7eb1a1')
		recruiting_studies = len([status for status in statuses if status == 'Recruiting'])
		if recruiting_studies > 0:
			axarr[1].bar(p_index, completed_studies+recruiting_studies, edgecolor='black', color='#deebe7')
	# set yticks to be integers with only 0 and the rounded max value closest to 5 with 5 ticks regardless of the max value
	max_y = max(max(top_sponsor_counts), max(top_phase_counts))
	# round up to the nearest 5
	max_y = int(max_y + 5 - (max_y % 5))
	axarr[0].set_yticks(range(0, max_y, int(max_y / 5)))
	plt.tight_layout()
	return f

# make a plot with the largest number of sponsors
def rename_sponsors_report(df, drug_name_field='drug_name', sponsor_field='fda_2_sponsor', new_field='sponsor'):
	all_sponsors = df[sponsor_field].tolist()
	# clean the sponsors
	all_sponsors_lower = clean_sponsors(all_sponsors)
	final_sponsors = []
	for sponsor in all_sponsors_lower:
		sponsor_split = sponsor.split()
		for company in fda_sponsor_list:
			if company in sponsor_split or (len(company) > 5 and company in sponsor):
				sponsor = company
		final_sponsors.append(sponsor)
	if 'fda_drug_name' in df.columns:
		drug_name_field = 'fda_drug_name'
	for s_index in range(len(list(final_sponsors))):
		drug_name = df[drug_name_field].iloc[s_index]
		# print(f'  {s_index} {drug_name:<20} {all_sponsors[s_index]} -> {final_sponsors[s_index]}')
	df[new_field] = final_sponsors
	return df

def write_ctgov_sponsors_to_markdown(f, df, search_term, file_path):
	df = rename_sponsors_report(df, drug_name_field='NCT Number', sponsor_field='Sponsor')
	# plot sponsors
	sponsor_figure = plot_sponsors_report(
		df, 
		drug_name_field=None, 
		sponsor_field='Sponsor', 
		unique_drugs_only=True
	)
	if search_term != 'all':
		ctgov_link = f'https://clinicaltrials.gov/search?term={search_term}'
		f.write(f'**{search_term} ([link]({ctgov_link}))**\n')
	else:
		f.write(f'**All Synonyms**\n')
	min_sponsor_count = 10
	if sponsor_figure is not None and len(df) > min_sponsor_count:
		# get directory name for file
		dir_name = os.path.join(os.path.dirname(file_path), 'images')
		# make the directory if it doesn't exist
		if not os.path.exists(dir_name):
			os.makedirs(dir_name)
		figure_path = os.path.join(dir_name, f'sponsor_plot_{search_term}.png')
		sponsor_figure.savefig(figure_path)
		f.write(f'![sponsor_plot](images/sponsor_plot_{search_term}.png)')
		f.write('\n')
	# sort dataframe by most recent start date and write the date, title, and sponsor to the markdown file
	cols = ['Start Date', 'Completion Date', 'NCT Number', 'Study Title', 'Sponsor', 'Phases', 'Conditions']
	ct_dates_df = pd.DataFrame(columns=cols)
	if len(df) == 0:
		f.write('> * No Clinical Trials Found\n')
		return
	first_date_info = df.sort_values(by='Start Date', ascending=True).iloc[0][cols]
	ct_dates_df = pd.concat([ct_dates_df, pd.DataFrame(first_date_info).T], axis=0)
	if len(df) > 1:
		last_date_info = df.sort_values(by='Start Date', ascending=False).iloc[0][cols]
		ct_dates_df = pd.concat([ct_dates_df, pd.DataFrame(last_date_info).T], axis=0)
	# conver all 'NCT Number' to links
	ct_dates_df['NCT Number'] = ct_dates_df['NCT Number'].apply(lambda x: f'[{x}](https://clinicaltrials.gov/study/{x})')
	f.write(ct_dates_df.to_markdown(index=False))
	f.write('\n\n')

def write_ctgov_to_markdown(f, ctgov_df):
	search_terms = list(flatten_list([ctgov_df['Search Term'].values]))[0]
	search_terms = list(set(flatten_list(search_terms)))
	print(f'  Number of synonyms in ctgov: {len(search_terms)}')
	file_path = f.name
	with open(file_path, 'a') as f:
		f.write('\n#### Clinical Trials\n\n')
		write_ctgov_sponsors_to_markdown(f, ctgov_df, 'all', file_path)
		for search_term in search_terms:
			df = ctgov_df[ctgov_df['Search Term'].apply(lambda x: search_term in x)]
			# standardize sponsor names
			write_ctgov_sponsors_to_markdown(f, df, search_term, file_path)

def synonym_ctgov_search(pubchem_df):
	if len(pubchem_df) > 0:
		ctgov_df = get_ctgov_synonyms(pubchem_df)
		return ctgov_df

def llama_to_markdown(	
		f, 
		company_name, 
		drug_name, 
		active_ingredient, 
		indication, 
		target, 
		mechanism,
		abstract_text,
		model='llama3.2',	
	):
	# write the response from model to the markdown file
	file_path = f.name
	
	# ask llama about the company
	print(f'  Asking {model} about {company_name}')
	company_response: ChatResponse = chat(
		model=model, messages=[
		{
		'role': 'user',
		'content': 
			f'What do you know about {company_name}? Describe their lead drug,\
			including the indication and mechanism of action.',
		},
	])
	print(f'  Asking {model} about {drug_name}')
	drug_response: ChatResponse = chat(model=model, messages=[
		{
			'role': 'user',
			'content': 
				f'What do you know about {drug_name} and/or {active_ingredient}? \
				Describe the drug\'s mechanism of action, which is {mechanism}, \
				and its target, which is {target} for the indication {indication}.\
				Additionally, what is the standard of care for this indication?',
		},
		])
	
	print(f'  Asking {model} about abstracts read from pubmed')
	abstract_response: ChatResponse = chat(model=model, messages=[
		{
			'role': 'user',
			'content': f'After reading {abstract_text}, what can you tell me about \
								 the future of this research and its potential impact on the field?',
		},
		])
	# look at the top 20 articles and summarize any of findings that would be relevant 
	# to an investor that is considering investing in this company

	with open(file_path, 'a') as f:
		f.write(f'### {model}\n\n')
		# Company Details
		f.write(f'#### {company_name}\n\n')
		message_response = company_response['message']['content']
		message_response = re.sub(r'\n\n', '\n', message_response)
		f.write(f'{message_response}\n\n')
		# Drug Details
		f.write(f'#### Drug Details\n\n')
		message_response = drug_response['message']['content']
		message_response = re.sub(r'\n\n', '\n', message_response)
		f.write(f'{message_response}\n')
		# Pubmed Abstracts
		f.write(f'#### Pubmed Abstracts\n\n')
		message_response = abstract_response['message']['content']
		message_response = re.sub(r'\n\n', '\n', message_response)
		f.write(f'{message_response}\n\n')

def default_search(
		df_dict, 
		f, 
		company_name='Gateway Neuroscience',
		drug_name='zelquistinel', 
		active_ingredient='NMDAR', 
		indication=['neurodegeneration'],
		target=['NMDAR'],
		mechanism=['NMDAR antagonist']
):

	# search for drug/active ingredient in pubchem
	print(f'PubChem Search: {drug_name} ({active_ingredient})')
	pubchem_df = search_pubchem(
		pd.DataFrame(
			columns=["drug_name", "active_ingredient"], 
			data=[[drug_name, active_ingredient]]),
		save_df=False
	)
	f = write_pubchem_to_markdown(pubchem_df, drug_name, active_ingredient, f)
	
	# search for synonyms in ctgov
	ctgov_df = synonym_ctgov_search(pubchem_df)
	write_ctgov_to_markdown(f, ctgov_df)
		
	# FDA drug/active ingredient search
	## separate by indication, separate by target - maybe from chatgpt/perplexity?
	## access both static FDA table and API
	### eventually get to standard of care for indication - FDA approved drugs for this indication
	print(f'FDA Search: {drug_name} ({active_ingredient})')
	file_path = f.name
	with open(file_path, 'a') as f:
		f.write(f'### FDA Approved Drugs\n\n')

	df_drugs = df_dict['fda_api_df']
	drug_search_terms = [active_ingredient, drug_name]
	df_results = find_drug_multiple_fields(
		df_drugs,
		list(df_drugs.columns),
		drug_search_terms,
		unique_values=True
	)

	write_fda_to_markdown(
		f,
		df_results,
		drug_search_terms,
		field='active_ingredient'
	)

	# search for 'indication' in 'indications and usage' field

	## FOR LLMs, ask about "best in class" from info provided
	print(f'Searching Indication: {indication}...')
	df_results = find_drug_multiple_fields(
		df_drugs,
		['approved_use', 'indications_and_usage'],
		indication,
		unique_values=True
	)
	write_fda_to_markdown(
		f,
		df_results,
		indication,
		field='indications_and_usage'
	)

	# search for 'target' in 'mechanism of action' field
	print(f'Searching Target: {target}...')
	df_results = find_drug_multiple_fields(
		df_drugs,
		[ 'description',
			'pharm_class_cs', 
	 	  'pharm_class_epc', 
			'mechanism_of_action', 
			'spl_product_data_elements', 
			'drug_interactions',
			'clinical_pharmacology',
			'pharmacokinetics'
		],
		target,
		unique_values=True
	)
	write_fda_to_markdown(
		f,
		df_results,
		target,
		field='target'
	)

	# search for 'mechanism of action' in 'mechanism of action' field
	print(f'Searching Mechanism: {mechanism}...')
	df_results = find_drug_multiple_fields(
		df_drugs,
		[ 'description',
			'pharm_class_cs', 
	 	  'pharm_class_epc', 
			'mechanism_of_action', 
			'spl_product_data_elements', 
			'drug_interactions',
			'clinical_pharmacology',
			'pharmacokinetics'
		],
		mechanism,
		unique_values=True,
	)
	write_fda_to_markdown(
		f,
		df_results,
		mechanism,
		field='mechanism_of_action'
	)

	pubmed_search_terms = [
		company_name, 
		drug_name, 
		active_ingredient, 
		target, 
		mechanism
	]
	# flatten the search terms
	pubmed_search_terms = list(set(flatten_list(pubmed_search_terms)))
	abstract_text = pubmed_search(pubmed_search_terms)

	model = 'llama3.2'
	print(f'Asking {model}')
	llama_to_markdown(
		f, 
		company_name, 
		drug_name, 
		active_ingredient, 
		indication, 
		target, 
		mechanism,
		abstract_text,
		model=model
	)

	model = 'deepseek-r1'
	print(f'Asking {model}')
	llama_to_markdown(
		f, 
		company_name, 
		drug_name, 
		active_ingredient, 
		indication, 
		target, 
		mechanism,
		abstract_text,
		model=model
	)

def main(
		pdf_name = 'Gate Neurosciences Series B - September 2024.pdf', 
		company_name = 'Gateway Neuroscience',
		drug_name = 'zelquistinel',
		active_ingredient = 'NMDAR',
		indication = ['neurodegeneration'],
		target = ['NMDAR'],
		mechanism = ['NMDAR antagonist'],
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
	ctgov_df = default_search(
		df_dict, 
		report_path,
		company_name = company_name,
		drug_name = drug_name,
		active_ingredient = active_ingredient, 
		indication = indication,
		target = target,
		mechanism = mechanism
	)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Read provided pitch deck and write results to markdown')
	# boolean search_file argument that is default true unless otherwise specified
	parser.add_argument('--search_file', action='store_true', help='generate terms from search file')
	parser.add_argument('--file', help='diligence file name')
	parser.add_argument('--company_name', help='company name')
	parser.add_argument('--drug_name', help='drug name to search')
	parser.add_argument('--active_ingredient', help='active ingredient to search')
	parser.add_argument('--indication', nargs='+', help='search terms for indication')
	parser.add_argument('--target', nargs='+', help='search terms for drug target')
	parser.add_argument('--mechanism', nargs='+', help='search terms for mechanism of action')
	args = parser.parse_args()

	if args.search_file:
		print('Using company_search for search terms...')
		company_name = company_search['company_name']
		drug_name = company_search['drug_name']
		active_ingredient = company_search['active_ingredient']
		search_terms = company_search['active_ingredient']
		indication = company_search['indication']
		target = company_search['target']
		mechanism = company_search['mechanism']
	else:
		company_name = args.company_name
		drug_name = args.drug_name
		active_ingredient = args.active_ingredient
		indication = args.indication
		target = args.target
		mechanism = args.mechanism

	main(
		pdf_name=args.file, 
		company_name=company_name,
		drug_name=drug_name,
		active_ingredient=active_ingredient,
		indication=indication,
		target=target,
		mechanism=mechanism
	)