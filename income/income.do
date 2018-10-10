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


*Dropping 50 adults with no information on their children
count
qui: do "$codes/income/drop_50.do"
count

*Control variables (and recovering p_assign)
qui: do "$codes/income/Xs.do"
if `controls'==1{

	
	local control_var age_ra i.marital i.ethnic d_HS2 higrade i.pastern2
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


*This is for computing incremental earnings
log using "$results/ls/mean_earnings.txt", replace text
sum gross_y if year<=2 & p_assign == "C" & d_young ==1
log close

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

		foreach inc in total_income_y gross_y welfare eitc sup_y{
			qui: sum `inc' if d_young==`x' & year<=2
			local mean_`inc'_`x' =string(round( r(mean)/1000,0.001),"%9.3f")
			qui xi: reg `inc' i.p_assign `control_var' if d_young==`x' & year<=2, vce(`SE')
			local te_`inc'_`x' =string(round( _b[_Ip_assign_2]/1000,0.001),"%9.3f")
			local se_`inc'_`x' =string(round( _se[_Ip_assign_2]/1000,0.001),"%9.3f")
			qui: test _Ip_assign_2=0
			local pv=r(p)

			if `pv'<=.01{
				local ast_`inc'_`x' ="***"	
			}
			else if `pv'<=.05 {
				local ast_`inc'_`x' ="**"		
			}
			else if `pv'<=.1 {
				local ast_`inc_`x'' ="*"		
			}
			else{
				local ast_`inc'_`x'=""
			}

			



		}

		
		


	}
	else{

		foreach inc in total_income_y gross_y welfare eitc sup_y{
			qui: sum `inc' if year<=2
			local mean_`inc'_`x' =string(round( r(mean)/1000,0.001),"%9.3f")
			qui xi: reg `inc' i.p_assign `control_var' if year<=2, vce(`SE')
			local te_`inc'_`x' =string(round( _b[_Ip_assign_2]/1000,0.001),"%9.3f")
			local se_`inc'_`x' =string(round( _se[_Ip_assign_2]/1000,0.001),"%9.3f")
			qui: test _Ip_assign_2=0
			local pv=r(p)

			if `pv'<=.01{
				local ast_`inc'_`x' ="***"	
			}
			else if `pv'<=.05 {
				local ast_`inc'_`x' ="**"		
			}
			else if `pv'<=.1 {
				local ast_`inc'_`x' ="*"		
			}
			else{
				local ast_`inc'_`x'=""
			}



		    *testing for diff effects
			qui xi: reg `inc' d_ra d_young c.d_ra#c.d_young  `control_var'  if year<=2, vce(`SE')
			qui: test c.d_ra#c.d_young=0
			local pv_`inc'=string(round(r(p),0.001),"%9.3f")



		}

	
	
		
	}
		
	
}



*************************************************************************************
*************************************************************************************
*************************************************************************************
/*GENERATING TABLE*/

file open tab_dec using "$results/Income/table_income.tex", write replace
file write tab_dec "\begin{tabular}{llccccc}"_n
file write tab_dec "\hline"_n
file write tab_dec "Variable &       & Old &       & Young   &       & Overall \bigstrut\\"_n
file write tab_dec "\cline{1-1}\cline{3-7}      &       &       &       &       &       &  \bigstrut[t]\\"_n

file write tab_dec "\textbf{Panel A.} &       & \multicolumn{5}{c}{\textbf{Earnings}} \\"_n
file write tab_dec "Treatment effect &       & `te_gross_y_0'`ast_gross_y_0'   &       & `te_gross_y_1'`ast_gross_y_1'    &       & `te_gross_y_2'`ast_gross_y_2'  \\"_n
file write tab_dec "&       & (`se_gross_y_0')   &       & (`se_gross_y_1')   &      & (`se_gross_y_2') \\"_n
file write tab_dec "Dependent mean &       & `mean_gross_y_0'   &       & `mean_gross_y_1'   &       & `mean_gross_y_2' \\"_n
file write tab_dec "p-val for diff. effects &       &   \multicolumn{5}{c}{ `pv_gross_y'} \\"_n
file write tab_dec "      &       &       &       &       &       &  \\"_n

file write tab_dec "\textbf{Panel B.} &       & \multicolumn{5}{c}{\textbf{Welfare}} \\"_n
file write tab_dec "Treatment effect &       & `te_welfare_0'`ast_welfare_0'   &       & `te_welfare_1'`ast_welfare_1'   &       & `te_welfare_2'`ast_welfare_2' \\"_n
file write tab_dec "&       & (`se_welfare_0')   &       & (`se_welfare_1')   &      & (`se_welfare_2') \\"_n
file write tab_dec "Dependent mean &       & `mean_welfare_0'   &       & `mean_welfare_1'   &       & `mean_welfare_2' \\"_n
file write tab_dec "p-val for diff. effects &       &  \multicolumn{5}{c}{ `pv_welfare'} \\"_n
file write tab_dec "      &       &       &       &       &       &  \\"_n

file write tab_dec "\textbf{Panel C.} &       & \multicolumn{5}{c}{\textbf{EITC}} \\"_n
file write tab_dec "Treatment effect &       & `te_eitc_0'`ast_eitc_0'   &       & `te_eitc_1'`ast_eitc_1'   &       & `te_eitc_2'`ast_eitc_2' \\"_n
file write tab_dec "&       & (`se_eitc_0')   &       & (`se_eitc_1')   &      & (`se_eitc_2') \\"_n
file write tab_dec "Dependent mean &       & `mean_eitc_0'   &       & `mean_eitc_1'   &       & `mean_eitc_2' \\"_n
file write tab_dec "p-val for diff. effects &       &   \multicolumn{5}{c}{`pv_eitc'} \\"_n
file write tab_dec "      &       &       &       &       &       &  \\"_n

file write tab_dec "\textbf{Panel D.} &       & \multicolumn{5}{c}{\textbf{New Hope}} \\"_n
file write tab_dec "Treatment effect &       & `te_sup_y_0'`ast_sup_y_0'   &       & `te_sup_y_1'`ast_sup_y_1'   &       & `te_sup_y_2'`ast_sup_y_2' \\"_n
file write tab_dec "&       & (`se_sup_y_0')   &       & (`se_sup_y_1')   &      & (`se_sup_y_2') \\"_n
file write tab_dec "Dependent mean &       & `mean_sup_y_0'   &       & `mean_sup_y_1'   &       & `mean_sup_y_2' \\"_n
file write tab_dec "p-val for diff. effects &       &   \multicolumn{5}{c}{ `pv_sup_y'} \\"_n

file write tab_dec "      &       &       &       &       &       &  \\"_n


file write tab_dec "\textbf{Panel E.} &       & \multicolumn{5}{c}{\textbf{Total income}} \\"_n
file write tab_dec "Treatment effect &       & `te_total_income_y_0'`ast_total_income_y_0'   &       & `te_total_income_y_1'`ast_total_income_y_1'   &       & `te_total_income_y_2'`ast_total_income_y_2' \\"_n
file write tab_dec "&       & (`se_total_income_y_0')   &       & (`se_total_income_y_1')   &      & (`se_total_income_y_2') \\"_n
file write tab_dec "Dependent mean &       & `mean_total_income_y_0'   &       & `mean_total_income_y_1'   &       & `mean_total_income_y_2' \\"_n
file write tab_dec "p-val for diff effects &       &   \multicolumn{5}{c}{ `pv_total_income_y'} \\"_n
file write tab_dec "      &       &       &       &       &       &  \\"_n

file write tab_dec "\hline"_n
file write tab_dec "\end{tabular}"_n
file close tab_dec


display `pv_gross_y'


*************************************************************************************
*************************************************************************************
*************************************************************************************







