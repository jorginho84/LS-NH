"""
exec(open('cc_quality.py').read())


This file computes stats to validate model

It uses:
ate_theta.py
oprobit.py
table_aux.py
ate_emp.py
ate_cc.py
ssrs_obs.do
ssrs_sim.do
ate_cc.do
ate_emp.do

"""
from __future__ import division #omit for python 3.x
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
import matplotlib
matplotlib.use('Agg') # Force matplotlib to not use any Xwindows backend.
import matplotlib.pyplot as plt
import subprocess
sys.path.append("/home/jrodriguez/understanding_NH/codes/model/simulate_sample")
import utility as util
import gridemax
import time
import int_linear
import emax as emax
import simdata as simdata
import openpyxl
sys.path.append("/home/jrodriguez/understanding_NH/codes/model/estimation")
import estimate as estimate


np.random.seed(1)

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
X_aux=pd.read_csv('/home/jrodriguez/understanding_NH/results/Model/sample_model_v2.csv')
x_df=X_aux

#Sample size 
N=X_aux.shape[0]

#Data for wage process
#see wage_process.do to see the order of the variables.
x_w=x_df[ ['d_HS2', 'constant' ] ].values


#Data for marriage process
#Parameters: marriage. Last one is the constant
x_m=x_df[ ['age_ra', 'constant']   ].values
marriagep_betas=pd.read_csv('/home/jrodriguez/understanding_NH/results/Model/marriage_process/betas_m_v2.csv').values

#Data for fertility process (only at X0)
#Parameters: kids. last one is the constant
x_k=x_df[ ['age_ra', 'age_ra2', 'constant']   ].values
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
age_ch = np.zeros((N,nperiods))
for t in range(nperiods):
	age_ch[:,t] = agech0[:,0] + t
boo_y = age_ch[:,2]<=6

#age of child two years after baseline
agech_t2 = agech0 + 2

#Defines the instance with parameters
param0=util.Parameters(alphap,alphaf,eta,gamma1,gamma2,gamma3,
	tfp,sigma2theta,rho_theta_epsilon,wagep_betas, marriagep_betas, kidsp_betas, eitc_list,
	afdc_list,snap_list,cpi,lambdas,kappas,pafdc,psnap,mup)



###Auxiliary estimates###
moments_vector=pd.read_csv('/home/jrodriguez/understanding_NH/results/Model/aux_model/moments_vector.csv').values

#This is the var cov matrix of aux estimates
var_cov=pd.read_csv('/home/jrodriguez/understanding_NH/results/Model/aux_model/var_cov.csv').values

#The vector of aux standard errors
#Using diagonal of Var-Cov matrix of simulated moments
se_vector  = np.sqrt(np.diagonal(var_cov))


#Creating a grid for the emax computation
dict_grid=gridemax.grid()

#For montercarlo integration
D=20

#For II procedure
M=30

#How many hours is part- and full-time work
hours_p=20
hours_f=40

#Indicate if model includes a work requirement (wr), 
#and child care subsidy (cs) and a wage subsidy (ws)
wr=1
cs=1
ws=1

output_ins=estimate.Estimate(nperiods,param0,x_w,x_m,x_k,x_wmk,passign,agech0,nkids0,
	married0,D,dict_grid,M,N,moments_vector,var_cov,hours_p,hours_f,
	wr,cs,ws)

#The model (utility instance)
hours = np.zeros(N)
childcare  = np.zeros(N)

model  = util.Utility(param0,N,x_w,x_m,x_k,passign,
	nkids0,married0,hours,childcare,agech0,hours_p,hours_f,wr,cs,ws)

#Obtaining emax instances, samples, and betas for M samples
np.random.seed(1)

#list of tfp
tfp_list = [tfp,tfp*.75,tfp*.5,tfp*.25, 0]

#The sample: with young children at t=2
boo_sample = agech_t2<=6

#Producing impact on child human capital
choices_list = []
ate_hours_list = [[],[]] #[[young],[old]]

for k in range(len(tfp_list)):
	param0.tfp = tfp_list[k]
	emax_instance = output_ins.emax(param0,model)
	choices = output_ins.samples(param0,emax_instance,model)
	choices_list.append(choices)

	#Treatment effects on hours
	hours = choices['hours_matrix'].copy()
	for samp in range(2): #the sample loop.
		ate_hours_list[samp].append(np.mean(np.mean(hours[(passign[:,0]==1) & (boo_sample[:,0]==samp),0,:],axis=0) - np.mean(hours[(passign[:,0]==0) & (boo_sample[:,0]==samp),0,:],axis=0),axis=0))



#The Graph
nper = len(ate_hours_list[0])
fig, ax=plt.subplots()
x = np.array(range(nper))
y_1 = ate_hours_list[0]
y_2 = ate_hours_list[1]
plot1=ax.plot(x,y_1,'k-',label='Old',alpha=0.9)
plot2=ax.plot(x,y_2,'k--',label='Young',alpha=0.9)
plt.setp(plot1,linewidth=3)
plt.setp(plot2,linewidth=3)
ax.set_ylabel(r'Hours worked', fontsize=14)
ax.set_xlabel(r'Child care quality', fontsize=14)
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.yaxis.set_ticks_position('left')
ax.xaxis.set_ticks_position('bottom')
ax.legend(['Old','Young'])
ax.set_xticks(x)
ax.set_xticklabels([r'$\gamma_1$', r'$\gamma_1\times.75$', r'$\gamma_1\times.50$', r'$\gamma_1\times.25$', r'$\gamma_1\times 0$' ])
plt.show()
fig.savefig('/home/jrodriguez/understanding_NH/results/Model/experiments/quality/cc_quality.pdf', format='pdf')
plt.close()


