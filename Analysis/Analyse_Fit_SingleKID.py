import matplotlib.pyplot as plt
import numpy as np
import Fitter # For circle fitting
import IQMixer.IQCalib as IQ
import FileReader as reader

def split_str(s, c, n):
    ### http://stackoverflow.com/questions/27227399/python-split-a-string-at-an-underscore
    ### Split file name to get center frequency
    words = s.split(c)
    return c.join(words[:n]), c.join(words[n:])
    
def Get_Data(result, bandwidth):
    span = float(result[len(result)-1][0])-float(result[2][0])
    interval = span/(len(result)-3)
    cut_num = len(result)-3-int(bandwidth/interval)
    if cut_num<0: cut_num = 0
    
    n = len(result)
    print "##### total number", n, "cut number", cut_num, "#####"
    freq = [float(result[i][0]) for i in range(2+cut_num/2, n-cut_num/2)]
    freq = np.asarray(freq)
    linear = [float(result[i][1]) for i in range(2+cut_num/2, n-cut_num/2)]
    phase = [float(result[i][2]) for i in range(2+cut_num/2, n-cut_num/2)]
    mag = np.asarray([float(result[i][3]) for i in range(2+cut_num/2, n-cut_num/2)])
    return freq, linear, phase, mag
    
def centerFreqTempPower(longfilename):
    ### Get temperature and center freq with float format
    ### from single long filename like: "20160104_-30dBm_5.373811875_0.0025_99.96mK"
    FirstSplit = split_str(str(longfilename).replace("[", "").replace("]", "").replace("'", "").replace("\\r", ""), "_", 2)
    SecondSplit = split_str(FirstSplit[1], "_", 1)
    Temp = split_str(SecondSplit[1], "_", 1)
    ThirdSplit = split_str(FirstSplit[0], "_", 1)
    Power = ThirdSplit[1].replace("dBm", "")
    Temp = split_str(Temp[1],"_", 1)
    T_float = float(Temp[0].replace("mK", ""))
    return T_float, float(SecondSplit[0]), Power

def Read_File(folder, filename):
    result = []
    with open(folder + filename,'r') as f:
        for line in f:
            result.append(map(str,line.split(',')))
    MeasState = centerFreqTempPower(filename.replace(".csv",""))
    return result, MeasState

def find_nearest(array,value):
    idx = (np.abs(array-value)).argmin()
    return idx

def SimpleQ(folder, filename, span):
    ### Read data from file
    result, MeasState = Read_File(folder, filename)
        
    freq, linear, phase, mag = Get_Data(result, span)
    linear_nor = np.asarray([linear[i]/linear[0] for i in range(0, len(freq))])
    minvalue = np.min(linear_nor)
    linear_nor_square = linear_nor**2
    Qpointvalue = (minvalue**2 + 1)/2.0
    Qpoint1 = find_nearest(linear_nor_square[:(len(freq)/2)], Qpointvalue)
    Qpoint2 = find_nearest(linear_nor_square[(len(freq)/2):], Qpointvalue) + len(freq)/2
    plt.plot(freq, linear_nor_square)
    plt.show()

    Q = MeasState[1]*1e9/(freq[Qpoint2]-freq[Qpoint1])
    Q_i = Q / minvalue
    Q_c = Q*Q_i/(Q_i - Q)
    print "Q", Q, "Qi", Q_i, "Qc", Q_c

def MillionQi(folder, filename, span):
    ### Read data from file
    result, MeasState = Read_File(folder, filename)

    freq, linear, phase, mag = Get_Data(result, span)
    n = len(freq)
    real = [linear[i] * np.cos(np.deg2rad(phase[i])) for i in range(0, n)]
    imag = [linear[i] * np.sin(np.deg2rad(phase[i])) for i in range(0, n)]
    complext = np.asarray([real[i] + 1j*imag[i] for i in range(0, n)])
    inverset = 1/complext
    para_guess = 1,0,1e5,1e5,np.median(freq),0
    a, a_err, phi0, phi0_err, Qi, Qi_err, Qc_scaled, Qc_scaled_err, fr, fr_err, aphi0, aphi0_err, result, Fit_result = Fitter.Fit_Million(freq, inverset, para_guess)
    fitcurve = a * (1 + Qi/Qc_scaled * np.exp(1j*phi0) * 1/(1 + 1j*2*Qi*(freq/fr-1)))* np.exp(1j*aphi0)
    #plt.plot(real, imag,'.')
    plt.plot(inverset.real, inverset.imag,'.')
    plt.plot(fitcurve.real, fitcurve.imag,'.r')
    #plt.plot(freq, real)
    #plt.plot(freq, inverset.real, 'r')
    #plt.plot(freq, imag)
    #plt.plot(freq, inverset.imag, 'r')
    plt.show()
    print np.rad2deg(phi0), len(inverset), len(complext)


