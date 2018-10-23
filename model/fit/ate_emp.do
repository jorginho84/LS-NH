/*
This do-file computes ate on emp using bootstrap
*/

clear
program drop _all
clear matrix
clear mata
set more off


use "/home/jrodriguez/understanding_NH/results/Model/sample_model_v2.dta", clear
set seed 2828
local reps = 800

*This program computes ATE for a given year
program prob_diff_y, rclass
	version 13
	tempname mean_1 mean_2
	args emp
	qui: sum `emp' if d_RA==1 & age_t2<=6
	scalar `mean_1'=r(mean)
	qui: sum `emp' if d_RA==0 & age_t2<=6
	scalar `mean_2'=r(mean)
	return scalar ate=`mean_1' - `mean_2'
end

program prob_diff_o, rclass
	version 13
	tempname mean_1 mean_2
	args emp
	qui: sum `emp' if d_RA==1 & age_t2>6
	scalar `mean_1'=r(mean)
	qui: sum `emp' if d_RA==0 & age_t2>6
	scalar `mean_2'=r(mean)
	return scalar ate=`mean_1' - `mean_2'
end

gen age_t2 = age_t0 + 2

*Computing ATEs for each year
mat ate_emp_y=J(9,1,.)
mat se_ate_emp_y=J(9,1,.)
mat ate_hours_y=J(9,1,.)
mat se_ate_hours_y=J(9,1,.)

mat ate_emp_o=J(9,1,.)
mat se_ate_emp_o=J(9,1,.)
mat ate_hours_o=J(9,1,.)
mat se_ate_hours_o=J(9,1,.)

foreach x in 0 1 4 7{
	gen d_emp_t`x' = hours_t`x'_cat2 == 1 | hours_t`x'_cat3 == 1
	
	bootstrap diff=r(ate), reps(`reps'): prob_diff_y d_emp_t`x'
	mat ate_emp_y[`x'+1,1] = e(b)
	mat se_ate_emp_y[`x'+1,1] = e(se)

	bootstrap diff=r(ate), reps(`reps'): prob_diff_o d_emp_t`x'
	mat ate_emp_o[`x'+1,1] = e(b)
	mat se_ate_emp_o[`x'+1,1] = e(se)

	bootstrap diff=r(ate), reps(`reps'): prob_diff_y hours_t`x'
	mat ate_hours_y[`x'+1,1] = e(b)
	mat se_ate_hours_y[`x'+1,1] = e(se)

	bootstrap diff=r(ate), reps(`reps'): prob_diff_o hours_t`x'
	mat ate_hours_o[`x'+1,1] = e(b)
	mat se_ate_hours_o[`x'+1,1] = e(se)

}

foreach vars in emp hours{

	*For each year
	preserve
	clear
	set obs 9
	svmat ate_`vars'_y
	outsheet using "/home/jrodriguez/understanding_NH/results/Model/fit/ate_`vars'_y.csv", comma replace
	restore

	preserve
	clear
	set obs 9
	svmat ate_`vars'_o
	outsheet using "/home/jrodriguez/understanding_NH/results/Model/fit/ate_`vars'_o.csv", comma replace
	restore

	preserve
	clear
	set obs 9
	svmat se_ate_`vars'_y
	outsheet using "/home/jrodriguez/understanding_NH/results/Model/fit/se_ate_`vars'_y.csv", comma replace
	restore

	preserve
	clear
	set obs 9
	svmat se_ate_`vars'_o
	outsheet using "/home/jrodriguez/understanding_NH/results/Model/fit/se_ate_`vars'_o.csv", comma replace
	restore

	
} 


exit, STATA clear






