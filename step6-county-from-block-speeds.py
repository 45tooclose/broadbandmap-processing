#############################
# created by Ahmad Aburizaiza
#############################
import pandas as pd
import json
import time
import os

# the strat variable is used to calculate the script running time
starting_time = time.clock()

####################################################################
# step 0: load config.json variables and check if input files exists
####################################################################
with open('./parent_config.json') as f:
    conf = json.load(f)

input_csvs_path = conf['input_csvs_path']
temp_csvs_path = conf['temp_csvs_path']
output_csvs_path = conf['output_csvs_path']

input_block_numprov_null_csvs = conf['input_block_numprov_null_csvs']
input_block_numprov_zeros_csvs = conf['input_block_numprov_zeros_csvs']
cols_lists_blocks = conf['cols_lists_blocks']
cols_dtypes_int8_blocks = conf['cols_dtypes_int8_blocks']


input_blockmaster_csv = conf['input_csvs_path']+conf['input_blockmaster_csv']

if os.path.isfile(input_blockmaster_csv) == False:
    print("Error: %s file not found" % input_blockmaster_csv)
    exit()

for csv in input_block_numprov_zeros_csvs:
    if os.path.isfile(temp_csvs_path+'block_numprov_with0/'+csv) == False:
        print("Error: %s file not found" % csv)
        exit()

temp_block_numprov_pop_csvs_c = conf['temp_block_numprov_pop_csvs_c']

output_county_numprov_csvs = conf['output_county_numprov_csvs']

cols_dtypes_category_blocks = conf['cols_dtypes_category_blocks']
cols_lists_blocks = conf['cols_lists_blocks']

cols_lists_counties = conf['cols_lists_counties']
cols_dtypes_counties = conf['cols_dtypes_counties']
########################################
# step 1: create temp_county_pop csv file
########################################
# create the blockmaster dataframe
blockm_df = pd.read_csv(input_blockmaster_csv,usecols=['geoid10','pop'],dtype={'geoid10':'object','pop':'float'})
# creating the series from the groupy object
blockm_df_gb = blockm_df.groupby(blockm_df['geoid10'].str[0:5])['pop'].sum()
# convert series to dataframe to save the column names !!!
temp_county_pop_df = blockm_df_gb.to_frame()
# rename the first column (the index) to county_id
temp_county_pop_df.index.name = 'county_id'
# filter out populations of 0s
#temp_county_pop_df = temp_county_pop_df[temp_county_pop_df['pop'] > 0.0]
# free up memory
#temp_county_pop_df needed for following steps
blockm_df_gb = None

################################################
# step 2: create temp_block_numprov_pop csv file
################################################
accumulated_cols_list = []
# create the block_numprov dataframes
for cl_i, cl_v in enumerate(cols_lists_blocks):
    for clv_i,clv_v in enumerate(cl_v):
        block_numprov = pd.read_csv(temp_csvs_path+'block_numprov_with0/'+input_block_numprov_zeros_csvs[cl_i],usecols=clv_v,dtype=cols_dtypes_category_blocks[cl_i][clv_i])
        accumulated_cols_list.append(block_numprov)
    # create the temp_block_numprov_pop dataframe for each of the seven files using
    # the concat method to concatenate block_numprov and pop sereis from the us_df
    accumulated_cols_list.append(blockm_df['pop'])
    temp_block_numprov_pop = pd.concat(accumulated_cols_list,axis=1)
    # free up memory
    # temp_block_numprov_pop needed for following steps
    block_numprov = None
    accumulated_cols_list = []
    # update the temp_block_numprov_pop by filtering out pop of 0s
    #temp_block_numprov_pop = temp_block_numprov_pop[temp_block_numprov_pop['pop'] > 0.0]
    # repale the block_fips column with county_id column and set it as index
    temp_block_numprov_pop['geoid10'] = temp_block_numprov_pop.geoid10.str[0:5]
    temp_block_numprov_pop.rename(columns={'geoid10': 'county_id'}, inplace=True)
    temp_block_numprov_pop.set_index('county_id', inplace=True)
    # add a county_pop column
    temp_block_numprov_pop['county_pop'] = temp_county_pop_df
    # reseting the index so we can have county_id as a regular column to groupby later
    temp_block_numprov_pop.reset_index(inplace=True)
    # saving a file for each speed in the temp_block_numprov_pop_csvs_c
    temp_block_numprov_pop.to_csv(temp_csvs_path+temp_block_numprov_pop_csvs_c[cl_i],index=False)
    print(str(temp_block_numprov_pop_csvs_c[cl_i]) + ' temp file is created')

##########################
# step 3: analyze the data
##########################
# create the block_numprov dataframes
for cl_i, cl_v in enumerate(cols_lists_counties):
    groupby_series_list = []
    for clv_i,clv_v in enumerate(cl_v):
        temp_block_numprov_pop = pd.read_csv(temp_csvs_path+temp_block_numprov_pop_csvs_c[cl_i],usecols=clv_v,dtype=cols_dtypes_counties[cl_i][clv_i])
        # loop through 21 columns for each speed file
        # each file is divided into three sets of 21 columns of speeds
        # plus county_id, pop, and county_pop
        for c in temp_block_numprov_pop.columns:
            if c in ['county_id','pop','county_pop']:
                continue
            temp_block_numprov_pop['temp'] = temp_block_numprov_pop[c].astype('int')
            temp_block_numprov_pop['temp'] = temp_block_numprov_pop['temp']*temp_block_numprov_pop['pop']
            temp_sum = temp_block_numprov_pop.groupby(temp_block_numprov_pop['county_id'])['temp'].sum()
            temp_pop_county = temp_block_numprov_pop.groupby(temp_block_numprov_pop['county_id'])['county_pop'].mean()
            boolean_temp_pop_county = temp_pop_county > 0.0

            # make the calculation according to the original SQL where clause of Rosenberg's code
            for i, v in temp_sum.iteritems():
                if temp_pop_county.loc[i] == 0:
                    continue
                else:
                    temp_sum.loc[i] = round(temp_sum.loc[i] / temp_pop_county.loc[i],1)
            
            temp_sum.rename(c, inplace=True)
            groupby_series_list.append(temp_sum)

    # concatenate the big series list as a pandas dataframe
    groupby_series_list.append(temp_pop_county)
    boolean_temp_pop_county.rename('is_populated', inplace=True)
    groupby_series_list.append(boolean_temp_pop_county)
    result = pd.concat(groupby_series_list, axis=1)
    # replace nulls with 0s
    result.fillna(0, inplace=True)
    # rename the index title from block_fips to county_id
    result.index.rename('county_id', inplace=True)
    # remove the county_pop column before saving
    result.drop('county_pop', axis=1, inplace=True)
    # save each output speed csv file in the output_county_numprov_csvs
    result.to_csv(temp_csvs_path+'county_numprov/'+output_county_numprov_csvs[cl_i])
    print(str(output_county_numprov_csvs[cl_i]) + ' file created')

###############################
# step 4: delete the temp files
###############################
for csv in temp_block_numprov_pop_csvs_c:
    if os.path.isfile(temp_csvs_path+csv):
        os.remove(temp_csvs_path+csv)
    else:
        print("Error: %s file not found" % csv)

##############################################
# outputing the time it took the script to run
##############################################
running_time = time.clock() - starting_time
print('step6_county_from_block_speeds.py took: '+str(round(running_time/60,2))+' minutes.')