def Fit_SingleKID(folder, filename, span):
    ### Read data from file
    result, MeasState = Read_File(folder, filename)
    freq, linear, phase, mag = Get_Data(result, span)
    n = len(freq)
    real = [linear[i] * np.cos(np.deg2rad(phase[i])) for i in range(0, n)]
    imag = [linear[i] * np.sin(np.deg2rad(phase[i])) for i in range(0, n)]
    
    x_c, x_c_err, y_c, y_c_err, radius, radius_err, circle_fit_report = Fitter.Fit_Circle(real, imag)
    
    Z_i = [real[i] + 1j*imag[i] for i in range(0, n)]
    Z_ii = (x_c + 1j*y_c - Z_i)*np.exp(-1j * np.arctan(y_c/x_c))

    #Fitter.plot_data_circle(real, imag, x_c, y_c, radius)
    #plt.show()
    
    ### Fit Phase
    data_phase = np.arctan2(Z_ii.imag, Z_ii.real)
    rotate_angle = np.pi-np.angle(Z_ii[0] + Z_ii[len(Z_ii)-1])
    Z_iic = Z_ii*np.exp(1j * rotate_angle)
    phase_rotated = np.arctan2(Z_iic.imag, Z_iic.real)

    ### Phase fit
    theta0_guess, fr_guess, Qr_guess = 0, np.median(freq), 1e5
    para_phase = theta0_guess, fr_guess, Qr_guess
    theta0, theta0_err, fr, fr_err, Qr, Qr_err, fit_report_phase = Fitter.Fit_Phase(freq, phase_rotated, para_phase)
    print fit_report_phase
    
    ### Qc and Qc error
    Qc = (np.absolute(x_c + 1j*y_c) + radius)/2/radius*Qr # Ref: Gao Thesis
    Qc_err0 = np.sqrt(2*(x_c**4*x_c_err**2 + y_c**4*y_c_err**2))/(x_c**2 + y_c**2)
    Qc_err1 = np.sqrt(Qc_err0**2/(x_c**2+y_c**2) + radius**2*radius_err**2)/(np.sqrt(x_c**2+y_c**2)+radius)
    Qc_err2 = np.sqrt(Qc_err1**2 + radius_err**2)
    Qc_err = np.sqrt(Qc_err2**2 + Qr_err**2)
    
    ### Qi and Qi error
    Qi = Qr * Qc/(Qc - Qr)
    Qi_err0 = np.sqrt(Qc_err**2 + Qr_err**2)
    Qi_err1 = np.sqrt(Qc**2*Qc_err**2 + Qr**2*Qr_err**2)/(Qc-Qr)
    Qi_err = np.sqrt(Qi_err0**2 + Qi_err1**2)
    print Qi_err, Qc_err, x_c_err, y_c_err, radius_err, Qr_err
    
    fitcurve = [-theta0 + 2*np.arctan(2 * Qr * (1 - freq[i]/fr)) for i in range(0, n)]
    #plt.plot(freq, data_phase)
    #plt.plot(freq, phase_rotated)
    #plt.plot(freq, fitcurve, 'r')
    #plt.show()
    #print "theta0", params['theta0'].value    
    #print "Temperature (mK)", MeasState[0], "fr from MagS21 (GHz)", MeasState[1], "fr from phase fit (GHz)", fr
    print "Qr", Qr, "Qi", Qi, "Qc", Qc
    #print "Circle fit residue", circle_residue #, "Phase fit residue", result.residual
    finalresult = []
    finalresult.append(MeasState[2])
    finalresult.append(MeasState[0])
    finalresult.append(MeasState[1])
    finalresult.append(fr/1e9)
    finalresult.append(fr_err)
    finalresult.append(Qr)
    finalresult.append(Qr_err)
    finalresult.append(Qc)
    finalresult.append(Qc_err)
    finalresult.append(Qi)
    finalresult.append(Qi_err)
    finalresult.append(filename)
    return finalresult

