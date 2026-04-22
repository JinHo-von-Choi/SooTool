# Medical Module

생체 측정 및 임상 계산 도구 모음.

## 도구 목록

### medical.bmi

WHO 기준 BMI 계산 및 분류.

**수식**: BMI = weight_kg / height_m²  
**소수점**: 2자리 (HALF_EVEN)  
**카테고리**: underweight(<18.5), normal(18.5~25), overweight(25~30), obese_1(30~35), obese_2(35~40), obese_3(>=40)

**출처**: World Health Organization. Obesity and overweight fact sheet. https://www.who.int/news-room/fact-sheets/detail/obesity-and-overweight

---

### medical.bsa

체표면적(BSA) 계산. 두 가지 공식 지원.

**DuBois 공식** (`method=dubois`): BSA = 0.007184 × h^0.725 × w^0.425  
**Mosteller 공식** (`method=mosteller`): BSA = sqrt(h × w / 3600)  
**소수점**: 4자리

**출처**:
- Du Bois D, Du Bois EF. A formula to estimate the approximate surface area if height and weight be known. *Arch Intern Med.* 1916;17:863–871.
- Mosteller RD. Simplified calculation of body-surface area. *N Engl J Med.* 1987;317(17):1098.

---

### medical.dose_weight_based

체중 기반 약물 용량 계산. 최대 용량(max_dose) 초과 시 cap 적용.

**수식**: dose = min(weight_kg × dose_per_kg, max_dose)

---

### medical.egfr

CKD-EPI 2021 race-free 방정식 기반 eGFR 계산. KDIGO 2012 기준 CKD stage 반환.

**수식**:
```
eGFR = 142 × min(Scr/κ, 1)^α × max(Scr/κ, 1)^-1.200 × 0.9938^age [× 1.012 if female]
```

| 성별 | κ | α |
|-|-|-|
| female | 0.7 | -0.241 |
| male | 0.9 | -0.302 |

**CKD Stage (KDIGO 2012)**:

| Stage | eGFR (mL/min/1.73m²) |
|-|-|
| G1 | >= 90 |
| G2 | 60-89 |
| G3a | 45-59 |
| G3b | 30-44 |
| G4 | 15-29 |
| G5 | < 15 |

**출처**:
- Inker LA, et al. New Creatinine- and Cystatin C-Based Equations to Estimate GFR without Race. *N Engl J Med.* 2021;385(19):1737–1749.
- Kidney Disease: Improving Global Outcomes (KDIGO) CKD Work Group. *Kidney Int Suppl.* 2013;3:1–150.

---

### medical.pregnancy_weeks

LMP 기준 임신 주수 및 분만예정일(EDD) 계산.

**수식**: EDD = LMP + 280일 (Naegele 법칙)  
**클램프**: 0~42주 (ACOG post-term 정의)

**삼분기 경계**:
- 1삼분기: 0~13주
- 2삼분기: 14~27주
- 3삼분기: 28주~

**출처**: American College of Obstetricians and Gynecologists (ACOG). Methods for Estimating the Due Date. Committee Opinion No. 700. May 2017.
