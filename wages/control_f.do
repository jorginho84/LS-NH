/*
This do file regresses log wages for those who work + control function
from structural model

*/


clear
program drop _all
clear matrix
clear mata
set more off
set maxvar 15000
set matsize 2000


global results "/home/jrodriguez/understanding_NH/results/wages"

use "$results/pscores.dta", clear
replace index = index + 1
tempfile data_p
save `data_p', replace

use "/home/jrodriguez/understanding_NH/results/Model/sample_model_v2.dta", clear
egen index=seq()


merge 1:1 index using `data_p'


*Dummy for age of youngest child
gen d_young_aux = age_t0 + 2 <=6
bysort sampleid: egen youngest_aux = total(d_young)
gen d_young = youngest_aux >= 1
duplicates drop sampleid, force
drop d_young_aux youngest_aux


foreach x of numlist 0 1 4 7{
	replace grossv2_y`x'=grossv2_y`x'/52
}


*Hourly wages
foreach x of numlist 0 1 4 7{
	gen hwage_t`x'=grossv2_y`x'/hours_t`x'
}



*log variables
gen lhwage_t0=log(hwage_t0)
gen lhwage_t1=log(hwage_t1)
gen lhwage_t4=log(hwage_t4)
gen lhwage_t7=log(hwage_t7)

*Age at each year
gen age_t1=age_ra+1
gen age_t4=age_ra+4
gen age_t7=age_ra+7

gen d_work_all = lhwage_t0!=.  & lhwage_t1!=. & lhwage_t4!=.  & lhwage_t7!=. 

*Panel
egen id=seq()
keep lhwage* age_ra d_HS2 id d_work_all higrade d_black p_assign d_young pscore*
reshape long lhwage_t pscore, i(id) j(t_ra)
xtset id t_ra

gen lt = log(t_ra + 1)
gen pscore2=pscore^2
gen pscore3=pscore^3
gen pscore4=pscore^4


**************************************************************************
**************************************************************************
**************************************************************************
/*

REGRESSION

*/
**************************************************************************
**************************************************************************
**************************************************************************
gen age_ra2 = age_ra^2 

********REG 1**********
xi: reg lhwage_t d_young if p_assign == "C"
local beta_ols1 = string(round( _b[d_young],0.001),"%9.3f")
local se_beta_ols1 = string(round( _se[d_young],0.001),"%9.3f")
test d_young=0
local pv=r(p)

if `pv'<=.01{
	local ast_beta_ols1 ="***"	
}
else if `pv'<=.05 {
	local ast_beta_ols1 ="**"		
}
else if `pv'<=.1 {
	local ast_beta_ols1 ="*"		
}
else{
	local ast_beta_ols1=""
}





********REG 2**********
xi: reg lhwage_t d_young age_ra age_ra2 d_HS2 if p_assign == "C"
local beta_ols2 = string(round( _b[d_young],0.001),"%9.3f")
local se_beta_ols2 = string(round( _se[d_young],0.001),"%9.3f")
test d_young=0
local pv=r(p)

if `pv'<=.01{
	local ast_beta_ols2 ="***"
}
else if `pv'<=.05 {
	local ast_beta_ols2 ="**"		
}
else if `pv'<=.1 {
	local ast_beta_ols2 ="*"		
}
else{
	local ast_beta_ols2=""
}



foreach vars of varlist age_ra age_ra2 d_HS2{
	local beta_`vars'_ols = string(round( _b[`vars'],0.001),"%9.3f")
	local se_beta_`vars'_ols = string(round( _se[`vars'],0.001),"%9.3f")

	test `vars'=0
	local pv = r(p)
	if `pv'<=.01{
		local ast_`vars'_ols ="***"	
	}
	else if `pv'<=.05 {
		local ast_`vars'_ols ="**"		
	}
	else if `pv'<=.1 {
		local ast_`vars'_ols ="*"		
	}
	else{
		local ast_`vars'_ols=""
	}
	
}



********REG 3**********
xi: reg lhwage_t d_young pscore pscore2 pscore3 pscore4 if p_assign == "C" , noc
local beta_cf1 = string(round( _b[d_young],0.001),"%9.3f")
local se_beta_cf1 = string(round( _se[d_young],0.001),"%9.3f")

