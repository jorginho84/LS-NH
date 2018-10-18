"""
exec(open('master_dcheck.py').read())

This file computes Emax 1 for a grid of D values

"""

import numpy as np
import pandas as pd
import pickle
import itertools
import sys, os
from scipy import stats
#from scipy.optimize import minimize
from scipy.optimize import fmin_bfgs
from joblib import Parallel, delayed
from scipy import interpolate
import matplotlib.pyplot as plt
#sys.path.append("C:\\Users\\Jorge\\Dropbox\\Chicago\\Research\\Human capital and the household\]codes\\model")
sys.path.append("/home/jrodriguez/understanding_NH/codes/model/simulate_sample")
import utility as util
import gridemax
import time
import int_linear
import emax as emax
import simdata as simdata

np.random.seed(1);
#Sample size
#N=315

betas_nelder=np.load('/home/jrodriguez/understanding_NH/results/Model/betas_modelv24.npy')

#Number of periods where all children are less than or equal to 18
nperiods = 8

#Utility function
eta = betas_nelder[0]
alphap = betas_nelder[1]
alphaf = betas_nelder[2]

#wage process
wagep_betas=np.array([betas_nelder[3],betas_nelder[4],betas_nelder[5],
	betas_nelder[6],betas_nelder[7]]).reshape((5,1))


#Production function [young,old]
gamma1= betas_nelder[8]
gamma2= betas_nelder[9]
gamma3= betas_nelder[10]
tfp=betas_nelder[11]
sigma2theta=1

kappas=[[betas_nelder[12],betas_nelder[13],betas_nelder[14],betas_nelder[15]],
[betas_nelder[16],betas_nelder[17],betas_nelder[18],betas_nelder[19]]]

#initial theta
rho_theta_epsilon = betas_nelder[20]

#First measure is normalized. starting arbitrary values
#All factor loadings are normalized
lambdas=[1,1]

#Child care price
mup = 0.57*0 + (1-0.57)*750

#Probability of afdc takeup
pafdc=.60

#Probability of snap takeup
psnap=.70

#Data
#X_aux=pd.read_csv('C:\\Users\\Jorge\\Dropbox\\Chicago\\Research\\Human capital and the household\\results\\Model\\Xs.csv')
X_aux=pd.read_csv('/home/jrodriguez/understanding_NH/results/Model/sample_model_v2.csv')
x_df=X_aux

#Sample size 
N=X_aux.shape[0]

#Data for wage process
#Parameters: wage function.the last one is sigma. 
#see wage_process.do to see the order of the variables.
x_w=x_df[ ['d_HS2', 'constant' ] ].values

#Data for marriage process 
#Parameters: marriage. Last one is the constant
x_m=x_df[ ['age_ra', 'constant']   ].values
marriagep_betas=pd.read_csv('/home/jrodriguez/understanding_NH/results/Model/marriage_process/betas_m_v2.csv').values

#Data for fertility process (only at X0)
#Parameters: kids. last one is the constant
x_k=x_df[ ['age_ra', 'constant']   ].values
kidsp_betas=pd.read_csv('/home/jrodriguez/understanding_NH/results/Model/kids_process/betas_kids_v2.csv').values

#Minimum set of x's (for interpolation)
x_wmk=x_df[  ['age_ra','age_ra2', 'd_HS2', 'constant'] ].values

#Data for treatment status
passign=x_df[ ['d_RA']   ].values


#The EITC parameters
eitc_list = pickle.load( open( '/home/jrodriguez/understanding_NH/codes/model/simulate_sample/eitc_list.p', 'rb' ) )

#The AFDC parameters
afdc_list = pickle.load( open( '/home/jrodriguez/understanding_NH/codes/model/simulate_sample/afdc_list.p', 'rb' ) )

#The SNAP parameters
snap_list = pickle.load( open( '/home/jrodriguez/understanding_NH/codes/model/simulate_sample/snap_list.p', 'rb' ) )

#CPI index
cpi =  pickle.load( open( '/home/jrodriguez/understanding_NH/codes/model/simulate_sample/cpi.p', 'rb' ) )

#Here: the estimates from the auxiliary model
###
###

#Assuming random start
#theta0=np.exp(np.random.randn(N))


#number of kids at baseline
nkids0=x_df[ ['nkids_baseline']   ].values

