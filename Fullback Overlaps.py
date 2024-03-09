#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb  2 13:49:30 2024

@author: gavin
"""

# from mplsoccer.pitch import Pitch
import pandas as pd
import numpy as np

# from matplotlib import animation
# from matplotlib import pyplot as plt

df = pd.read_csv("game_id_2261066.csv")

#create columns 'distance_to_ball', 'closest_player_distance', 'closest_player'
def euclidean_distance(x1, y1, x2, y2):
    return np.sqrt((x1 - x2)**2 + (y1 - y2)**2)

#apply euclidean_distance and find player's distance to ball
df['distance_to_ball'] = euclidean_distance(df['x'], df['y'], df['ball_x'], df['ball_y'])

#create pivot tables through grouping to find the closest player, his distance from the ball, and his team
def closest_player_info(group):
    # Drop rows with NaN values in 'distance_to_ball' and 'team'
    group = group.dropna(subset=['distance_to_ball', 'team_id'])

    if not group.empty:
        # Calculate the minimum distance and retrieve the corresponding 'player_id' and 'team'
        min_distance_index = group['distance_to_ball'].idxmin()
        closest_player_id = group.loc[min_distance_index, 'player_id']
        closest_player_team = group.loc[min_distance_index, 'team_id']
        return pd.Series({
            'distance_to_ball': group['distance_to_ball'].min(),
            'player_id': closest_player_id,
            'team_of_closest_player': closest_player_team
        })
    else:
        # Return NaN if the group is empty after dropping NaN values
        return pd.Series({
            'distance_to_ball': np.nan,
            'player_id': np.nan,
            'team_of_closest_player': np.nan
        })


#pivot table!!
pivot_table_result = df.groupby('frame_idx').apply(closest_player_info)
pivot_table_result

#merge pivot table with og df, place closest player and his distance in rightmost columns
df = pd.merge(df, pivot_table_result, left_on='frame_idx', right_index=True, how='left')

#just rename df
df = df.rename(columns={'distance_to_ball_x':'distance_to_ball',
                        'distance_to_ball_y':'closest_player_distance',
                        'player_id_y':'closest_player',
                        'player_id_x':'player_id'})

df['starting_ball_distance_to_goal']=1000
df['min_ball_distance_to_goal']=1000
df['player_overlapped'] = 0


#let's generalize!
def get_possible_overlaps(half, player, attacking):
    # Inputs: half (int)
    #       player id (int)
    #       Attacking (int)
    #           = 1 if right
    #           = -1 if left
    
    # filter df for player, half, and when they are running
    df_highspeed = df[(df['period_id']==half) & (df['player_id']==player) & (df['speed']>3.8)].copy()
    
    # calculate forward and backward frame differences
    df_highspeed['difference'] = df_highspeed['frame_idx'].diff()
    df_highspeed['rev_difference'] = df_highspeed['frame_idx'] - df_highspeed['frame_idx'].shift(-1)
    
    # calculate x and y difference between ball and player
    # x: + means player --> ball --> goal [player is behind the ball]
    # x: - means ball --> player --> goal [player is in front of the ball]
    # y: + means player --> ball --> goal [player is towards touchline]
    # y: - means ball --> player --> goal [player is inside of the ball]
    
    df_highspeed['ball_y_player_diff'] = (((df_highspeed['y']>0)*2)-1)*( # = 1 if positive, -1 if negative
                                            df_highspeed['y']-df_highspeed['ball_y'])
    # + if run is towards goal, - if away
    df_highspeed['ball_x_player_diff'] = attacking * (df_highspeed['ball_x']-df_highspeed['x'])
    #make this so that it's talking about towards goal
    
    # get successive runs (start and endpoint, sometimes with points in between)
    df_runs = df_highspeed[(df_highspeed['difference']!=1) | (df_highspeed['rev_difference']!=-1)].copy()
    df_runs['x_diff'] = df_runs['x'].diff() * attacking
    
    # make sure to generalize for side of field
    # gives boolean true if runs are towards goal
    df_runs['critical_point'] = (df_runs['rev_difference']<-1) & (df_runs['x_diff']>10)
    
    # drop middle values that muddy the outcome
    df_runs = df_runs[(df_runs['rev_difference']<-25) |
                      (df_runs['difference']>25) |
                      (df_runs['critical_point']==True) |
                      (pd.isna(df_runs['x_diff']))]
    
    # Maps critical point = True --> 2, row directly before that's critical point --> 1
    # Label == 1 --> start of run; Label == 2 --> end of run
    df_runs['Label'] = 0
    df_runs.loc[df_runs['critical_point'], 'Label'] = 2
    df_runs.loc[df_runs['critical_point'].shift(-1, fill_value=False), 'Label'] = 1
    
    #merge highspeed and runs to get start and end of runs with rest of the cols
    df_possible_overlaps = pd.merge(df_highspeed, df_runs[['frame_idx', 'Label']], on='frame_idx', how='left')
    return df_possible_overlaps

#This df_overlapping is what is used to finally get the overlapping runs
#We don't know who is overlapping yet and when before this function

def get_overlaps(df_in, attacking):
    # Inputs: df_in (pandas dataframe)
    #               df_possible_overlaps output from get_possible_overlaps
    #       attacking (int)
    #           = 1 if right
    #           = -1 if left
    
    
    #local function, retrieves ball minimum distance to goal over the next 20 seconds
    def get_min_dist_to_goal(time_in, player, attacking):
        
        df_temp = df[(df['player_id'] == player) &
                     (df['game_clock'] >= time_in) &
                     (df['game_clock'] <= time_in + 25)].copy()
        df_temp['dist_to_goal'] = euclidean_distance(df_temp['ball_x'],
                                                     df_temp['ball_y'],
                                                     attacking*52.5, 0)
        return df_temp['dist_to_goal'].min()
        
    
    df_in['overlapping'] = 0 #1 if true, 0 if false
    df_in['overlapping_start'] = 0 #1 if true, 0 if false
    
    
    
    on_the_run = False
    overlapping = False
    for index, row in df_in.iterrows():
        if row['Label'] == 2: #if it is the end of the run
            if overlapping:
                
                df_in.loc[index, 'overlapping'] = 1
                df_in.loc[index, 'overlapping_start'] = time_stamp
                df_in.loc[index, 'min_ball_distance_to_goal'] = get_min_dist_to_goal(time_stamp, row['player_id'], attacking)
                df_in.loc[index, 'starting_ball_distance_to_goal'] = start_ball_distance
                df_in.loc[index, 'player_overlapped'] = playeroverlapped
                
            overlapping = False
            on_the_run = False
        elif row['Label']==1: #if it is the start of the run
            time_stamp = row['game_clock']
            start_ball_distance = euclidean_distance(row['ball_x'],
                                                         row['ball_y'],
                                                         attacking*52.5, 0)
            
            on_the_run = True
        elif on_the_run & ~ overlapping: #if the run is happening
            if (((row['ball_x_player_diff']>0) & (row['ball_x_player_diff']<5)) &
                ((row['ball_y_player_diff']>1) & (row['ball_y_player_diff']<12)) &
                (row['team_id']==row['team_of_closest_player']) &
                (abs(row['y'])>10) &
                (row['closest_player']!=row['player_id']) &
                (row['closest_player_distance']<1.5)): #!!!watch out for danger of overtraining
                playeroverlapped = row['closest_player']
                overlapping = True #eventually change to needing to be outside of the goal
                
        
    # df_in[df_in['overlapping']==1]['game_clock']/60
    return df_in

# get_overlap_stats()

# Repeatedly two main above functions to count all overlaps
def get_all_overlaps(player, team):
    # Input: player_id (int_)
    #        team_id (string_)
    direction = -1 # direction of first half for OCSC
    if team == 'Team1':
        direction = 1
    
    df_player = get_possible_overlaps(1, player, direction)
    df_player_overlaps = get_overlaps(df_player, direction)
    
    df_player_overlaps = df_player_overlaps[df_player_overlaps['overlapping']==1].copy()
    df_player_overlaps['time_stamp'] = pd.to_timedelta(df_player_overlaps['overlapping_start'], unit='s').dt.total_seconds() / 60
    
    df_player2 = get_possible_overlaps(2, player, -1*direction)
    df_player2_overlaps = get_overlaps(df_player2, direction)
    df_player2_overlaps = df_player2_overlaps[df_player2_overlaps['overlapping']==1].copy()
    df_player2_overlaps['time_stamp'] = pd.to_timedelta(df_player2_overlaps['overlapping_start'] + 60*45, unit='s').dt.total_seconds() / 60
    
    
    df_out = pd.concat([df_player_overlaps,
                       df_player2_overlaps],
                       ignore_index = True)
    df_out['time_stamp'] = df_out['time_stamp'].round(2)
    
    
    
    return df_out

df_fb1 = get_all_overlaps(443002, 'Team2') #fullback 1 on Team2

df_fb2 = get_all_overlaps(246099, 'Team2') #fullback 2 on Team2

df_fb3 = get_all_overlaps(427869, 'Team1') #fullback 3 on Team1
    
df_fb4 = get_all_overlaps(119644, 'Team1') #fullback 4 on Team1

df_fb5 = get_all_overlaps(227733, 'Team2') #fullback 5 on Team 2 (subsitute)

df_all_overlaps = pd.concat([df_fb1, df_fb2, df_fb3, df_fb4,
                             df_fb5], ignore_index = True)

df_to_print = df_all_overlaps[['time_stamp','player_id', 'player_overlapped', 'starting_ball_distance_to_goal', 'min_ball_distance_to_goal']].copy()

df_to_print['ball_progression_distance'] = abs(df_to_print['starting_ball_distance_to_goal']-df_to_print['min_ball_distance_to_goal'])

min_value = df_to_print['starting_ball_distance_to_goal'].min()
max_value = df_to_print['starting_ball_distance_to_goal'].max()
df_to_print['normalized_start'] = (df_to_print['starting_ball_distance_to_goal'] - min_value) / (max_value - min_value)

min_value = df_to_print['min_ball_distance_to_goal'].min()
max_value = df_to_print['min_ball_distance_to_goal'].max()
df_to_print['normalized_min'] = ((df_to_print['min_ball_distance_to_goal'] - min_value) / (max_value - min_value)-1)*-1

min_value = df_to_print['ball_progression_distance'].min()
max_value = df_to_print['ball_progression_distance'].max()
df_to_print['normalized_ball_progression_distance'] = (df_to_print['ball_progression_distance'] - min_value) / (max_value - min_value)

df_to_print['starting_ball_distance_to_goal'] = df_to_print['starting_ball_distance_to_goal'].round(2)
df_to_print['min_ball_distance_to_goal'] = df_to_print['min_ball_distance_to_goal'].round(2)
df_to_print['ball_progression_distance'] = df_to_print['ball_progression_distance'].round(2)

df_to_print['value'] = (df_to_print['normalized_ball_progression_distance']+df_to_print['normalized_min'])/2

df_to_print = df_to_print[['time_stamp','player_id', 'player_overlapped', 'starting_ball_distance_to_goal', 'min_ball_distance_to_goal', 'ball_progression_distance', 'value']].copy()
df_to_print = df_to_print.sort_values(by='value', ascending=False)
# df_to_print

#df_to_print.to_csv(, index = False) * redacted
