"""
exec(open('policies_mech.py').read())

This file plots ATE theta of different New Hope policies

"""

#from __future__ import division #omit for python 3.x
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
#matplotlib.use('Agg') # Force matplotlib to not use any Xwindows backend.
import matplotlib.pyplot as plt
sys.path.append("/home/jrodriguez/understanding_NH/codes/model/simulate_sample")
import utility as util
import gridemax
import time
import int_linear
import emax as emax
import simdata as simdata
sys.path.append("/home/jrodriguez/understanding_NH/codes/model/estimation")
import estimate as estimate
sys.path.append("/home/jrodriguez/understanding_NH/codes/model/experiments/NH")
from util2 import Prod2



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

#Defines the instance with parameters
param0=util.Parameters(alphap,alphaf,eta,gamma1,gamma2,gamma3,
	tfp,sigma2theta, rho_theta_epsilon,wagep_betas, marriagep_betas, kidsp_betas, eitc_list,
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

#Number of samples to produce
M=30

#How many hours is part- and full-time work
hours_p=20
hours_f=40

#################################################################################
###Obtaining counterfactuals

#This is the list of models to compute [wr,cs,ws]. This order is fixed
models_list = [[1,0,1],[1,1,1]]
models_names = ['WR_WS','WR_CS_WS']

###Computing counterfactuals
ate_hours_1_list = []
ate_hours_2_list = []
ate_emp_list = []
sd_matrix_list = []
choices_list = []


#Samples
age_child = np.zeros((agech0[:,0].shape[0],nperiods))
for x in range(nperiods):
	age_child[:,x]=agech0[:,0] + x

boo_sample = (age_child[:,2]<=6)

for j in range(len(models_list)): #the counterfactual loop
	output_ins=estimate.Estimate(nperiods,param0,x_w,x_m,x_k,x_wmk,passign,agech0,nkids0,
		married0,D,dict_grid,M,N,moments_vector,var_cov,hours_p,hours_f,
		models_list[j][0],models_list[j][1],models_list[j][2])

	hours = np.zeros(N) #arbitrary to initialize model instance
	childcare  = np.zeros(N)

	#obtaining values to normalize theta
	model = util.Utility(param0,N,x_w,x_m,x_k,passign,nkids0,married0,hours,childcare,
		agech0,hours_p,hours_f,models_list[j][0],models_list[j][1],models_list[j][2])

	np.random.seed(1)
	emax_instance = output_ins.emax(param0,model)
	choices = output_ins.samples(param0,emax_instance,model)
	#The E[Log] of consumption, leisure, and child care to normalize E[log theta]=0
	ec = np.mean(np.mean(np.log(choices['consumption_matrix']),axis=2),axis=0)
	hours_m = choices['hours_matrix']
	boo_p = hours_m == hours_p
	boo_f = hours_m == hours_f
	boo_u = hours_m == 0
	cc = choices['choice_matrix']>2
	ecc = np.mean(np.mean(cc,axis=2),axis=0)
	
	tch = np.zeros((N,nperiods,M))
	for t in range(nperiods):
		tch[age_ch[:,t]<=5,t,:] = cc[age_ch[:,t]<=5,t,:]*(168 - hours_f) + (1-cc[age_ch[:,t]<=5,t,:])*(168 - hours_m[age_ch[:,t]<=5,t,:])
		tch[age_ch[:,t]>5,t,:] = 133 - hours_m[age_ch[:,t]>5,t,:] 
	
	el = np.mean(np.mean(np.log(tch),axis=2),axis=0)
	e_age = np.mean(age_ch<=5,axis=0)
	
	np.save("/home/jrodriguez/understanding_NH/results/Model/experiments/NH/el.npy",el)
	np.save("/home/jrodriguez/understanding_NH/results/Model/experiments/NH/ec.npy",ec)
	np.save("/home/jrodriguez/understanding_NH/results/Model/experiments/NH/ecc.npy",ecc)
	np.save("/home/jrodriguez/understanding_NH/results/Model/experiments/NH/e_age.npy",e_age)
	
	#SD matrix
	ltheta = np.log(choices['theta_matrix'])
	sd_matrix = np.zeros((nperiods,M))
	for jj in range (M):
		for t in range(nperiods):
			sd_matrix[t,jj] = np.std(ltheta[:,t,jj],axis=0)
	
	sd_matrix_list.append(sd_matrix)

	#Obtaining counterfactuals with the same emax
	choices_c = {}
	models = []
	for k in range(2):
		passign_aux=k*np.ones((N,1))#everybody in treatment/control
		models.append(Prod2(param0,N,x_w,x_m,x_k,passign,
					nkids0,married0,hours,childcare,agech0,hours_p,hours_f,
					models_list[j][0],models_list[j][1],models_list[j][2]))
		output_ins.__dict__['passign'] = passign_aux
		choices_c['Choice_' + str(k)] = output_ins.samples(param0,emax_instance,models[k])

	choices_list.append(choices_c)


	

	#Generating counterfactuals numbers

	emp = []
	hours = []

	for k in range(2): #choice loop
		hours.append(choices_c['Choice_'+str(k)]['hours_matrix'])
		emp.append(choices_c['Choice_'+str(k)]['hours_matrix']>0)
	

	ate_emp = []
	ate_hours_1 = []
	ate_hours_2 = []
	boo_work = choices_c['Choice_'+str(0)]['hours_matrix'][:,0,:]>0

	for k in range(2): #sample loop
		ate_emp.append(np.mean(np.mean(emp[1][boo_sample==k,0,:],axis=0) - np.mean(emp[0][boo_sample==k,0,:],axis=0),axis=0))
		ate_hours_1.append(np.mean(np.mean(hours[1][boo_sample==k,0,:],axis=0) - np.mean(hours[0][boo_sample==k,0,:],axis=0),axis=0))

		ate_aux = np.zeros(M)
		for m in range(M): #the simulated sample loop
			ate_aux[m] = np.mean(hours[1][(boo_sample==k) & (boo_work[:,m]),0,m],axis=0) - np.mean(hours[0][(boo_sample==k) & (boo_work[:,m]),0,m],axis=0)


		ate_hours_2.append(np.mean(ate_aux,axis=0))

	ate_emp_list.append(ate_emp)
	ate_hours_1_list.append(ate_hours_1)
	ate_hours_2_list.append(ate_hours_2)







#################################################################################
#GRAPHS
alpha_plot1 = 0.8
alpha_plot2 = 0.4
bar_width = 0.4
loc_legen = 1
fontsize_axis = 15

#Impact on employment probability
fig, ax=plt.subplots()
x = np.array([1,2.5])
plot1=ax.bar(x,[ate_emp_list[1][1],ate_emp_list[0][1]],bar_width,label='Young',color='k',alpha=alpha_plot1)
plot2=ax.bar(x + [bar_width],[ate_emp_list[1][0],ate_emp_list[0][0]],bar_width,label='Old',edgecolor='k',color='k',alpha=alpha_plot2)
ax.legend(loc=loc_legen,fontsize=fontsize_axis)
ax.set_ylabel(r'Employment', fontsize=fontsize_axis)
ax.annotate(r'$\}$', xy=(x[0]+bar_width-0.2, ate_emp_list[0][1] + 0.005), xytext=(x[0]+bar_width-0.2, ate_emp_list[0][1] + 0.004),size = 60)
ax.annotate( '{:04.3f}'.format(ate_emp_list[1][1]-ate_emp_list[1][0]), xy=(x[0]+bar_width+0.1, ate_emp_list[0][1]), xytext=(x[0]+bar_width+0.1, ate_emp_list[0][1]+0.01),size = 16)
ax.annotate(r'$\}$', xy=(x[1]+bar_width-0.2, ate_emp_list[0][0] + 0.005), xytext=(x[1]+bar_width-0.2, ate_emp_list[0][0] + 0.004),size = 30)
ax.annotate( '{:04.3f}'.format(ate_emp_list[0][1]-ate_emp_list[0][0]), xy=(x[1]+bar_width+0.1, ate_emp_list[0][0]), xytext=(x[1]+bar_width+0.01, ate_emp_list[0][0]+0.005),size = 16)
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.yaxis.set_ticks_position('left')
ax.xaxis.set_ticks_position('bottom')
ax.set_xticklabels(['Full treatment', 'No CC subsidy'])
ax.set_xticks([x[0]+(bar_width)/2,x[1]+(bar_width)/2])
ax.legend(loc=loc_legen,fontsize=15)
plt.show()
fig.savefig('/home/jrodriguez/understanding_NH/results/Model/experiments/NH/ate_emp.pdf', format='pdf')
plt.close()


#Impact on hours
fig, ax=plt.subplots()
x = np.array([1,2.5])
plot1=ax.bar(x,[ate_hours_1_list[1][1],ate_hours_1_list[0][1]],bar_width,label='Young',color='k',alpha=alpha_plot1)
plot2=ax.bar(x + [bar_width],[ate_hours_1_list[1][0],ate_hours_1_list[0][0]],bar_width,label='Old',edgecolor='k',color='k',alpha=alpha_plot2)
ax.legend(loc=loc_legen,fontsize=fontsize_axis)
ax.set_ylabel(r'Hours', fontsize=fontsize_axis)
ax.annotate(r'$\}$', xy=(x[0]+bar_width-0.2, ate_hours_1_list[0][1] + 0.1), xytext=(x[0]+bar_width-0.2, ate_hours_1_list[0][1] + 0.55),size = 60)
ax.annotate( '{:4.1f}'.format(ate_hours_1_list[1][1]-ate_hours_1_list[1][0]), xy=(x[0]+bar_width+0.1, ate_hours_1_list[0][1]+0.6), xytext=(x[0]+bar_width+0.1, ate_hours_1_list[0][1]+0.6),size = 16)
ax.annotate(r'$\}$', xy=(x[1]+bar_width-0.2, ate_hours_1_list[0][0] + 0.005), xytext=(x[1]+bar_width-0.2, ate_hours_1_list[0][0] + 0.004),size = 15)
ax.annotate( '{:4.1f}'.format(ate_hours_1_list[0][1]-ate_hours_1_list[0][0]), xy=(x[1]+bar_width-0.1, ate_hours_1_list[0][0]), xytext=(x[1]+bar_width-0.1, ate_hours_1_list[0][0]+0.005),size = 16)
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.yaxis.set_ticks_position('left')
ax.xaxis.set_ticks_position('bottom')
ax.set_xticklabels(['Full treatment', 'No CC subsidy'])
ax.set_xticks([x[0]+(bar_width)/2,x[1]+(bar_width)/2])
ax.legend(loc=loc_legen,fontsize=15)
plt.show()
fig.savefig('/home/jrodriguez/understanding_NH/results/Model/experiments/NH/ate_hours_1.pdf', format='pdf')
plt.close()

#Impact on hours conditional on working (intensive margin)
fig, ax=plt.subplots()
x = np.array([1,2.5])
plot1=ax.bar(x,[ate_hours_2_list[1][1],ate_hours_2_list[0][1]],bar_width,label='Young',color='k',alpha=alpha_plot1)
plot2=ax.bar(x + [bar_width],[ate_hours_2_list[1][0],ate_hours_2_list[0][0]],bar_width,label='Old',edgecolor='k',color='k',alpha=alpha_plot2)
ax.legend(loc=loc_legen,fontsize=fontsize_axis)
ax.set_ylabel(r'Hours', fontsize=fontsize_axis)
ax.annotate(r'$\}$', xy=(x[0]+bar_width-0.2, ate_hours_2_list[0][1] + 0.8), xytext=(x[0]+bar_width-0.2, ate_hours_2_list[0][1] + 0.8),size = 35)
ax.annotate( '{:4.1f}'.format(ate_hours_2_list[1][1]-ate_hours_2_list[1][0]), xy=(x[0]+bar_width, ate_hours_2_list[0][1]+0.85), xytext=(x[0]+bar_width, ate_hours_2_list[0][1]+0.85),size = 16)
ax.annotate(r'$\{$', xy=(x[1]+0.1, ate_hours_2_list[0][1] + 0.005), xytext=(x[1]+0.1, ate_hours_2_list[0][1] + 0.004),size = 20)
ax.annotate( '{:4.1f}'.format(ate_hours_2_list[0][1]-ate_hours_2_list[0][0]), xy=(x[1]-0.1, ate_hours_2_list[0][1]), xytext=(x[1]-0.1, ate_hours_2_list[0][1]+0.005),size = 16)
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.yaxis.set_ticks_position('left')
ax.xaxis.set_ticks_position('bottom')
ax.set_xticklabels(['Full treatment', 'No CC subsidy'])
ax.set_xticks([x[0]+(bar_width)/2,x[1]+(bar_width)/2])
ax.legend(loc=loc_legen,fontsize=15)
plt.show()
fig.savefig('/home/jrodriguez/understanding_NH/results/Model/experiments/NH/ate_hours_2.pdf', format='pdf')
plt.close()