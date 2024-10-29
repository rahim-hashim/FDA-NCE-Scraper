import os
import re
import sys
import time
import tqdm
import string
import datetime
import requests
import textwrap
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from collections import defaultdict
from utils.webpage_scraping import test_connection
from utils.pickle_dataframes import pickle_dataframe
from utils.drug_search import clean_drug_name
from utils.fda_sponsors import fda_sponsor_list, rename_sponsors
# surpress warnings
import warnings
pd.options.mode.chained_assignment = None  # default='warn'
warnings.simplefilter(action='ignore', category=FutureWarning)

def combine_values(list_1, list_2):
	combine_flag = True
	if (list_1 == None and list_2 == None) or (list_1 == [None] and list_2 == [None]):
		final_list = None
		combine_flag = False
	if list_1 == None or list_1 == [None]:
		final_list = list_2
		combine_flag = False
	if list_2 == None or list_2 == [None]:
		final_list = list_1
		combine_flag = False
	if combine_flag:
		final_list = list(set(list_1 + list_2))
	if final_list != None and len(final_list) == 1:
		final_list = final_list[0]
	return final_list

# access pubchem API
def get_pubchem_cid(drug):
	'''
	Get PubChem CID for a drug name
	'''
	base_url = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{drug}/cids/JSON'
	response = test_connection(base_url)
	if response.status_code == 404:
		return None
	try:
		cid = response.json()
	except:
		# print(f'  Error: {response.text}')
		return None
	if 'IdentifierList' in cid:
		cid = cid['IdentifierList']['CID'][0]
	else:
		cid = None
	# print(f'  PubChem CID for {drug}: {cid}')
	return cid

def get_pubchem_sid(drug):
	'''
	Get PubChem SID for a drug name
	'''
	base_url = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/substance/name/{drug}/sids/JSON'
	response = test_connection(base_url)
	if response.status_code == 404:
		return None
	try:
		sid = response.json()
	except:
		# print(f'  Error: {response.text}')
		return None
	if 'IdentifierList' in sid:
		sid = sid['IdentifierList']['SID'][0]
	else:
		sid = None
	# print(f'  PubChem SID for {drug}: {sid}')
	return sid

def get_pubchem_synonyms(drug, search_type='compound'):
	base_url = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/{search_type}/name/{drug}/synonyms/XML'
	response = test_connection(base_url)
	soup = BeautifulSoup(response.text, features='lxml')
	synonyms_soup = soup.find_all("information")
	if len(synonyms_soup) == 0:
		return [drug]
	synonyms = synonyms_soup[0].find_all("synonym")
	synonyms = [drug] + [synonym.get_text() for synonym in synonyms]
	# print(f'  Synonyms for {drug}: {synonyms}')
	return synonyms

def get_pubchem_description(drug):
	base_url = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{drug}/description/XML'
	response = test_connection(base_url)
	soup = BeautifulSoup(response.text, features='lxml')
	description_soup = soup.find_all("information")
	if len(description_soup) < 2:
		# print(f'  No description found for {drug}')
		return None
	try:
		description = description_soup[1].find("description").get_text()
		# print(f'  Description for {drug}: {description}')
	except:
		description = None
		# print(f'  No description found for {drug}')
	return description

def pubmed_cid_search(cid):
	base_url = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/xrefs/PubMedID/XML'
	response = test_connection(base_url)
	soup = BeautifulSoup(response.text, features='lxml')
	pmids_soup = soup.find_all("information")
	if len(pmids_soup) == 0:
		return None
	pmids = pmids_soup[0].find_all("pubmedid")
	pmids = [pmid.get_text() for pmid in pmids]
	return pmids

def get_pubchem_pmids(cids):
	if cids == None:
		return None
	pubmed_ids = []
	if type(cids) == list:
		for cid in cids:
			pmids = pubmed_cid_search(cid)
			if pmids != None:
				pubmed_ids += pmids
	else:
		pubmed_ids = pubmed_cid_search(cids)
	# remove duplicates
	if pubmed_ids != None:
		pubmed_ids = [pubmed_id for pubmed_id in set(pubmed_ids)]
		len_pubmed_ids = [len(pubmed_ids) if type(pubmed_ids) == list else 0][0]
	else:
		len_pubmed_ids = 0
	# print(f'  PubMed IDs for {cids}: {len_pubmed_ids}')
	return pubmed_ids

def get_pubchem_patents(drug):
	base_url = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{drug}/xrefs/PatentID/XML'
	response = test_connection(base_url)
	soup = BeautifulSoup(response.text, features='lxml')
	patents_soup = soup.find_all("information")
	if len(patents_soup) == 0:
		return None
	patents = patents_soup[0].find_all("patentid")
	patents = [patent.get_text() for patent in patents]
	print(f'  Patents for {drug}: {patents}')
	return patents

# # some active ingredients have multiple names separated by commas
# if ',' in active_ingredient:
# 	active_ingredients = active_ingredient.split(',')
# 	for active_ingredient in active_ingredients:
# 		active_ingredient_cleaned = active_ingredient.replace('and', '').strip()
# 		cid = combine_values([get_pubchem_cid(active_ingredient_cleaned)],

