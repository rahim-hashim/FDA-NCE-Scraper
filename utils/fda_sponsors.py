import re
import string
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# found combining sponsor names from the FDA NCE database
fda_sponsor_list = [
	'Abbott',
	'Alba Bioscience',
	'Allecra',
	'Allergan',
	'Almirall',
	'Alnylam',
	'Altor Bioscience',
	'Alvogen Pine Brook',
	'Amgen',
	'Amicus',
	'Amivas',
	'Amneal',
	'Amryt',
	'Amylyx',
	'Anacor',
	'Apellis',
	'Apotex',
	'Ardelyx',
	'Argenx Bv',
	'Array Biopharma',
	'Ascendis Pharma Encocrinology Div As',
	'Astellas',
	'Astrazeneca',
	'Aurinia',
	'Aurobindo',
	'Aveo',
	'Avid Radiopharms',
	'Axsome Malta',
	'Basilea',
	'Bausch',
	'Bausch And Lomb',
	'Bayer',
	'Bdsi',
	'Beigene',
	'Biocodex Sa',
	'Biocryst',
	'Biogen',
	'Biolinerx',
	'Biomarin',
	'Bioverativ Therapeutics',
	'Bluebird',
	'Blue Earth',
	'Blueprint Medicines',
	'Boehringer Ingelheim',
	'Botanix',
	'Bracco',
	'Braintree Labs',
	'Breckenridge',
	# 'Bristol',
	'Bristol Myers Squibb',
	# 'Bristolmyers',
	# 'Bristolmyers Squibb',
	'Btg International',
	'Btg Intl',
	'Cara',
	'Cardinal Health',
	'Catalyst',
	'Celgene',
	'Chemo Research Sl',
	'Chemocentryx',
	'Chiesi',
	'Cipla',
	'Clivunel',
	'Coherus Biosciences',
	'Commave',
	'Cormedix',
	'Cosette',
	'Covis',
	'CSL Behring',
	'Cti Biopharma',
	'Cubist',
	'Daiichi Sankyo',
	'Day One Biopharms',
	'Deciphera',
	'Dermavant Sci',
	'Dompe Farmaceutici',
	'Dr Reddys',
	'Dutch Ophthalmic',
	'Dyax',
	'Eisai',
	'Eli Lilly',
	'Elusys Therapeutics',
	'Emd Serono',
	'Entasis',
	'Epizyme',
	'Esperion',
	'Eugia Pharma Speclts',
	'Eusa',
	'Evive Biotechnology',
	'Evol',
	'Fabre Kramer',
	'Ferrer Internacional',
	'Ferring',
	'Foldrx',
	'Fonseca Biosciences',
	'Fresenius Kabi',
	'G1',
	'Galderma Labs Lp',
	'Ge',
	'Genentech',
	'Genmab',
	'Genzyme',
	'Geron',
	'Gilead Sciences',
	'Giskit',
	'Glaxo Grp',
	'Glaxosmithkline',
	'Global Blood',
	'Guerbet',
	'Harmony',
	'Hatchtech',
	'Helsinn',
	'Hetero Labs',
	'Hoffmannla Roche',
	'Horizon Therapeutics',
	'Hugel',
	'Human Genome Sciences',
	'Idorsia',
	'Immucor',
	'Immunocore',
	'Immunogen',
	'Immunomedics',
	'Immunotek',
	'Incyte',
	'Ingenus',
	'Innate',
	'Intracellular',
	'Ipsen',
	'Ironwood',
	'Italfarmaco',
	'Janssen',
	'Jazz',
	'Kadmon',
	'Kai',
	'Karyopharm',
	'Kastle',
	'Key',
	'Knight',
	'Kyowa Kirin',
	'La Jolla',
	'Laurus Generics',
	'Lees',
	'Leo Pharma As',
	'Lexicon',
	'Life Molecular',
	'Lnhc',
	'Loxo Oncol',
	'Loxo Oncol Eli Lilly',
	'Lumicell',
	'Lundbeck Seattle Biopharmaceuticals',
	'Lupin',
	'Macrogenics',
	'Madrigal',
	'Mallinckrodt',
	'Marinus',
	'Mayne',
	'Mdgh',
	'Mediwound',
	'Melinta',
	'Merck',
	'Millipore',
	'Mirati',
	'Mirum',
	'Mp Biomedicals',
	'Morphosys',
	'Msn',
	'Msn Labs Pvt',
	'Mundipharma',
	'Mycovia',
	'Mylan',
	'Nabriva',
	'Natco',
	'National Cancer Institute',
	'Nektar Therapeutics'
	'Neurocrine',
	'Nippon Shinyaku',
	'Novartis',
	'Novimmune Sa',
	'Novo',
	'Novo Nordisk',
	'Nps',
	'On Target Labs',
	'Otsuka',
	'Paratek',
	'Pf Prism Cv',
	'Pfizer',
	'Pharmaessentia',
	'Pharming',
	'Phathom',
	'Polarean',
	'Portola',
	'Prinston',
	'Progenics',
	'Provention Bio',
	'Radiomedix',
	'Radius',
	'Reata',
	'Recordati Rare',
	'Redhill',
	'Regeneron',
	'Rempex',
	'Revance Therapeutics',
	'Rhythm',
	'Ridgeback Biotherapeutics',
	'Rigel',
	'Roche',
	'Rk',
	'Sage',
	'Salix',
	'Sandoz',
	'Sanofi',
	'Sarepta',
	'Scynexis',
	'Seagen',
	'Secura',
	'Sentynl',
	'Servier',
	'Shield Tx',
	'Shionogi',
	'Siga Technologies',
	'Sk Life',
	'Slayback',
	'Spectrum',
	'Springworks',
	'Sprout',
	'Stemline',
	'Stemline Therapeutics',
	'Sumitomo',
	'Sumitomo Pharma Am',
	'Sun',
	'Supernus',
	'Taiho Oncology',
	'Takeda',
	'Tarsus',
	'Tersera',
	'Tetraphase',
	'Teva',
	'Tg',
	'Tg Therapeutics',
	'Theracosbio',
	'Theratechnologies',
	'Thrombogenics',
	'Torrent',
	'Travere',
	'Trevena',
	'Ucb',
	'Ultragenyx',
	'United',
	'Urovant',
	'Uswm',
	'Valeant Luxembourg',
	'Valinor',
	'Vancocin Italia',
	'Vanda',
	'Verona',
	'Vertex',
	'Vgyaan',
	'Viela Bio',
	'Vifor',
	'Viiv',
	'Visiox',
	'Wyeth',
	'X4',
	'Ymabs Therapeutics',
	'Zealand',
	'Zenara',
	'Zhejiang Yongning',
	'Zr',
	'Zydus'
]

