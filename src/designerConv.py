'''
Created on Dec 24, 2012

@author: dstrauss

go ahead and build the designerConv script in Python
use MPI4py to get things going in super parallel

'''

import numpy as np

class convOperator(object):
    ''' a class to make the convolutional matrix '''
    def __init__(self,m,p,q):
        ''' initialization for convolution operator
        creates an m x n implicit matrix
        m is the length of the 'data to reconstruct' 
        q is the length of the filters 
        p is the number of filters '''
        
        self.m = m
        self.p = p
        self.q = q
        self.n = self.m*self.p
        
        
    def changeWeights(self,w):
        ''' reset internal weights '''
        assert(w.shape[0] == self.q)
        if self.p > 1:
            assert(w.shape[1] == self.p)
        self.w = w
        
    def mtx(self,x):
        ''' multiplication operator '''
        assert(x.size == self.n)
        xl = x.reshape(self.m,self.p)
        
        y = np.zeros(self.m,x.dtype)
            
        for ix in xrange(self.p):
            y += np.convolve(xl[:,ix], self.w[:,ix].flatten(),'same')
        
        return y
            
    
    def mtxT(self,y):
        ''' adjoint multiplication operator '''
        assert(y.size==self.m)
        
        x = np.zeros(self.n,y.dtype)
        print 'y type ' + repr(y.dtype)
        
        for ix in range(self.p):
            slz = slice((ix*self.m),(ix*self.m)+self.m)
            x[slz] = np.convolve(y,np.flipud(self.w[:,ix].flatten()),'same')
               
        return x
        
    def matvec(self,x):
        ''' haha! cg call for a function called matvec, I can simply overload it
        and return AtA haha '''
        return self.mtxT(self.mtx(x))

def test():
    ''' test routine for matrices 
    should implement a reciprocal, in place Transposed routine '''
    import scipy.linalg
    import matplotlib.pyplot as plt
    
    ''' some test dimensions, small in size '''
    p = 1
    q = 5
    m = 20
    
    ''' create the operator, initialize '''
    A = convOperator(m,p,q)
    w = np.random.randn(q,p)
    A.changeWeights(w)
    
    '''create random x'''
    x = np.random.randn(m)
    
    
    ''' apply functional operator and its transpose '''
    yf = A.mtx(x)
    xf = A.mtxT(yf)
    
    ''' build the convmtx() version '''
    wx = np.zeros(m+q-1)
    wx[:q] = w.flatten()
    M = np.tril(scipy.linalg.toeplitz(wx),0)
    M = M[:,:m]
    M = M[2:22]
    
    print 'size of convmtx ' + repr(M.shape)
    
    ym = np.dot(M,x)
    xm = np.dot(M.T,ym)
    
    ''' and do naiive convolution'''
    yc = np.convolve(w.flatten(),x)
    xc = np.convolve(np.flipud(w.flatten()),yc)
                     
                     
    plt.figure(1)
    plt.subplot(2,1,1)
    plt.plot(range(20), yf, range(20),ym, range(-2,22),yc)
    
    plt.subplot(2,1,2)
    plt.plot(range(20), xf, range(20), xm, range(-4,24), xc)
    
    plt.show()
    
    return (yf,xf,ym,xm,yc,xc)
    
    
    
if __name__ == '__main__':
    test()