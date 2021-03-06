'''
Created on Dec 26, 2012

@author: dstrauss

creating some routines to make a convolutional net. especially one that works in parallel

Works in parallel
Maps over a list of data. This means that it can handle looking for a sparse separation in 
multiple channels simultaneously. This feature has direct applicability for the hypervelocity
dust experiment data

This code is more "flexible" than the standard convNet, but accomplishes the same goal.



'''

import scipy.io as spio
import numpy as np
from dataModel import dtm
from lassoUpdate import lasso
import weightsUpdate
from time import time
from mpi4py import MPI
import sys



def main():
    ''' main routine '''
    comm = MPI.COMM_WORLD
    rk = comm.Get_rank()
    nProc = comm.Get_size()
    
    if len(sys.argv) <= 2:
        ''' complain '''
        print 'need  arguments: plain or fft?'
        return 0
    else:
        if sys.argv[1] == 'plain':
            plain = True
        elif sys.argv[1] == 'fft':
            plain = False
        else:
            plain = True
            
    if len(sys.argv) >= 3:
        dts = sys.argv[2]
    else:
        dts = 'plmr'
            
    ''' set the parameters for how big of a problem to grab'''   
    m = 50000 # size of data
    p = 25 # number of filters
    q = 300 # length of filters
    
    if dts == 'plmr':
        rho = 1 # l1 internal parameter
        lmb = 0.005 # l1 weighting
        xi = 0.2 # weights update parameter
        ch = 1 # number of channels
    elif dts == 'mpk':
        rho = 0.1
        lmb = 4e-6
        xi = 0.2
        ch = 3

    ''' load data, given rank '''
    y = getData(m,dts,ch,rank=rk)
    
    ''' initialize weights '''    
    wt = [weightInit(p,q,comm) for ix in xrange(ch)]
    
    A = [dtm(m,p,q,fourier=not plain) for ix in xrange(ch)]
        
    for Q in A:
        print Q.n
            
    optl1 = lasso(m,A[0].n,rho,lmb,ch)
        
    newWW = [weightsUpdate.weightsUpdate(m,p,q,xi) for ix in xrange(ch)]
    print newWW[0].m
    for WWl,wl in zip(newWW,wt):
        WWl.wp = wl
    
    rrz = list()
    gap = list()
    ''' begin loop '''
    for itz in range(1000):
        ws = [WWl.wp for WWl in newWW]
        for Q,w in zip(A,wt) :
            Q.changeWeights(w)
        tm = time()
        z = optl1.solveL1(y, A)
        rrz = optl1.rrz # .append(optl1.rrz.pop())
        gap = optl1.gap #.append(optl1.gap.pop())
        print 'rank ' + repr(rk) + ' of ' + repr(nProc) +  ' solved l1 itr: ' + repr(itz) + ' time: ' + repr(time()-tm)
        tm = time()
        
        if plain:
            wmx = [WL.updatePlain(yl, wtl, zl) for WL,yl,wtl,zl in zip(newWW,y,wt,z)]
        else:
            wmx = [WL.updateFourier(yl, wtl, zl) for WL,yl,wtl,zl in zip(newWW,y,wt,z)]
            
        print 'rank ' + repr(rk) + ' of ' + repr(nProc) +  ' solved w update itr: ' + repr(itz) + ' time: ' + repr(time()-tm)
        tm = time()
        wt = [weightAgg(wmxl,p,q,comm) for wmxl in wmx]
        wp = [WL.wp for WL in newWW]
        print 'rank ' + repr(rk) + ' of ' + repr(nProc) +  ' have new weights itr: ' + repr(itz) + ' time: ' + repr(time()-tm)
        outd = {'itr':itz, 'y':y, 'z':z, 'wt':wt,'wp':wp,'m':m,'p':p,'q':q, 'rho':rho,'lmb':lmb, 'xi':xi, 'rrz':rrz,'gap':gap, 'ws':ws }
        
        if plain & (dts == 'plmr'):
            spio.savemat('miniOut_' + repr(p) + '_' + repr(nProc) + '_' + repr(rk), outd)
        elif plain & (dts == 'mpk'):
            spio.savemat('miniOutMPK_' + repr(nProc) + '_' + repr(rk), outd)
        else:
            spio.savemat('plainOut_' + repr(nProc) + '_' + repr(rk), outd) 
            
    ''' return these values if I chance to run this in an interactive Python shell'''
    return y,z,optl1,A,wt
    
    ''' for n iterations '''
    
    ''' calculate local weights '''
    
    ''' all reduce '''
    
    
def weightAgg(U,p,q,comm):
    ''' aggregation for weights '''
    
    wmx = np.zeros((q,p))
    
    wmx = comm.allreduce(U,wmx,op=MPI.SUM)
    
    wmx = wmx/comm.Get_size()
    
    wt = np.zeros((q,p))
    
    for ix in xrange(p):
        nrm = np.linalg.norm(wmx[:,ix])
        if nrm > 1:
            wt[:,ix] = wmx[:,ix]/nrm
        elif nrm < 0.95:
            wt[:,ix] = 0.95*wmx[:,ix]/(nrm)
        else:
            wt[:,ix] = wmx[:,ix]
    
    return wt
            
def weightInit(p,q,comm):
    ''' create some initial, normalized weights '''
    rank = comm.Get_rank()
    if rank == 0:
        wt = np.random.randn(q,p)/np.sqrt(q)
    else:
        wt = None
        
    return comm.bcast(wt,root=0)
        
    
    

def getData(m,dts,ch,rank=0):
    ''' simple function to grab data 
    returns zero mean, normalized data sample
    '''
    
#    import matplotlib.pyplot as plt
    if dts == 'plmr':
        D = spio.loadmat('../data/plmr.mat')
        cix = 1000 + rank*m # np.random.random_integers(0,upb,1)
        slz = slice(cix,cix+m)
        y = D['fs'][slz].astype('complex128').flatten()
        y = y - np.mean(y)
        y = [y]
        
    if dts == 'mpk':
        nbr = (np.floor(rank/2) + 900).astype('int64')
        D = spio.loadmat('../data/lcd' + repr(nbr) + '.mat')
        
        y = list()
        for ix in xrange(ch):
            yl = D['alldat'][0][ix][:m].astype('complex128').flatten()
            yl = yl-np.mean(yl)
            y.append(yl)
    
    print 'shape of y ' + repr(len(y))
    print [yl.shape for yl in y]
    return y
    
def testMain():
    import matplotlib.pyplot as plt
    y,z,optl1,A,wt = main()
    
    D = spio.loadmat('fakew.mat') 
    w = D['w']
    
    plt.figure(10)
    plt.plot(z.real)
    
    plt.figure(11)
    plt.plot(range(y.size),y, range(y.size), A.mtx(z).real)
    
    plt.figure(12)
    plt.plot(range(w.shape[0]),w[:,0], range(wt.shape[0]),wt[:,0])
    
    return y,z,optl1,A,wt,w
    
    
if __name__ == '__main__':
    main()
    
    
    