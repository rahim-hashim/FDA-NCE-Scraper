import os
import pickle
import pandas as pd

def get_size(filename):
	# get the size of the dataframe
	size = os.path.getsize(filename)
	print(f'{filename} file size: {size/1e6} MB')

# pickle the dataframes
def pickle_dataframe(df, filename):
	with open(filename, 'wb') as f:
		pickle.dump(df, f)
		# get the size of the dataframe
		get_size(filename)

# unpickle dataframes
def unpickle_dataframes(database_folder='databases'):
	pickled_files = [file for file in os.listdir(database_folder) if file.endswith('.pkl')]
	print(f'Number of pickled files found: {len(pickled_files)}')
	dataframes = {}
	for file in sorted(pickled_files):
		df_name = file.split('.')[0]
		dataframes[df_name] = pd.read_pickle(f'{database_folder}/{file}')
		print(f'  {df_name} dataframe shape: {dataframes[df_name].shape}')
	return dataframes

def read_excel(save_dir ='', file_name='fda_nce.xlsx'):
	file_path = os.path.join(save_dir, file_name)
	df = pd.read_excel(file_path)
	return df