def Fit_SingleKID_Lo(folder, filename, span):
    ### Lorentizian fitting
    result, MeasState = Read_File(folder, filename)
    freq, linear, phase, mag = Get_Data(result, span)

    A1, A1_err, A2, A2_err, A3, A3_err, A4, A4_err, fr, fr_err, Qr, Qr_err, report = Fitter.Fit_SkewedLorentizian(freq, mag)
    fitcurve = [10*np.log10(A1 + A2*(f-fr) + (A3 + A4*(f-fr))/(1 + 4*Qr*Qr*((f-fr)/fr)**2)) for f in freq]
    minvalue = np.power(10, (np.amin(mag) - np.amax(mag))/10)
    Qi = Qr / minvalue
    Qc = Qr*Qi/(Qi - Qr)
    print Qr, Qi, Qc
    plt.plot(freq, mag, '.', linewidth=2, label="Data")
    plt.plot(freq, fitcurve, 'r-', linewidth=1, label="Fit")
    plt.xlabel('Normalized Frequency')
    plt.ylabel('S21 (dB)')
    plt.legend(loc=3)
    plt.gca().get_xaxis().get_major_formatter().set_useOffset(False)
    plt.show()
    
    #print report,fr
    #return A1, A2, A3, A4, fr, Qr

def Fit_7parameter(folder, filename, span):
    ### Read data from file
    result, MeasState = Read_File(folder, filename)
    freq, linear, phase, mag = Get_Data(result, span)
    n = len(freq)
    real = [linear[i] * np.cos(np.deg2rad(phase[i])) for i in range(0, n)]
    imag = [linear[i] * np.sin(np.deg2rad(phase[i])) for i in range(0, n)]
    comp = [real[i]+imag[i]*1j for i in range(0, n)]

    """
    Fit Circle
    Rotate and move data  to the origin
    """
    x_c, x_c_err, y_c, y_c_err, radius, radius_err, circle_fit_report = Fitter.Fit_Circle(real, imag)

    Z_i = [real[i] + 1j*imag[i] for i in range(0, n)]
    Z_ii = (x_c + 1j*y_c - Z_i)*np.exp(-1j * np.arctan(y_c/x_c))
    
    #Fitter.plot_data_circle(Z_ii.real, Z_ii.imag, x_c, y_c, radius)
    #plt.show()

    ### Fit Phase
    data_phase = np.arctan2(Z_ii.imag, Z_ii.real)

    rotate_angle = np.pi-np.angle(Z_ii[0] + Z_ii[len(Z_ii)-1])
    Z_iic = Z_ii*np.exp(1j * rotate_angle)
    phase_rotated = np.arctan2(Z_iic.imag, Z_iic.real)

    ### Phase fit
    theta0_guess, fr_guess, Qr_guess = 0, np.median(freq), 1e5
    para_phase = theta0_guess, fr_guess, Qr_guess
    theta0, theta0_err, fr, fr_err, Qr, Qr_err, fit_report_phase = Fitter.Fit_Phase(freq, phase_rotated, para_phase)
    print fit_report_phase
    Qc = (np.absolute(x_c + 1j*y_c) + radius)/2/radius*Qr # Ref: Gao Thesis
    Qi = Qr * Qc/(Qc - Qr)
    print Qi
    """
    fitphasecurve = [-theta0 + 2*np.arctan(2 * Qr * (1 - freq[i]/fr)) for i in range(0, n)]
    plt.plot(freq, phase_rotated)
    plt.plot(freq, fitphasecurve, 'r')
    plt.show()
    """
    #print "theta0", params['theta0'].value    
    #print "Temperature (mK)", MeasState[0], "fr from MagS21 (GHz)", MeasState[1], "fr from phase fit (GHz)", fr
    #print "Qr", Qr, "Qi", Qi, "Qc", Qc
    #print "Circle fit residue", circle_residue #, "Phase fit residue", result.residual
    a = 3.636
    alpha = 0.381
    tau = 0
    phi0 = theta0-np.arctan2(x_c, y_c)+rotate_angle + np.pi
    estimateparas = [a,alpha,tau,phi0,fr,Qr,Qc]
    
    a, a_err, alpha, alpha_err, tau, tau_err, phi0, phi0_err, fr, fr_err, Qr, Qr_err, Qc, Qc_err, sevenparafittingresult = Fitter.Fit_7para(freq, comp, estimateparas)
    sevenpara_result = a, a_err, alpha, alpha_err, tau, tau_err, phi0, phi0_err, fr, fr_err, Qr, Qr_err, Qc, Qc_err, sevenparafittingresult
    fit7paracurve = sevenpara_result[0]*np.exp(1j*sevenpara_result[2]) * np.exp(-2*np.pi*1j*freq*sevenpara_result[4]) * (1 - (sevenpara_result[10]/sevenpara_result[12]*np.exp(1j*sevenpara_result[6]))/(1 + 2*1j*sevenpara_result[10]*(freq-sevenpara_result[8])/sevenpara_result[8]))
    #plt.plot(real,imag)
    #plt.plot(fit7paracurve.real, fit7paracurve.imag, 'r')
    #plt.show()
    
    Qi = sevenpara_result[10] * sevenpara_result[12]/(sevenpara_result[12] - sevenpara_result[10])
    print Qi
    
    finalresult = []
    finalresult.append(MeasState[2])
    finalresult.append(MeasState[0])
    finalresult.append(MeasState[1])
    finalresult.append(fr/1e9)
    finalresult.append(fr_err/fr)
    finalresult.append(Qr)
    finalresult.append(Qr_err/Qr)
    finalresult.append(Qc)
    finalresult.append(Qi)
    finalresult.append(filename)
    
    return finalresult
    
