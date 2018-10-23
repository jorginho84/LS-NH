part = choices['hours_matrix']==hours_p
full = choices['hours_matrix']==hours_f
emp = (part == 1) | (full ==  1)
hours = choices['hours_matrix'].copy()

#saving ates here
ate_emp = []
ate_hours = []
se_ate_emp = []
se_ate_hours= []

#simulated
for samp in range(2):
	ate_emp.append(np.mean(np.mean(emp[(passign[:,0]==1) & (boo_sample[:,0]==samp),:,:],axis=0) - np.mean(emp[(passign[:,0]==0) & (boo_sample[:,0]==samp),:,:],axis=0),axis=1 ))
	ate_hours.append(np.mean(np.mean(hours[(passign[:,0]==1) & (boo_sample[:,0]==samp),:,:],axis=0) - np.mean(hours[(passign[:,0]==0) & (boo_sample[:,0]==samp),:,:],axis=0),axis=1 ))

	se_ate_emp.append(np.std(np.mean(emp[(passign[:,0]==1) & (boo_sample[:,0]==samp),:,:],axis=0) - np.mean(emp[(passign[:,0]==0) & (boo_sample[:,0]==samp),:,:],axis=0),axis=1 ))
	se_ate_hours.append(np.std(np.mean(hours[(passign[:,0]==1) & (boo_sample[:,0]==samp),:,:],axis=0) - np.mean(hours[(passign[:,0]==0) & (boo_sample[:,0]==samp),:,:],axis=0),axis=1 ))

#data
ate_emp_obs = []
se_ate_emp_obs = []

ate_hours_obs = []
se_ate_hours_obs = []


dofile = "/home/jrodriguez/understanding_NH/codes/model/fit/ate_emp.do"
cmd = ["stata-se", "do", dofile]
subprocess.call(cmd)

for k in ["o", "y"]:

	ate_emp_obs.append(pd.read_csv('/home/jrodriguez/understanding_NH/results/Model/fit/ate_emp_'+k+'.csv').values)
	se_ate_emp_obs.append(pd.read_csv('/home/jrodriguez/understanding_NH/results/Model/fit/se_ate_emp_'+k+'.csv').values)
	ate_hours_obs.append(pd.read_csv('/home/jrodriguez/understanding_NH/results/Model/fit/ate_hours_'+k+'.csv').values)
	se_ate_hours_obs.append(pd.read_csv('/home/jrodriguez/understanding_NH/results/Model/fit/se_ate_hours_'+k+'.csv').values)



ate_sim_list = [ate_emp,ate_hours]
se_ate_list = [se_ate_emp,se_ate_hours]
ate_list = [ate_emp_obs,ate_hours_obs]
se_list = [se_ate_emp_obs,se_ate_hours_obs]
name_list = ["employment", "weekly hours worked"]
graph_list = ["employment", "hours"]
sample_list = ["old", "young"]

for k in range(2): #the sample loop

	for j in range(2): #the moment loop
		ate_emp_obs_long=np.empty((ate_sim_list[j][0].shape))
		ate_emp_obs_long[:] =np.NAN
		se_ate_emp_obs_long=np.empty((ate_sim_list[j][0].shape))
		se_ate_emp_obs_long[:] =np.NAN 

		i = 0
		for x in [0,1,4,7]:
			ate_emp_obs_long[x] = ate_list[j][k][i,0]
			se_ate_emp_obs_long[x] = se_list[j][k][i,0]
			i = i + 1

		#figure
		s1mask = np.isfinite(ate_emp_obs_long)
		nper = ate_emp_obs_long.shape[0]
		fig, ax=plt.subplots()
		x = np.array(range(0,nper))
		plot1=ax.plot(x[0:3],ate_sim_list[j][k][0:3],'bs-',label='Simulated',alpha=0.6)
		plot4=ax.errorbar(x[0:3],ate_sim_list[j][k][0:3],yerr=se_ate_list[j][k][0:3],ecolor='b',alpha=0.6)
		plot2=ax.plot(x[s1mask][0:2]+0.05,ate_emp_obs_long[s1mask][0:2],'ko-',label='Data',alpha=0.9)
		plot3=ax.errorbar(x[s1mask][0:2]+0.05,ate_emp_obs_long[s1mask][0:2],yerr=se_ate_emp_obs_long[s1mask][0:2],fmt='ko',ecolor='k',alpha=0.9)
		plt.setp(plot1,linewidth=5)
		plt.setp(plot2,linewidth=5)
		plt.setp(plot3,linewidth=3)
		plt.setp(plot4,linewidth=3)
		ax.set_xticks([0, 1, 2])
		ax.set_xlim(-0.2,2.2)
		if j==0:
			ax.set_ylim(0,0.22)
		else:
			ax.set_ylim(0,12)

		ax.set_ylabel(r'Impact on ' + name_list[j], fontsize=15)
		ax.set_xlabel(r'Years after random assignment ($t$)', fontsize=15)
		ax.spines['right'].set_visible(False)
		ax.spines['top'].set_visible(False)
		ax.yaxis.set_ticks_position('left')
		ax.xaxis.set_ticks_position('bottom')
		plt.yticks(fontsize=11)
		plt.xticks(fontsize=11)
		ax.legend(loc=1,fontsize=15)
		plt.show()
		fig.savefig('/home/jrodriguez/understanding_NH/results/Model/fit/ate_' + graph_list[j] + '_' +sample_list[k] +'.pdf', format='pdf')
		plt.close()

	
	