# get info for aspirin
def get_drug_info(drug_name, active_ingredient, pubchem_df):
	# if drug name is different from active ingredient, get info for both active ingredient and drug name and combine
	if drug_name != active_ingredient:
		# print(f' Searching PubChem CIDs:')
		cid = combine_values([get_pubchem_cid(active_ingredient)],
											 	 [get_pubchem_cid(drug_name)])
		# print(f' Searching PubChem SIDs:')
		sid = combine_values([get_pubchem_sid(active_ingredient)], 
											 	 [get_pubchem_sid(drug_name)])
		# print(f' Searching PubChem Compound Synonyms:')
		compound_synonyms = combine_values(get_pubchem_synonyms(active_ingredient), 
																		 	 get_pubchem_synonyms(drug_name))
		# print(f' Searching PubChem Substance Synonyms:')
		substance_synonyms = combine_values(get_pubchem_synonyms(active_ingredient, 'substance'), 
																				get_pubchem_synonyms(drug_name, 'substance'))
		# print(f' Searching PubChem Descriptions:')
		description = combine_values([get_pubchem_description(active_ingredient)], 
															 	 [get_pubchem_description(drug_name)])
	else:
		cid = get_pubchem_cid(active_ingredient)
		sid = get_pubchem_sid(active_ingredient)
		compound_synonyms = get_pubchem_synonyms(active_ingredient)
		substance_synonyms = get_pubchem_synonyms(active_ingredient, 'substance')
		description = get_pubchem_description(active_ingredient)
	if cid == None:
		print(f'  No PubChem CID found for {active_ingredient} or {drug_name}')
	print(f'  CID: {cid} | Synonyms {len(compound_synonyms)}')
	# print(f' Searching PubChem PubMed IDs:')
	pubmed_ids = get_pubchem_pmids(cid)
	pubchem_df = pd.concat([pubchem_df, pd.DataFrame({
		"drug_name": [drug_name],
		"active_ingredient": [active_ingredient],
		"cid": [cid],
		"sid": [sid],
		"compound_synonyms": [compound_synonyms],
		"substance_synonyms": [substance_synonyms],
		"description": [description],
		"pubmed_ids": [pubmed_ids],
		"link": [f'https://pubchem.ncbi.nlm.nih.gov/compound/{cid}']
		# "patents": None
	})], ignore_index=True)
	return pubchem_df

def convert_float_int(pubchem_df, col_name='cid'):
	# conver all values in cid to int
	id_count = 0
	for i, id in enumerate(pubchem_df[col_name]):
		# check for None or nan values
		if id == None or id != id:
			pubchem_df[col_name].iloc[i] = None
			continue
		id_count += 1
		if type(id) == list:
			pubchem_df[col_name].iloc[i] = [int(c) for c in id]
		else:
			pubchem_df[col_name].iloc[i] = int(id)
	# print(f'Number of {col_name.upper()}s: {id_count}')
	return pubchem_df

# add drug_name and active_ingredient to compound synonyms only if they are not already in the list
def add_drug_name_active_ingredient(df):
	for i, row in df.iterrows():
		compound_synonyms = row['compound_synonyms']
		if compound_synonyms == None:
			compound_synonyms = [row['drug_name'], row['active_ingredient']]
		elif row['drug_name'] not in compound_synonyms:
			compound_synonyms = [row['drug_name']] + compound_synonyms
		elif row['active_ingredient'] not in compound_synonyms:
			compound_synonyms = [row['active_ingredient']] + compound_synonyms
		df['compound_synonyms'].iloc[i] = compound_synonyms
	return df

# count the number of drugs that have either a CID or SID
def count_pubchem_ids(pubchem_df):
	cid_count = 0
	sid_count = 0
	for i, row in pubchem_df.iterrows():
		if row['cid'] != None:
			cid_count += 1
		if row['sid'] != None:
			sid_count += 1
	print(f'Number of drugs with CID: {cid_count}/{len(pubchem_df)}')
	print(f'Number of drugs with SID: {sid_count}/{len(pubchem_df)}')
	# print the drugs missing SID
	missing_sid = pubchem_df[pubchem_df['sid'].isnull()]
	print('  Drugs missing SID:')
	if len(missing_sid) == 0:
		print('  None')
	else:
		print(missing_sid[['drug_name', 'active_ingredient']])

# create a pandas dataframe
def search_pubchem(df, save_df=False):
	pubchem_df = pd.DataFrame(columns=["drug_name", "active_ingredient", "cid", "sid",  "compound_synonyms", "substance_synonyms", "description", "pubmed_ids", "link"])
	for d_index, drug_name in enumerate(df['drug_name'].values):
		active_ingredient = df['active_ingredient'].iloc[d_index]
		print(f'Getting drug info for {drug_name} ({active_ingredient})...({d_index+1}/{len(df)})')
		# some drugs have multiple active ingredients separated by commas
		pubchem_df = get_drug_info(drug_name, active_ingredient, pubchem_df)
	# convert all cids to int or list of ints
	pubchem_df = convert_float_int(pubchem_df, 'cid')
	pubchem_df = convert_float_int(pubchem_df, 'sid')
	# add drug_name and active_ingredient to compound synonyms only if they are not already in the list
	pubchem_df = add_drug_name_active_ingredient(pubchem_df)
	count_pubchem_ids(pubchem_df)
	if save_df:
		pickle_dataframe(pubchem_df, 'databases/pubchem_df.pkl')
	return pubchem_df