def Fit_7parameterIQ1(freq, comp, tau):
    a = 1
    alpha = 0
    
    phi0 = 0#theta0-np.arctan2(x_c, y_c)+rotate_angle + np.pi
    estimateparas = [a,alpha,tau,phi0,freq[len(freq)/2],5e4,5e4]
    
    a, a_err, alpha, alpha_err, tau, tau_err, phi0, phi0_err, fr, fr_err, Qr, Qr_err, Qc, Qc_err, sevenparafittingresult = Fitter.Fit_7para(freq, comp, estimateparas)
    sevenpara_result = a, a_err, alpha, alpha_err, tau, tau_err, phi0, phi0_err, fr, fr_err, Qr, Qr_err, Qc, Qc_err, sevenparafittingresult
    #fit7paracurve = a * np.exp(1j*alpha) * np.exp(-2*np.pi*1j*freq*tau) * (1 - (Qr/Qc*np.exp(1j*phi0))/(1 + 2*1j*Qr*(freq-fr)/fr))

    #plt.plot(real,imag)
    #plt.plot(fitIQ.real, fitIQ.imag, '+')
    #plt.plot(fit7paracurve.real, fit7paracurve.imag, 'r')
    #plt.show()
    
    Qi = sevenpara_result[10] * sevenpara_result[12]/(sevenpara_result[12] - sevenpara_result[10])
    print Qi
    
    finalresult = []
    finalresult.append(a)
    finalresult.append(a_err/a)
    finalresult.append(alpha)
    finalresult.append(alpha_err/alpha)
    finalresult.append(tau)
    finalresult.append(tau_err/tau)
    finalresult.append(phi0)
    finalresult.append(phi0_err/phi0)
    finalresult.append(fr)
    finalresult.append(fr_err/fr)
    finalresult.append(Qr)
    finalresult.append(Qr_err/Qr)
    finalresult.append(Qc)
    finalresult.append(Qc_err/Qc)
    finalresult.append(Qi)
    
    return finalresult
    