#marital status at baseline
married0=x_df[ ['d_marital_2']   ].values

#age of child at baseline
agech0=x_df[['age_t0']].values

#Defines the instance with parameters
param=util.Parameters(alphap,alphaf,eta,gamma1,gamma2,gamma3,
	tfp,sigma2theta, rho_theta_epsilon,wagep_betas, marriagep_betas, kidsp_betas, eitc_list,
	afdc_list,snap_list,cpi,lambdas,kappas,pafdc,psnap,mup)


#Creating a grid for the emax computation
dict_grid=gridemax.grid()

#How many hours is part- and full-time work
hours_p=15
hours_f=40

hours = np.zeros(N)
childcare = np.zeros(N)
wr,cs,ws=1,1,1

#This is an arbitrary initialization of Utility class
model = util.Utility(param,N,x_w,x_m,x_k,passign,nkids0,married0,hours,childcare,
	agech0,hours_p,hours_f,wr,cs,ws)

theta0 = np.exp(model.shocks_init()['epsilon_theta0'])
epsilon0 = model.shocks_init()['epsilon0']

######################################################################

#data for initial state values
data_int_ex=np.concatenate(( np.reshape(np.log(theta0),(N,1)),nkids0,married0,
	np.reshape(np.square(np.log(theta0)),(N,1)),passign,x_wmk ), axis=1)


data_int_ex=np.concatenate(( np.reshape(np.log(theta0),(N,1)), 
	np.reshape(nkids0,(N,1)),np.reshape(married0,(N,1)),
	np.reshape(np.square(np.log(theta0)),(N,1)),
	np.reshape(passign,(N,1)), 
	np.reshape(epsilon0,(N,1)),
	np.reshape(np.square(epsilon0),(N,1)),
	x_wmk ), axis=1)

J = 6

D = [50,45,40,35,30,25,20,15,10,5]

#average emax for the grid of D (for N individuals)
av_emax = []
se_emax = []

for k in range(len(D)):
	
	#The emax interpolated values
	np.random.seed(2)
	emax_function_in=emax.Emaxt(param,D[k],dict_grid,hours_p,hours_f,wr,cs,ws,model)
	emax_dic = emax_function_in.recursive()
	

	emax_t1_int = np.zeros((N,J))
	for j in range(J):
		emax_int_ins = emax_dic[4][0]['emax1'][j]
		emax_betas = emax_int_ins.betas()
		emax_t1_int[:,j] = emax_int_ins.int_values(data_int_ex,emax_betas)

	#av individual emax and se
	av_emax.append(np.mean(emax_t1_int,axis=0))
	se_emax.append(np.std(emax_t1_int,axis=0))



av_emax_choice0 = []
sd_emax_choice0 = []

for k in range(len(D)):
	av_emax_choice0.append(av_emax[k][0])
	sd_emax_choice0.append(se_emax[k][0])

fig, ax=plt.subplots()
plot1=ax.plot(D,av_emax_choice0,'k',alpha=0.9)
ax.set_ylabel(r'Emax average', fontsize=12)
ax.set_xlabel(r'Number of shocks for Montecarlo integration', fontsize=12)
ax.set_ylim(0,0.16)
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.yaxis.set_ticks_position('left')
ax.xaxis.set_ticks_position('bottom')
plt.yticks(fontsize=11)
plt.xticks(fontsize=11)
ax.legend(loc=4,fontsize = 11)
plt.show()
fig.savefig('/home/jrodriguez/understanding_NH/results/Model/checks/av_emax_choice0.pdf', format='pdf')
plt.close()

fig, ax=plt.subplots()
plot1=ax.plot(D,sd_emax_choice0,'k',alpha=0.9)
ax.set_ylabel(r'Emax SD', fontsize=12)
ax.set_xlabel(r'Number of shocks for Montecarlo integration', fontsize=12)
ax.set_ylim(0,0.16)
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.yaxis.set_ticks_position('left')
ax.xaxis.set_ticks_position('bottom')
plt.yticks(fontsize=11)
plt.xticks(fontsize=11)
ax.legend(loc=4,fontsize = 11)
plt.show()
fig.savefig('/home/jrodriguez/understanding_NH/results/Model/checks/sd_emax_choice0.pdf', format='pdf')
plt.close()