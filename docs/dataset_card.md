# Dataset Card: PhysioNet Fantasia Database

## Dataset Overview
- **Name**: PhysioNet Fantasia Database
- **Curators**: Beth Israel Deaconess Medical Center, Boston, MA; Harvard Medical School
- **Official URL**: [https://physionet.org/content/fantasia/](https://physionet.org/content/fantasia/)
- **License**: PhysioNet Open Access License
- **Modality**: Simultaneous Electrocardiogram (Lead II) and Thoracic Plethysmography (Respiration)
- **Sampling Frequency**: $250\text{ Hz}$ continuous
- **Dynamic Voltage Range**:
  - ECG: Mean $5.744\text{ mV}$ to $11.770\text{ mV}$
  - RESP: Mean $7.626\text{ V}$ to $11.883\text{ V}$

## Demographic Cohort
- **Total Cohort Analyzed**: 20 rigorously screened healthy human subjects
  - Young Adult Controls (Class 0): 10 subjects (5 Female, 5 Male), Age $27.3 \pm 4.6$ years (range: 21–34)
  - Elderly Risk Cohort (Class 1): 10 subjects (5 Female, 5 Male), Age $73.7 \pm 3.4$ years (range: 68–81)
- **Inclusion Criteria**: Clinically verified healthy subjects without overt cardiovascular pathology or chronic medication.
- **Experimental Protocol**: Continuous supine resting state while watching the movie *Fantasia* to maintain relaxed wakefulness without emotional stressors.

## Clinical Risk Proxy Rationale
The classification task targets:
- Class 0: Healthy Young Controls (intact autonomic plasticity, strong vagal tone, high RSA)
- Class 1: Elderly Autonomic Risk Proxy (vagal blunting, sinoatrial remodeling, impaired baroreflex sensitivity)
This target acts as a biophysical proxy for autonomic degradation and stress vulnerability.