def Fit_7parameterIQ2(freq, comp, para_guess):

    #Fit Circle
    #Rotate and move data to the origin
    n = len(freq)
    I = comp.real
    Q = comp.imag
    x_c, x_c_err, y_c, y_c_err, radius, radius_err, circle_fit_report = Fitter.Fit_Circle(I, Q)

    Z_i = [I[i] + 1j*Q[i] for i in range(0, n)]
    Z_ii = (x_c + 1j*y_c - Z_i)*np.exp(-1j * np.arctan(y_c/x_c))
    
    #Fitter.plot_data_circle(Z_ii.real, Z_ii.imag, x_c, y_c, radius)
    #plt.show()

    ### Fit Phase
    data_phase = np.arctan2(Z_ii.imag, Z_ii.real)

    rotate_angle = np.pi-np.angle(Z_ii[0] + Z_ii[len(Z_ii)-1])
    Z_iic = Z_ii*np.exp(1j * rotate_angle)
    phase_rotated = np.arctan2(Z_iic.imag, Z_iic.real)

    ### Phase fit
    theta0_guess, fr_guess, Qr_guess = 0, np.median(freq), 1e5
    para_phase = theta0_guess, fr_guess, Qr_guess
    theta0, theta0_err, fr, fr_err, Qr, Qr_err, fit_report_phase = Fitter.Fit_Phase(freq, phase_rotated, para_phase)
    print fit_report_phase
    Qc = (np.absolute(x_c + 1j*y_c) + radius)/2/radius*Qr # Ref: Gao Thesis
    Qi = Qr * Qc/(Qc - Qr)
    print Qi
    """
    fitphasecurve = [-theta0 + 2*np.arctan(2 * Qr * (1 - freq[i]/fr)) for i in range(0, n)]
    plt.plot(freq, phase_rotated)
    plt.plot(freq, fitphasecurve, 'r')
    plt.show()
    """
    a, a_err, alpha, alpha_err, tau, tau_err, phi0, phi0_err, fr, fr_err, Qr, Qr_err, Qc, Qc_err, sevenparafittingresult = Fitter.Fit_7para(freq, comp, para_guess)
    sevenpara_result = a, a_err, alpha, alpha_err, tau, tau_err, phi0, phi0_err, fr, fr_err, Qr, Qr_err, Qc, Qc_err, sevenparafittingresult
    fit7paracurve = a * np.exp(1j*alpha) * np.exp(-2*np.pi*1j*freq*tau) * (1 - (Qr/Qc*np.exp(1j*phi0))/(1 + 2*1j*Qr*(freq-fr)/fr))

    #plt.plot(comp.real, comp.imag)
    #plt.plot(fit7paracurve.real, fit7paracurve.imag, 'r')
    #plt.show()
    
    Qi = sevenpara_result[10] * sevenpara_result[12]/(sevenpara_result[12] - sevenpara_result[10])
    print Qi
    
    finalresult = []
    finalresult.append(a)
    finalresult.append(a_err/a)
    finalresult.append(alpha)
    finalresult.append(alpha_err/alpha)
    finalresult.append(tau)
    finalresult.append(tau_err/(tau+1))
    finalresult.append(phi0)
    finalresult.append(phi0_err/phi0)
    finalresult.append(fr)
    finalresult.append(fr_err/fr)
    finalresult.append(Qr)
    finalresult.append(Qr_err/Qr)
    finalresult.append(Qc)
    finalresult.append(Qc_err/Qc)
    finalresult.append(x_c)
    finalresult.append(x_c_err/x_c)
    finalresult.append(y_c)
    finalresult.append(y_c_err/y_c)
    finalresult.append(radius)
    finalresult.append(radius_err/radius)
    
    return finalresult
    
def Fit_IQ_Sweep(freq, complexIQ):
    n = len(freq)
    """
    Fit Circle
    Rotate and move data  to the origin
    """
    x_c, x_c_err, y_c, y_c_err, radius, radius_err, circle_fit_report = Fitter.Fit_Circle(complexIQ.real, complexIQ.imag)
    Z_ii = (x_c + 1j*y_c - complexIQ)#*np.exp(-1j * np.arctan(y_c/x_c))
    """
    ### Fit result and data
    #Fitter.plot_data_circle(complexIQ.real, complexIQ.imag, x_c, y_c, radius)
    plt.plot(Z_ii.real, Z_ii.imag)
    plt.show()
    """
    ### Fit Phase
    data_phase = np.arctan2(Z_ii.imag, Z_ii.real)
    rotate_angle = np.pi-np.angle(Z_ii[0] + Z_ii[n-1])
    Z_iir = Z_ii*np.exp(1j * rotate_angle)
    phase_rotated = np.arctan2(Z_iir.imag, Z_iir.real)
    theta0_guess, fr_guess, Qr_guess = 0, np.median(freq), 1e5
    para_phase = theta0_guess, fr_guess, Qr_guess
    theta0, theta0_err, fr, fr_err, Qr, Qr_err, fit_report_phase = Fitter.Fit_Phase(freq, phase_rotated, para_phase)
    print fit_report_phase

    ### Qc and Qc error
    Qc = (np.absolute(x_c + 1j*y_c) + radius)/2/radius*Qr # Ref: Gao Thesis
    Qc_err0 = np.sqrt(2*(x_c**4*x_c_err**2 + y_c**4*y_c_err**2))/(x_c**2 + y_c**2)
    Qc_err1 = np.sqrt(Qc_err0**2/(x_c**2+y_c**2) + radius**2*radius_err**2)/(np.sqrt(x_c**2+y_c**2)+radius)
    Qc_err2 = np.sqrt(Qc_err1**2 + radius_err**2)
    Qc_err = np.sqrt(Qc_err2**2 + Qr_err**2)
    
    ### Qi and Qi error
    Qi = Qr * Qc/(Qc - Qr)
    Qi_err0 = np.sqrt(Qc_err**2 + Qr_err**2)
    Qi_err1 = np.sqrt(Qc**2*Qc_err**2 + Qr**2*Qr_err**2)/(Qc-Qr)
    Qi_err = np.sqrt(Qi_err0**2 + Qi_err1**2)

    return x_c, x_c_err, y_c, y_c_err, radius, radius_err, circle_fit_report, theta0, theta0_err, fr, fr_err, Qr, Qr_err, Qc, Qc_err, Qi, Qi_err, fit_report_phase

