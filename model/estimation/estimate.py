"""
This class takes an initial set of parameters and actual data and estimates
the parameters of the structural model via General Indirect Inference.

"""
import numpy as np
import pandas as pd
import gc
from numba import jit
import sys, os
from scipy import stats
from scipy.optimize import minimize
from scipy.optimize import fmin_bfgs
from pathos.multiprocessing import ProcessPool
sys.path.append("/home/jrodriguez/understanding_NH/codes/model/simulate_sample")
import utility as util
import gridemax
import time
import int_linear
import emax as emax
import simdata as simdata


class Estimate:
	def __init__(self,nperiods,param0,x_w,x_m,x_k,x_wmk,passign,agech0,
		nkids0,married0,D,dict_grid,M,N,moments_vector,w_matrix,hours_p,hours_f,
		wr,cs,ws):

		self.nperiods,self.param0=nperiods,param0
		self.x_w,self.x_m,self.x_k,self.x_wmk=x_w,x_m,x_k,x_wmk
		self.passign,self.nkids0,self.married0=passign,nkids0,married0
		self.D,self.dict_grid =D,dict_grid
		self.agech0=agech0
		self.M,self.N=M,N
		self.moments_vector,self.w_matrix=moments_vector,w_matrix
		self.hours_p,self.hours_f=hours_p,hours_f
		self.wr,self.cs,self.ws=wr,cs,ws

	def emax(self,param1,model):
		"""
		Takes given betas and estimates the emax function (en emax_dic)

		"""
		#free up memory
		gc.collect()
		#updating with new betas
		np.random.seed(1) #always the same emax, for a given set of beta
		emax_ins_1=emax.Emaxt(param1,self.D,self.dict_grid,self.hours_p,
			self.hours_f,self.wr,self.cs,self.ws,model)
		return emax_ins_1.recursive() #t=1 to t=8

	def samples(self,param1,emaxins,model):
		"""
		Returns a sample M of utility values
		"""

		#number of choices
		J=6

		#updating sample with new betas and emax
		simdata_ins= simdata.SimData(self.N,param1,emaxins,
			self.x_w,self.x_m,self.x_k,self.x_wmk,self.passign,
			self.nkids0,self.married0,self.agech0,self.hours_p,self.hours_f,
			self.wr,self.cs,self.ws,model)

		#save here
		util_list=[]
		income_matrix=np.zeros((self.N,self.nperiods,self.M))
		consumption_matrix=np.zeros((self.N,self.nperiods,self.M))
		iscost_matrix=np.zeros((self.N,self.nperiods,self.M))
		cscost_matrix=np.zeros((self.N,self.nperiods,self.M))
		choice_matrix=np.zeros((self.N,self.nperiods,self.M))
		utils_periodt=np.zeros((self.N,J,self.nperiods,self.M))
		utils_c_periodt=np.zeros((self.N,J,self.nperiods,self.M))
		theta_matrix=np.zeros((self.N,self.nperiods,self.M))
		wage_matrix=np.zeros((self.N,self.nperiods,self.M))
		hours_matrix=np.zeros((self.N,self.nperiods,self.M))
		ssrs_t2_matrix=np.zeros((self.N,self.M))
		ssrs_t5_matrix=np.zeros((self.N,self.M))
		
		#Computing samples (in parallel)
		def sample_gen(j):
			np.random.seed(j+100)
			return simdata_ins.fake_data(self.nperiods)

		pool = ProcessPool(nodes=10)
		dics = pool.map(sample_gen,range(self.M))
		pool.close()
		pool.join()
		pool.clear()
	#	dics = []
	#	for j in range(self.M):
	#		np.random.seed(j+100)
	#		dics.append(simdata_ins.fake_data(self.nperiods))


    	#Saving results		
		for j in range(0,self.M):
			income_matrix[:,:,j]=dics[j]['Income']
			consumption_matrix[:,:,j]=dics[j]['Consumption']
			iscost_matrix[:,:,j]=dics[j]['nh_matrix']
			cscost_matrix[:,:,j]=dics[j]['cs_cost_matrix']
			choice_matrix[:,:,j]=dics[j]['Choices']
			theta_matrix[:,:,j]=dics[j]['Theta']
			wage_matrix[:,:,j]=dics[j]['Wage']
			hours_matrix[:,:,j]=dics[j]['Hours']
			ssrs_t2_matrix[:,j]=dics[j]['SSRS_t2']
			ssrs_t5_matrix[:,j]=dics[j]['SSRS_t5']
			
			

			for periodt in range(0,self.nperiods):
				utils_periodt[:,:,periodt,j]=dics[j]['Uti_values_dic'][periodt]
				utils_c_periodt[:,:,periodt,j]=dics[j]['Uti_values_c_dic'][periodt]

		return {'utils_periodt': utils_periodt,'utils_c_periodt': utils_c_periodt,
				'income_matrix':income_matrix,
				'choice_matrix': choice_matrix,'theta_matrix': theta_matrix,
				'wage_matrix': wage_matrix,'consumption_matrix':consumption_matrix,
				'hours_matrix': hours_matrix,'ssrs_t2_matrix':ssrs_t2_matrix,
				'ssrs_t5_matrix':ssrs_t5_matrix,
				'cscost_matrix':cscost_matrix, 'iscost_matrix': iscost_matrix }

	def aux_model(self,choices):
		"""
		Computes the auxiliary estimates from simulated data
		"""

		#number of choices
		J=6
		J_1=3 #3 hours categories
		nperiods=self.nperiods
		age_child=np.zeros((self.N,nperiods)) #age of child every period
		for x in range(0,nperiods):
			age_child[:,x]=np.reshape(self.agech0,self.N)+x

		##Obtaining Auxiliary estimate for every m##
		choice_matrix=choices['choice_matrix'].copy()
		hours_matrix=choices['hours_matrix'].copy()
		wage_matrix=choices['wage_matrix'].copy()
		ssrs_t2_matrix=choices['ssrs_t2_matrix'].copy()
		ssrs_t5_matrix=choices['ssrs_t5_matrix'].copy()
		consumption_matrix=choices['consumption_matrix'].copy()

		############################################################
		####Aux to identify utility function########################
		############################################################

		#child care at period t=1
		choices_aux=choice_matrix[:,1,:].copy()
		age_aux=age_child[:,1].copy()
		passign_aux=self.passign[:,0].copy()
		cc_logit=choices_aux>=3
		boo=(passign_aux==0)
		beta_childcare=np.mean(cc_logit[boo,:],axis=0) #beta for every m


		#mean hours at t=0,1
		hours_aux=np.concatenate((hours_matrix[:,0,:],hours_matrix[:,1,:]),axis=0)
		passign_aux=np.concatenate((self.passign[:,0],self.passign[:,0]),axis=0)
		
		hours_aux_1 = hours_aux == self.hours_p
		hours_aux_2 = hours_aux == self.hours_f
		boo_h = passign_aux == 0
		beta_hours1=np.mean(hours_aux_1[boo_h,:],axis=0)
		beta_hours2=np.mean(hours_aux_2[boo_h,:],axis=0)

		
		############################################################
		####Aux to identify wage process############################
		############################################################


		passign_aux=np.concatenate((self.passign[:,0],self.passign[:,0],
			self.passign[:,0],self.passign[:,0]),axis=0)

		wage_aux=np.log(np.concatenate((wage_matrix[:,0,:],wage_matrix[:,1,:],
		wage_matrix[:,4,:],wage_matrix[:,7,:]),axis=0)) #to panel and logs

		age_t0=self.x_w[:,0]
		age=np.zeros((self.N,self.nperiods))
		for t in range(self.nperiods):
			age[:,t]=age_t0.copy()
		
		logt_dic={'period0':np.zeros((self.N,1)),
		'period1': np.zeros((self.N,1)) + 1,
		'period4': np.zeros((self.N,1)) + 4,
		'period7':np.zeros((self.N,1)) + 7}
		
		lt = np.reshape(np.concatenate((logt_dic['period0'][:,0],
			logt_dic['period1'][:,0],logt_dic['period4'][:,0],
			logt_dic['period7'][:,0]),axis=0),(self.N*4,1))

		x_list = [] #the X matrix
		x_list.append(np.reshape(np.concatenate((self.x_w[:,0],self.x_w[:,0],self.x_w[:,0],self.x_w[:,0]),axis=0),(self.N*4,1)))
		x_list.append(lt)
		x_list.append(np.reshape(np.concatenate((self.x_w[:,1],self.x_w[:,1],self.x_w[:,1],self.x_w[:,1]),axis=0),(self.N*4,1)))

		#sample who work all years
		boo_sample = ((choice_matrix[:,0,:]==1) | (choice_matrix[:,0,:]==2) | (choice_matrix[:,0,:]==4) | (choice_matrix[:,0,:]==5)) & ((choice_matrix[:,1,:]==1) | (choice_matrix[:,1,:]==2) | (choice_matrix[:,1,:]==4) | (choice_matrix[:,1,:]==5)) 	& ((choice_matrix[:,4,:]==1) | (choice_matrix[:,4,:]==2) | (choice_matrix[:,4,:]==4) | (choice_matrix[:,4,:]==5)) 	& ((choice_matrix[:,7,:]==1) | (choice_matrix[:,7,:]==2) | (choice_matrix[:,7,:]==4) | (choice_matrix[:,7,:]==5))
		boo_sample[self.passign[:,0]==1,:] = 0 #only control group estimates
		boo_work = np.concatenate((boo_sample,boo_sample,
			boo_sample,boo_sample),axis=0)

		beta_w=np.zeros((len(x_list),self.M))
		sigma_w=np.zeros((1,self.M))
		rho_eps=np.zeros((1,self.M))
		

		for j in range(self.M): #the sample loop
			xw_aux=np.concatenate((x_list[0][boo_work[:,j]==1,:],
				x_list[1][boo_work[:,j]==1,:],
				x_list[2][boo_work[:,j]==1,:]),axis=1)

			
			if np.linalg.cond(np.dot(np.transpose(xw_aux),
					xw_aux)) < 1/sys.float_info.epsilon: #If nonsingular matrix

				xx_inv=np.linalg.inv(np.dot(np.transpose(xw_aux),xw_aux))
				xy=np.dot(np.transpose(xw_aux),wage_aux[boo_work[:,j],j])
				beta_w[:,j]=np.dot(xx_inv,xy)

				#obtaining residuals by period for those who work all periods
				e_list = []
				n_work = self.x_w[boo_sample[:,j]==1,1].shape[0]

				for k in [0,1,4,7]:

					#Xs for those working all periods
					xw_aux_2=np.concatenate((np.reshape(self.x_w[boo_sample[:,j]==1,0],(n_work,1)),
						np.reshape(logt_dic['period' + str(k)][boo_sample[:,j]==1],(n_work,1)),
						np.reshape(self.x_w[boo_sample[:,j]==1,1],(n_work,1)),),axis=1)
					
					e = np.log(wage_matrix[boo_sample[:,j]==1,k,j]) - np.dot(xw_aux_2,beta_w[:,j])
					e_list.append(e)

				e  = np.concatenate((e_list[1],e_list[2],e_list[3]),axis=0).reshape((n_work*3,1))
				e_t1  = np.concatenate((e_list[0],e_list[1],e_list[2]),axis=0).reshape((n_work*3,1)) #lagged
				
				ee_inv = np.linalg.inv(np.dot(np.transpose(e_t1),e_t1))
				ey = np.dot(np.transpose(e_t1),e)
				rho_eps[:,j] = np.dot(ee_inv,ey)
				u = e - e_t1*rho_eps[:,j]
				sigma_w[:,j]=np.sum(np.square(u))/(e.shape[0] - rho_eps[:,j].shape[0])
			else:
				print ('disregarding m sample: singular matrix in wage process estimation')
				pass
		beta_wagep=np.concatenate((beta_w,sigma_w,rho_eps),axis=0)

		
		############################################################
		###Aux estimate to identify prod function###################
		############################################################

		

		ssrs_t2_matrix_se=ssrs_t2_matrix>2
		ssrs_t5_matrix_se=ssrs_t5_matrix>2

				
		cc_matrix = choice_matrix>=3
		

		leisure_matrix = np.zeros((self.N,hours_matrix.shape[1],self.M))
		for t in range(hours_matrix.shape[1]):
			leisure_matrix[age_child[:,t]<=5,t,:] = cc_matrix[age_child[:,t]<=5,t,:]*(168 - self.hours_f) + (168-hours_matrix[age_child[:,t]<=5,t,:])*(1-cc_matrix[age_child[:,t]<=5,t,:])
			leisure_matrix[age_child[:,t]>5,t,:] = cc_matrix[age_child[:,t]>5,t,:]*(133 - self.hours_f) + (133-hours_matrix[age_child[:,t]>5,t,:])*(1-cc_matrix[age_child[:,t]>5,t,:])
		
		#to panel
		consumption_aux=np.concatenate((consumption_matrix[:,1,:],
			consumption_matrix[:,4,:]),axis=0)
		leisure_aux=np.concatenate((leisure_matrix[:,1,:],
			leisure_matrix[:,4,:]),axis=0)
		choice_aux=np.concatenate((choice_matrix[:,1,:],
			choice_matrix[:,4,:]),axis=0)
		age_aux=np.concatenate((age_child[:,1],
			age_child[:,4]),axis=0)
		ssrs_aux=np.concatenate((ssrs_t2_matrix_se,
			ssrs_t5_matrix_se),axis=0)
		passign_aux=np.concatenate((self.passign[:,0],
			self.passign[:,0]),axis=0)

		beta_inputs_young=np.zeros((4,self.M)) #5 moments
		beta_inputs_old=np.zeros((4,self.M)) #5 moments
		betas_init_prod=np.zeros((1,self.M)) #5 moments
		beta_kappas_t2=np.zeros((4,self.M)) #4 moments
		beta_kappas_t5=np.zeros((4,self.M)) #4 moments

		for z in range(2,6): #4 rankings
			boo=ssrs_t2_matrix==z
			beta_kappas_t2[z-2,:]=np.mean(boo,axis=0)
			boo=ssrs_t5_matrix==z
			beta_kappas_t5[z-2,:]=np.mean(boo,axis=0)
		
			
		for j in range(self.M):

			#for gamma1
			beta_inputs_young[0,j] = np.corrcoef(ssrs_t2_matrix_se[(self.passign[:,0]==0) & (age_child[:,1]<=5),j],ssrs_t5_matrix_se[(self.passign[:,0]==0) & (age_child[:,1]<=5),j])[1,0]
			beta_inputs_old[0,j] = np.corrcoef(ssrs_t2_matrix_se[(self.passign[:,0]==0) & (age_child[:,1]>5),j],ssrs_t5_matrix_se[(self.passign[:,0]==0) & (age_child[:,1]>5),j])[1,0]
			
			#for gamma2 and 3
			x_aux = np.concatenate((np.reshape(consumption_aux[(passign_aux==0) & (age_aux<=5),j],(consumption_aux[(passign_aux==0) & (age_aux<=5),j].shape[0],1)),
				np.reshape(leisure_aux[(passign_aux==0) & (age_aux<=5),j],(leisure_aux[(passign_aux==0) & (age_aux<=5),j].shape[0],1)),
				np.ones((leisure_aux[(passign_aux==0) & (age_aux<=5),j].shape[0],1))),axis=1)
			
			xx_inv = np.linalg.inv(np.dot(np.transpose(x_aux),x_aux))
			xy = np.dot(np.transpose(x_aux),ssrs_aux[(passign_aux==0) & (age_aux<=5),j])
			beta = np.dot(xx_inv,xy)
			beta_inputs_young[1,j] = beta[0]
			beta_inputs_young[2,j] = beta[1]

			x_aux = np.concatenate((np.reshape(consumption_aux[(passign_aux==0) & (age_aux>5),j],(consumption_aux[(passign_aux==0) & (age_aux>5),j].shape[0],1)),
				np.reshape(leisure_aux[(passign_aux==0) & (age_aux>5),j],(leisure_aux[(passign_aux==0) & (age_aux>5),j].shape[0],1)),
				np.ones((leisure_aux[(passign_aux==0) & (age_aux>5),j].shape[0],1))),axis=1)
			
			xx_inv = np.linalg.inv(np.dot(np.transpose(x_aux),x_aux))
			xy = np.dot(np.transpose(x_aux),ssrs_aux[(passign_aux==0) & (age_aux>5),j])
			beta = np.dot(xx_inv,xy)
			beta_inputs_old[1,j] = beta[0]
			beta_inputs_old[2,j] = beta[1]

			#for tfp
			b_cc0=choice_aux[:,j]<3 #child care choice=0 at t=1
			b_cc1=choice_aux[:,j]>=3 #child care choice=1 at t=1
			boo_young_cc0 = (b_cc0==True) & (passign_aux==0)
			boo_young_cc1 = (b_cc1==True) & (passign_aux==0)
			beta_inputs_young[3,j] = np.mean(ssrs_aux[(boo_young_cc1) & (age_aux<=5),j]) - np.mean(ssrs_aux[(boo_young_cc0) & (age_aux<=5),j])
			beta_inputs_old[3,j] = np.mean(ssrs_aux[(boo_young_cc1) & (age_aux>5),j]) - np.mean(ssrs_aux[(boo_young_cc0) & (age_aux>5),j])
			
			
			betas_init_prod[0,j] = np.corrcoef(ssrs_t2_matrix_se[self.passign[:,0]==0,j],np.log(wage_matrix[self.passign[:,0]==0,0,j]))[1,0]

		
		
		
		return{'beta_childcare':beta_childcare,'beta_hours1': beta_hours1,
		'beta_hours2':beta_hours2,'beta_wagep': beta_wagep,
		'beta_kappas_t2': beta_kappas_t2,
		'beta_inputs_young': beta_inputs_young,'beta_inputs_old': beta_inputs_old,
		'beta_kappas_t5':beta_kappas_t5,'betas_init_prod':betas_init_prod}
	
	
	def ll(self,beta):
		"""
		Takes structural parameters and computes the objective function for optimization 
		
		"""
		start_time = time.time()
		print ('')
		print ('')
		print ('Beginning sample generator')

		def sym(a):
			return ((1/(1+np.exp(-a))) - 0.5)*2

		#updating beta->parameters instance to compute likelihood.
		self.param0.eta=beta[0]
		self.param0.alphap=beta[1]
		self.param0.alphaf=beta[2]
		self.param0.betaw[0]=beta[3]
		self.param0.betaw[1]=beta[4]
		self.param0.betaw[2]=beta[5]
		self.param0.betaw[3]=np.exp(beta[6])
		self.param0.betaw[4]=beta[7]
		self.param0.gamma1[0]=beta[8]
		self.param0.gamma2[0]=beta[9]
		self.param0.gamma3[0]=beta[10]
		self.param0.tfp[0]=beta[11]
		self.param0.gamma1[1]=beta[12]
		self.param0.gamma2[1]=beta[13]
		self.param0.gamma3[1]=beta[14]
		self.param0.tfp[1]=beta[15]
		self.param0.kappas[0][0]=beta[16]
		self.param0.kappas[0][1]=beta[17]
		self.param0.kappas[0][2]=beta[18]
		self.param0.kappas[0][3]=beta[19]
		self.param0.kappas[1][0]=beta[20]
		self.param0.kappas[1][1]=beta[21]
		self.param0.kappas[1][2]=beta[22]
		self.param0.kappas[1][3]=beta[23]
		self.param0.rho_theta_epsilon=sym(beta[24])
					

		#The model (utility instance)
		hours = np.zeros(self.N)
		childcare  = np.zeros(self.N)

		model  = util.Utility(self.param0,self.N,self.x_w,self.x_m,self.x_k,self.passign,
			self.nkids0,self.married0,hours,childcare,
			self.agech0,self.hours_p,self.hours_f,self.wr,self.cs,self.ws)

		##obtaining emax instance##
		emax_instance=self.emax(self.param0,model)

		print('done with emax')
		
		##obtaining samples##

		choices=self.samples(self.param0,emax_instance,model)

		###########################################################################
		##Getting the betas of the auxiliary model#################################
		###########################################################################
		dic_betas=self.aux_model(choices)

		time_opt=time.time() - start_time
		print ('')
		print ('')
		print ('Done sample generation in')
		print("--- %s seconds ---" % (time_opt))
		print ('')
		print ('')
		start_time = time.time()
		print ('Beginning aux model generator')


		#utility_aux
		beta_childcare=np.mean(dic_betas['beta_childcare'],axis=0) #1x1
		beta_hours1=np.mean(dic_betas['beta_hours1'],axis=0) #1x1
		beta_hours2=np.mean(dic_betas['beta_hours2'],axis=0) #1x1
		beta_wagep=np.mean(dic_betas['beta_wagep'],axis=1) # 6 x 1
		beta_kappas_t2=np.mean(dic_betas['beta_kappas_t2'],axis=1) #4 x 1
		beta_kappas_t5=np.mean(dic_betas['beta_kappas_t5'],axis=1) #4 x 1
		beta_inputs_young=np.mean(dic_betas['beta_inputs_young'],axis=1) #4 x 1
		beta_inputs_old=np.mean(dic_betas['beta_inputs_old'],axis=1) #4 x 1
		betas_init_prod=np.mean(dic_betas['betas_init_prod'],axis=1) #1 x 1
		
		

			

		###########################################################################
		####Forming the likelihood#################################################
		###########################################################################

		#Number of moments to match
		num_par=beta_childcare.size + beta_hours1.size + beta_hours2.size + beta_wagep.size + + beta_kappas_t2.size +  beta_kappas_t5.size + beta_inputs_young.size + beta_inputs_old.size + betas_init_prod.size
		
		#Outer matrix
		x_vector=np.zeros((num_par,1))

		
		x_vector[0:beta_childcare.size,0]=beta_childcare - self.moments_vector[0,0]
		
		ind=beta_childcare.size
		x_vector[ind:ind+beta_hours1.size,0]=beta_hours1 - self.moments_vector[ind,0]

		ind = ind + beta_hours1.size
		x_vector[ind:ind+beta_hours2.size,0]=beta_hours2 - self.moments_vector[ind,0]
		
		ind=ind + beta_hours2.size
		x_vector[ind: ind+ beta_wagep.size,0]=beta_wagep - self.moments_vector[ind:ind+ beta_wagep.size,0]
		
		ind = ind + beta_wagep.size
		x_vector[ind:ind + beta_kappas_t2.size,0]=beta_kappas_t2 - self.moments_vector[ind:ind + beta_kappas_t2.size,0]

		ind = ind + beta_kappas_t2.size
		x_vector[ind: ind + beta_kappas_t5.size,0] = beta_kappas_t5 - self.moments_vector[ind: ind + beta_kappas_t5.size,0]
		
		ind = ind + beta_kappas_t5.size
		x_vector[ind:ind + beta_inputs_young.size,0] = beta_inputs_young - self.moments_vector[ind:ind + beta_inputs_young.size,0]

		ind = ind + beta_inputs_young.size
		x_vector[ind:ind + beta_inputs_old.size,0] = beta_inputs_old - self.moments_vector[ind:ind + beta_inputs_old.size,0]
		
		ind = ind + beta_inputs_old.size
		x_vector[ind:ind + betas_init_prod.size,0] = betas_init_prod - self.moments_vector[ind:ind + betas_init_prod.size,0]
		
		
		#The Q metric
		q_w=np.dot(np.dot(np.transpose(x_vector),self.w_matrix),x_vector)
		print ('')
		print ('The objetive function value equals ', q_w)
		print ('')

		time_opt=time.time() - start_time
		print ('Done aux model generation in')
		print("--- %s seconds ---" % (time_opt))

		return q_w



	def optimizer(self):
		
		
		#symmetric interval constraint
		def syminv(g):
			out = -np.log((2/(g+1)) - 1)
			return out
		
				
		beta0=np.array([self.param0.eta,self.param0.alphap,self.param0.alphaf,
			self.param0.betaw[0],
			self.param0.betaw[1],self.param0.betaw[2],
			np.log(self.param0.betaw[3]),self.param0.betaw[4],
			self.param0.gamma1[0],self.param0.gamma2[0],self.param0.gamma3[0],	
			self.param0.tfp[0],
			self.param0.gamma1[1],self.param0.gamma2[1],self.param0.gamma3[1],	
			self.param0.tfp[1],
			self.param0.kappas[0][0],self.param0.kappas[0][1],#kappa: t=2, m0
			self.param0.kappas[0][2],self.param0.kappas[0][3], #kappa: t=2, m0
			self.param0.kappas[1][0],self.param0.kappas[1][1],#kappa: t=5, m0
			self.param0.kappas[1][2],self.param0.kappas[1][3], #kappa: t=5, m0,
			syminv(self.param0.rho_theta_epsilon)]) 

		
		#Here we go
		opt = minimize(self.ll, beta0,  method='Nelder-Mead', options={'maxiter':5000, 'maxfev': 90000, 'ftol': 1e-3, 'disp': True, 'adaptive': True});
		#opt = minimize(self.ll, beta0,  method='bfgs', options={'maxiter':5000, 'gtol': 1e-3, 'disp': True});
		
		return opt