def replace_prefix_suffix(sponsor_list, word_list):
	for s_index in range(len(list(sponsor_list))):
		for word in word_list:
			sponsor = sponsor_list[s_index]
			sponsor_split = sponsor.split()
			if not sponsor_split:
				continue
			if word == sponsor_split[0].strip():
				sponsor = ' '.join(sponsor_split[1:])
			if word == sponsor_split[-1].strip():
				sponsor = ' '.join(sponsor_split[:-1])
			sponsor_list[s_index] = sponsor
	return sponsor_list

def clean_sponsors(all_sponsors):
	# make all sponsors lowercase and remove punctuation
	# replace None with empty string
	sponsor_count = 0
	for s_index, sponsor in enumerate(all_sponsors):
		if sponsor == None or sponsor == [] or sponsor == np.nan or type(sponsor) == float:
			all_sponsors[s_index] = ''
		else:
			sponsor_count += 1
	print(f'Found {sponsor_count}/{len(all_sponsors)} sponsors')
	# if it's a list, convert to string
	all_sponsors = [sponsor if type(sponsor) != list else sponsor[0] for sponsor in all_sponsors]
	all_sponsors_lower = [sponsor.lower().translate(str.maketrans('', '', string.punctuation)) for sponsor in all_sponsors]
	# compound words
	compound_words = ['and co', 'and company', 'farmaceutici spa', 'us inc', ', inc', 'ireland pharmaceuticals', 'ltd v', 
									 'branded pharm', 'pharms intl', 'an indirect whollyowned su', 'aventis', 'msd', 'sharp dohme', '414', 
									 'sharp amp dohme', 'limited ellens glen rd']
	for s_index in range(len(list(all_sponsors_lower))):
		sponsor = all_sponsors_lower[s_index]
		for word in compound_words:
			if word in sponsor:
				sponsor = sponsor.replace(word, '')
		all_sponsors_lower[s_index] = sponsor
	# company words
	company_words = ['.', 'inc', 'corp', 'corporation', 'sub', 'llc', 'limited', 'ab', 'as', 'ltd', 'lp', 'llp', 
									'allsch', 'co', 'healthcare', 'hlthcare', 'respiratory',  'synthelabo', 'prods', 'branded',
									'corp.', 'idec', 'spa', 'sb', 'us', 'usa', 'uk', 'ireland', 'hk', 'ma', 'gmbh', 'company',
									]
	all_sponsors_lower = replace_prefix_suffix(all_sponsors_lower, company_words)
	# pharma words
	pharma_words = ['pharma', 'pharm', 'pharms', 'pharm', 'pharmaceuticals', 'pharmaceutical']
	all_sponsors_lower = replace_prefix_suffix(all_sponsors_lower, pharma_words)
	# biotech words
	biotech_words =  ['biotech', 'biotechnologies', 'biologicals']
	all_sponsors_lower = replace_prefix_suffix(all_sponsors_lower, biotech_words)
	# therapies words
	therapy_words = ['theraps', 'therap']
	all_sponsors_lower = replace_prefix_suffix(all_sponsors_lower, therapy_words)
	# vaccine and diagnostics words
	vaccine_words = ['vaccines', 'vaccine', 'diagnostics', 'diagnostic', 'vaccine and diagnostics']
	all_sponsors_lower = replace_prefix_suffix(all_sponsors_lower, vaccine_words)
	# other words
	# other_words = []
	# all_sponsors_lower = replace_prefix_suffix(all_sponsors_lower, other_words)
	# remove all trailing or leading spaces
	all_sponsors_lower = [sponsor.strip() for sponsor in all_sponsors_lower]
	# capitalize first letter of each word
	all_sponsors_lower = [sponsor.title() for sponsor in all_sponsors_lower]
	# if any fda_sponsor_list are in the list, replace with the full name
	return all_sponsors_lower