def GetFr(sweepdata_folder, sweepdata_file, IQCalibrationfile, IQReffolder, IQReffilename):
    ### Read IQ Sweep data
    freq, I, Q = reader.ReadSweep(sweepdata_folder, sweepdata_file)
    ### Get IQ Mixer calibration data for sweep data frequency
    paras = IQ.IQ_GetPara(IQCalibrationfile, int(round(freq[len(freq)/2]/1e6)))
    ### Calibrate IQ Sweep data
    I_mixercalibrated, Q_mixercalibrated = IQ.IQ_CorrtBarends(paras,I,Q)

    ### Normalize calibrated IQ Sweep data to IQ reference data
    ### Get complex IQ
    IQ_normalized = IQ.IQ_Normalize_Sweep(freq, I_mixercalibrated, Q_mixercalibrated, IQReffolder, IQReffilename)
    x_c, x_c_err, y_c, y_c_err, radius, radius_err, circle_fit_report, theta0, theta0_err, fr, fr_err, Qr, Qr_err, Qc, Qc_err, Qi, Qi_err, fit_report_phase = Fit_IQ_Sweep(freq, IQ_normalized)
    return int(round(fr))
    
def Fit_IQ_Noise(freq, sweepcomplexIQ):
    """
    Fit Circle
    Rotate and move data  to the origin
    """
    n = len(freq)
    x_c, x_c_err, y_c, y_c_err, radius, radius_err, circle_fit_report = Fitter.Fit_Circle(sweepcomplexIQ.real, sweepcomplexIQ.imag)
    Z_ii = (x_c + 1j*y_c - sweepcomplexIQ)#*np.exp(-1j * np.arctan(y_c/x_c))
    """
    ### Fit result and data
    #Fitter.plot_data_circle(complexIQ.real, complexIQ.imag, x_c, y_c, radius)
    plt.plot(Z_ii.real, Z_ii.imag)
    plt.show()
    """
    ### Fit Phase
    data_phase = np.arctan2(Z_ii.imag, Z_ii.real)
    rotate_angle = np.pi-np.angle(Z_ii[0] + Z_ii[n-1])
    Z_iir = Z_ii*np.exp(1j * rotate_angle)
    phase_rotated = np.arctan2(Z_iir.imag, Z_iir.real)
    theta0_guess, fr_guess, Qr_guess = 0, np.median(freq), 1e5
    para_phase = theta0_guess, fr_guess, Qr_guess
    theta0, theta0_err, fr, fr_err, Qr, Qr_err, fit_report_phase = Fitter.Fit_Phase(freq, phase_rotated, para_phase)
    print fit_report_phase
#filename = '20160518_-10dBm_4.99347845_0.0025_707.804mK.csv'
#folder = '../../../MeasurementResult/20160516_Nb154nmCry3/'
#span = 2e6
#a = SimpleQ(folder, filename, span)
#b = MillionQi(folder, filename, span)
#result = Fit_SingleKID(folder, filename, span)
#result = Fit_SingleKID_Lo(folder, filename, span)
#result = Fit_7parameter(folder, filename)
#print result