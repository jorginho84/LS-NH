/*

This do-file computes the impact of NH on total income.
Income is measured using administrative sources.

Income sources:
-UI
-Earnings supplement
-CSJs
-EITC


To compute effects by employment status: change local 'emp"

*/

global databases "/home/jrodriguez/NH-secure"
global codes "/home/jrodriguez/understanding_NH/codes"
global results "/home/jrodriguez/understanding_NH/results"


local SE="hc2"

clear
clear matrix
clear mata
set more off
set maxvar 15000

/*
controls: choose if regression should include controls for parents: age, ethnicity, marital status, and education.
*/

local controls=0

*Choose: 1 if produce income graph for employed at baseline
*Choose: 0 if produce income graph for unemployed at baseline
*Choose: 3 if total
local emp=3

use "$results/Income/data_income.dta", clear

drop total_income_y0 gross_y0 gross_nominal_y0 grossv2_y0 employment_y0 /*
*/ fs_y0 afdc_y0 sup_y0 eitc_state_y0 eitc_fed_y0
forvalues x=1/9{
	local z=`x'-1
	rename total_income_y`x' total_income_y`z'
	rename gross_y`x' gross_y`z'
	rename grossv2_y`x' grossv2_y`z'
	rename gross_nominal_y`x' gross_nominal_y`z'
	rename employment_y`x' employment_y`z'
	rename afdc_y`x' afdc_y`z'
	rename fs_y`x' fs_y`z'
	rename sup_y`x' sup_y`z'
	rename eitc_fed_y`x' eitc_fed_y`z'
	rename eitc_state_y`x' eitc_state_y`z'

}



*Many missing obs
drop total_income_y10


*****************************************
*****************************************
*THE FIGURES
*****************************************
*****************************************

*Dropping 50 adults with no information on their children
count
qui: do "$codes/income/drop_50.do"
count

*Control variables (and recovering p_assign)
qui: do "$codes/income/Xs.do"
if `controls'==1{

	
	local control_var age_ra i.marital i.ethnic d_HS2 higrade i.pastern2
}

*Sample
if `emp'==1{
	keep if emp_baseline==1
}
else if `emp'==0{
	keep if emp_baseline==0

}

*dummy RA for ivqte
gen d_ra = .
replace d_ra = 1 if p_assign=="E"
replace d_ra = 0 if p_assign=="C"

*Getting child age info
tempfile data_aux
save `data_aux', replace
use "$databases/Youth_original2.dta", clear
keep sampleid kid1dats
destring sampleid, force replace
destring kid1dats, force replace
format kid1dats %td
gen year_birth=yofd(kid1dats)
drop kid1dats

bysort sampleid: egen seq_aux=seq()
reshape wide year_birth,i(sampleid) j(seq_aux	)
merge 1:1 sampleid using `data_aux'
keep if _merge==3
drop _merge

*child age at baseline
gen year_ra = substr(string(p_radaym),1,2)
destring year_ra, force replace
replace year_ra = 1900 + year_ra

gen agechild1_ra =  year_ra - year_birth1
gen agechild2_ra =  year_ra - year_birth2

*Dummy: at least 1 child less than 6 years of age by two years after baseline
gen d_young = (agechild1_ra + 2 <=6) | (agechild2_ra + 2 <=6)


*Save temporal data (before panel)
tempfile data_aux
save `data_aux', replace


*To panel
keep total_income_y* gross_y* employment_y* afdc_y* fs_y* sup_y* eitc_fed_y* /*
*/ eitc_state_y* d_young sampleid d_ra p_assign emp_baseline age_ra marital ethnic d_HS2 higrade pastern2

reshape long total_income_y gross_y employment_y afdc_y fs_y eitc_fed_y sup_y  /*
*/ eitc_state_y, i(sampleid) j(year)

drop if year>8

*Save panel data
tempfile data_panel
save `data_panel', replace


*Welfare
egen welfare=rowtotal(afdc_y fs_y)
egen eitc=rowtotal(eitc_fed_y eitc_state_y)


*************************************************************************************
*************************************************************************************
*************************************************************************************
/*COMPUTING TREATMENT EFFECTS ON INCOME/EARNINGS/WELFARE/NH/EITC*/

*************************************************************************************
*************************************************************************************
*************************************************************************************


*For t<=2
forvalues x=0/2{/*the sample loop*/

	if `x'<=1{

		qui xi: reg total_income_y i.p_assign if d_young==`x' & year<=2, vce(`SE')
		local dec0_emp`x' = _b[_Ip_assign_2]

		qui xi: reg gross_y i.p_assign if d_young==`x' & year<=2, vce(`SE')
		local dec1_emp`x' = _b[_Ip_assign_2]

		qui xi: reg welfare i.p_assign if d_young==`x' & year<=2, vce(`SE')
		local dec2_emp`x' = _b[_Ip_assign_2]

		qui xi: reg eitc i.p_assign if d_young==`x' & year<=2, vce(`SE')
		local dec3_emp`x' = _b[_Ip_assign_2]

		qui xi: reg sup_y i.p_assign if d_young==`x' & year<=2, vce(`SE')
		local dec4_emp`x' = _b[_Ip_assign_2]

		*shares
		qui xi: reg total_income_y i.p_assign if d_young==`x' & year<=2, vce(`SE')
		local tot = _b[_Ip_assign_2]

		forvalues j=1/4{
			local dec`j'_emp`x'=string(round(`dec`j'_emp`x''/1000,0.001),"%9.3f")/*rounding*/
		}
		


	}
	else{

		qui xi: reg total_income_y i.p_assign if year<=2, vce(`SE')
		local dec0_emp`x' = _b[_Ip_assign_2]

		qui xi: reg gross_y i.p_assign if year<=2, vce(`SE')
		local dec1_emp`x' = _b[_Ip_assign_2]

		qui xi: reg welfare i.p_assign if year<=2, vce(`SE')
		local dec2_emp`x' = _b[_Ip_assign_2]

		qui xi: reg eitc i.p_assign if year<=2, vce(`SE')
		local dec3_emp`x' = _b[_Ip_assign_2]

		qui xi: reg sup_y i.p_assign if year<=2, vce(`SE')
		local dec4_emp`x' = _b[_Ip_assign_2]

		*shares
		qui xi: reg total_income_y i.p_assign if year<=2, vce(`SE')
		local tot = _b[_Ip_assign_2]

		forvalues j=1/4{
			local dec`j'_emp`x'=string(round(`dec`j'_emp`x''/1000,0.001),"%9.3f")/*rounding*/
		}
		
	}
		
	
}











