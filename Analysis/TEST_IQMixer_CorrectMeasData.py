### test data correction is OK or not
### For example, use the correction parameters to correct the original calibration data
### to see the calibration data could be circled or not
import numpy as np
import matplotlib.pyplot as plt
import IQMixer.IQCalib as IQ
import csv
from scipy import interpolate

folder ="../../../MeasurementResult/"
filename = 'Sweep_5000MHz'
### Get IQ measurement data
data = []
with open(folder + filename + '.csv','r') as f:
    for line in f:
        data.append(map(str,line.split(',')))

frequency = np.asarray([int(float(data[i][0])/1e6) for i in range(0,len(data))])
I = np.asarray([float(data[i][1]) for i in range(0,len(data))])
Q = np.asarray([float(data[i][2].replace("\n", "")) for i in range(0,len(data))])
print frequency[0]

IQCorrectionfile ='IQMixer_Calib/20160803_1M_BOX/EllipseFit_0dBm_2000MHz_8000MHz.csv'
Icrr= []
Qcrr= []
for i in range(0, len(frequency)):
    paras = IQ.IQ_GetPara(IQCorrectionfile,frequency[i])
    Itemp, Qtemp = IQ.IQ_CorrtBarendsSingle(paras, I[i], Q[i])
    Icrr.append(Itemp)
    Qcrr.append(Qtemp)


#plt.plot(frequency, I)
plt.plot(4005, fc(4005),'.')
plt.plot(frequency, Icrr, '.')
plt.xlim([4000,4010])
plt.show()

### save calibrated result
crrfile = open(folder + filename + '_IQMixerCalibrated.csv', 'w')
fwrite = csv.writer(crrfile)

for i in range(0, len(Icrr)):
    fwrite.writerow([frequency[i], Icrr[i], Qcrr[i]])
crrfile.close()
"""
IcalG, QcalG = IQ.IQ_CorrtGao(paras,I,Q)
plt.plot(I,Q,'g')
plt.plot(IcalG,QcalG)
plt.show()

IcalB, QcalB = IQ.IQ_CorrtBarends(paras,I,Q)
plt.plot(I,Q,'g')
plt.plot(IcalB,QcalB,'r')

from scipy import signal
fs = 5e4

fwelch,Pwelch = signal.welch(Icrr, fs, nperseg=len(Icrr))
plt.loglog(fwelch,Pwelch,label='Icrr')

fwelch,Pwelch = signal.welch(I, fs, nperseg=len(Icrr))
plt.loglog(fwelch,Pwelch,label='I')
plt.show()
"""