def myround(x, base=5):
  return base * np.ceil(x/base)

def plot_sponsors(df, drug_name_field='drug_name', sponsor_field='sponsor', unique_drugs_only=True):
	# drop any rows that have the exact same (drug_name, sponsor) pair
	if unique_drugs_only:
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
	f, ax = plt.subplots(1, 1)
	top_sponsor_names = top_sponsors.index
	top_sponsor_counts = top_sponsors.values
	print(list(zip(top_sponsor_names, top_sponsor_counts)))
	# make bar edges black
	plt.bar(top_sponsor_names, top_sponsor_counts, edgecolor='black')
	# rotate x-axis labels
	plt.xticks(rotation=90, fontsize=8)
	# show each sponsor on x-axis
	ax.set_xlabel('Sponsor', fontsize=16, fontweight='bold')
	ax.set_ylabel('Number of Drugs', fontsize=16, fontweight='bold')
	# ax.set_title('Drug Sponsors', fontsize=20, fontweight='bold')
	# round the y tick labels
	ymax = myround(max(top_sponsor_counts))+5
	if ymax == 5:
		ymax = 10
	plt.yticks(np.arange(0, ymax, 5), fontsize=8)
	plt.tight_layout()
	# make sure nothing is cut off
	plt.subplots_adjust(bottom=0.6, top=0.9)
	return f

# make a plot with the largest number of sponsors
def rename_sponsors(df, drug_name_field='drug_name', sponsor_field='fda_2_sponsor', new_field='sponsor'):
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
		print(f'  {s_index} {drug_name:<20} {all_sponsors[s_index]} -> {final_sponsors[s_index]}')
	df[new_field] = final_sponsors
	return df