test d_young=0
local pv=r(p)

if `pv'<=.01{
	local ast_beta_cf1 ="***"	
}
else if `pv'<=.05 {
	local ast_beta_cf1 ="**"		
}
else if `pv'<=.1 {
	local ast_beta_cf1 ="*"		
}
else{
	local ast_beta_cf1 =""
}


********REG 4**********
xi: reg lhwage_t d_young age_ra age_ra2 d_HS2 pscore pscore2 pscore3 pscore4 if p_assign == "C" , noc
local beta_cf2 = string(round( _b[d_young],0.001),"%9.3f")
local se_beta_cf2 = string(round( _se[d_young],0.001),"%9.3f")

test d_young=0
local pv=r(p)

if `pv'<=.01{
	local ast_beta_cf2 ="***"	
}
else if `pv'<=.05 {
	local ast_beta_cf2 ="**"		
}
else if `pv'<=.1 {
	local ast_beta_cf2 ="*"		
}
else{
	local ast_beta_cf2 =""
}


foreach vars of varlist age_ra age_ra2 d_HS2{
	local beta_`vars'_cf = string(round( _b[`vars'],0.001),"%9.3f")
	local se_beta_`vars'_cf = string(round( _se[`vars'],0.001),"%9.3f")

	test `vars'=0
	local pv = r(p)
	if `pv'<=.01{
		local ast_`vars'_cf ="***"	
	}
	else if `pv'<=.05 {
		local ast_`vars'_cf ="**"		
	}
	else if `pv'<=.1 {
		local ast_`vars'_cf ="*"		
	}
	else{
		local ast_`vars'_cf =""
	}
	
}



*************************************************************************************
*************************************************************************************
*************************************************************************************
/*GENERATING TABLE*/

file open tab_dec using "$results/table_cf.tex", write replace
file write tab_dec "\begin{tabular}{llccccccc}"_n
file write tab_dec "\hline"_n
file write tab_dec "\multirow{2}[2]{*}{Variables} &       & \multicolumn{3}{c}{OLS} && \multicolumn{3}{c}{Control function} \bigstrut[t]\\"_n
file write tab_dec "      &       & (1)   &       & (2)   &       & (3)   &       & (4) \bigstrut[b]\\"_n
file write tab_dec "\cline{1-1}\cline{3-9}      &       &       &       &       &       &       &       &  \bigstrut[t]\\"_n

file write tab_dec "Young child &       & `beta_ols1'`ast_beta_ols1'   &       & `beta_ols2'`ast_beta_ols2'   &       & `beta_cf1'`ast_beta_cf1'   &       & `beta_cf2'`ast_beta_cf2' \\"_n
file write tab_dec "      &       & (`se_beta_ols1') &       & (`se_beta_ols2') &       & (`se_beta_cf1') &       & (`se_beta_cf2') \\"_n
file write tab_dec "&       &       &       &       &       &       &       &  \\"_n
file write tab_dec "High school &       &   &       & `beta_d_HS2_ols'`ast_d_HS2_ols'   &       &   &       & `beta_d_HS2_cf'`ast_d_HS2_cf' \\"_n
file write tab_dec "      &       &  &       & (`se_beta_d_HS2_ols') &       &  &       & (`se_beta_d_HS2_cf') \\"_n
file write tab_dec "&       &       &       &       &       &       &       &  \\"_n
file write tab_dec "Age &       &   &       & `beta_age_ra_ols'`ast_age_ra_ols'   &       &   &       & `beta_age_ra_cf'`ast_age_ra_cf' \\"_n
file write tab_dec "      &       &  &       & (`se_beta_age_ra_ols') &       &  &       & (`se_beta_age_ra_cf') \\"_n
file write tab_dec "&       &       &       &       &       &       &       &  \\"_n
file write tab_dec "Age\$^2\$&       &   &       & `beta_age_ra2_ols'`ast_age_ra2_ols'   &       &   &       & `beta_age_ra2_cf'`ast_age_ra2_cf' \\"_n
file write tab_dec "      &       &  &       & (`se_beta_age_ra2_ols') &       &  &       & (`se_beta_age_ra2_cf') \\"_n
file write tab_dec "\hline"_n
file write tab_dec "\end{tabular}%"_n
file close tab_dec
      

exit, STATA clear



