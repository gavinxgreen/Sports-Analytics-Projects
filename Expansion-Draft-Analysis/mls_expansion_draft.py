#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 25 17:04:31 2024

@author: gavin
"""
import pandas as pd
from sklearn.metrics import r2_score
import matplotlib.pyplot as plt
from scipy import stats


df = pd.read_csv("/Users/gavin/Documents/All Data Projects/MLS data/mls_expansion_data.csv")

grouped_data = df.groupby('MLS Team')[['Minutes Played', 'Money']].sum()

grouped_data['Total Points'] = {'Atlanta United FC': 55,
                                'Minnesota United FC': 36,
                                'Los Angeles FC': 57,
                                'FC Cincinnati': 24,
                                'Nashville SC': 32,
                                'Inter Miami CF': 24,
                                'Austin FC': 31,
                                'Charlotte FC': 42,
                                'St. Louis City SC': 56}

# Adjusting 'Minutes Played' and 'Total Points' for Nashville SC and Inter Miami CF
grouped_data.loc[['Nashville SC', 'Inter Miami CF'], 'Minutes Played'] *= (34 / 23)
grouped_data.loc[['Nashville SC', 'Inter Miami CF'], 'Total Points'] *= (34 / 23)

team_abbreviations = {
    'Nashville SC': 'Nashville',
    'Inter Miami CF': 'Miami',
    'Austin FC': 'Austin',
    'Charlotte FC': 'Charlotte',
    'Minnesota United FC': 'MNUFC',
    'St. Louis City SC': 'STL',
    'Los Angeles FC': 'LAFC',
    'Atlanta United FC': 'ATL',
    'FC Cincinnati': 'Cinci'
    # Add more teams as needed
}

def plot_adj(percentage, outliers):
    #Input: percentage (How much money plays a part in the overall equation)
    #Input: outlier (boolean of do we include outliers LAFC, STL, ATL)
    if outliers:
        minutes_played = grouped_data['Minutes Played']
        money = grouped_data['Money']
        total_points = grouped_data['Total Points']
    else:
        temp_data = grouped_data.drop(['Atlanta United FC', 'Los Angeles FC', 'St. Louis City SC'])
        minutes_played = temp_data['Minutes Played']
        money = temp_data['Money']
        total_points = temp_data['Total Points']
    
    
    minutes_adjusted = minutes_played+money*percentage
    slope, intercept, r_value, p_value, std_err = stats.linregress(minutes_adjusted, total_points)
    print(slope)
    
    fit_coeffs = np.polyfit(minutes_adjusted, total_points, 1)  # Linear fit (1st degree polynomial)
    fit_line = np.polyval(fit_coeffs, minutes_adjusted)
    mse = mean_squared_error(total_points, fit_line)

    # Calculate R^2 value
    r_squared = r2_score(total_points, fit_line)

    # Scatter plot
    plt.figure(figsize=(10, 6))
    plt.scatter(minutes_adjusted, total_points, alpha=0.5, label='Data')
    plt.plot(minutes_adjusted, fit_line, color='red', label='Line of Best Fit')
    if outliers:
        plt.title('Minutes Played from Expansion Draft Players vs. Points')
    else:
        plt.title('Minutes Played from Expansion Draft Players vs. Points (w/o Outliers)')
    
    if percentage == 0:
        plt.xlabel('Total Minutes Played')
    else:
        plt.xlabel('Total Minutes Played (adjusted by ' + str(percentage) + ')')
    
    plt.ylabel('Total Points')
    plt.grid(True)
    plt.legend()
    
    for i, team in enumerate(minutes_played.index):
        abbreviation = team_abbreviations.get(team, team)  # Get abbreviation or use full name if not found
        plt.text(minutes_adjusted[i], total_points[i], abbreviation, fontsize=10, ha='right', va='bottom')
    
    plt.text(0.85, 0.64, f'R^2 = {r_squared:.2f}', transform=plt.gca().transAxes)
    plt.text(0.85, 0.6, f'MSE = {mse:.2f}', transform=plt.gca().transAxes)
    plt.text(0.85, 0.56, f'p-value = {p_value:.4f}', transform=plt.gca().transAxes)  # Add p-value
    
    plt.show()
    

def execute_calls():
    plot_adj(0, True)
    plot_adj(0, False)
    plot_adj(0.002, True)
    plot_adj(0.002, False)



# # Fit a polynomial to the data
# fit_coeffs = np.polyfit(minutes_played, total_points, 1)  # Linear fit (1st degree polynomial)
# fit_line = np.polyval(fit_coeffs, minutes_played)

# # Calculate R^2 value
# r_squared = r2_score(total_points, fit_line)

# # Scatter plot
# plt.figure(figsize=(10, 6))
# plt.scatter(minutes_played, total_points, alpha=0.5, label='Data')
# plt.plot(minutes_played, fit_line, color='red', label='Line of Best Fit')
# plt.title('Minutes Played from Expansion Draft Players vs. Points')
# plt.xlabel('Total Minutes Played')
# plt.ylabel('Total Points')
# plt.grid(True)
# plt.legend()

# # Add the R^2 value to the plot
# # Add the R^2 value to the plot in the upper right corner
# plt.text(0.85, 0.65, f'R^2 = {r_squared:.2f}', transform=plt.gca().transAxes)
# plt.show()
